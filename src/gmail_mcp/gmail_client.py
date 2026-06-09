"""Per-account Gmail service wrapper plus shared MIME / rendering / label helpers.

Tools never talk to the raw googleapiclient resource directly; they go through a
cached :class:`GmailClient`, which owns the ``service`` object, a label-name
cache, and the message-building/rendering utilities every tool needs.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from email.message import EmailMessage
from email.utils import getaddresses
from typing import Any, Iterable

from googleapiclient.discovery import build

from .accounts import Account
from .auth import get_credentials
from .errors import GmailMcpError, execute

# One built service per account selector — building is relatively expensive and
# the underlying credentials refresh themselves in place.
_clients: dict[str, "GmailClient"] = {}


def get_client(account: Account) -> "GmailClient":
    client = _clients.get(account.selector)
    if client is None:
        creds = get_credentials(account)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        client = GmailClient(account, service)
        _clients[account.selector] = client
    return client


# --------------------------------------------------------------------------- #
# base64url helpers (Gmail uses URL-safe base64, often without padding)
# --------------------------------------------------------------------------- #
def b64url_decode(data: str) -> bytes:
    if not data:
        return b""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _as_address_list(value: str | Iterable[str] | None) -> str | None:
    """Accept a comma string or a list of addresses; return a header-ready string."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    joined = ", ".join(v.strip() for v in value if v and v.strip())
    return joined or None


def build_mime(
    *,
    to: str | Iterable[str] | None = None,
    cc: str | Iterable[str] | None = None,
    bcc: str | Iterable[str] | None = None,
    subject: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    sender: str | None = None,
    attachments: Iterable[str] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> EmailMessage:
    """Build an :class:`EmailMessage` from high-level fields.

    ``attachments`` is a list of file paths on the host running the server.
    """
    msg = EmailMessage()
    if sender:
        msg["From"] = sender
    for header, value in (("To", to), ("Cc", cc), ("Bcc", bcc)):
        addr = _as_address_list(value)
        if addr:
            msg[header] = addr
    msg["Subject"] = subject or ""
    for key, value in (extra_headers or {}).items():
        if value:
            msg[key] = value

    if body_html:
        msg.set_content(body_text or "")
        msg.add_alternative(body_html, subtype="html")
    else:
        msg.set_content(body_text or "")

    for path in attachments or []:
        _attach_file(msg, path)
    return msg


def _attach_file(msg: EmailMessage, path: str) -> None:
    if not os.path.isfile(path):
        raise GmailMcpError(f"Attachment not found: {path}")
    ctype, _ = mimetypes.guess_type(path)
    maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
    with open(path, "rb") as fh:
        data = fh.read()
    msg.add_attachment(
        data, maintype=maintype, subtype=subtype, filename=os.path.basename(path)
    )


def attach_bytes(
    msg: EmailMessage, data: bytes, filename: str, mime_type: str | None = None
) -> None:
    """Attach in-memory bytes (used when forwarding to re-attach original parts)."""
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)


def raw_of(msg: EmailMessage) -> str:
    """base64url-encode a MIME message for the Gmail `raw` field."""
    return b64url_encode(msg.as_bytes())


class GmailClient:
    def __init__(self, account: Account, service: Any):
        self.account = account
        self.service = service
        self._label_cache: dict[str, str] | None = None  # name(lower) -> id
        self._email: str | None = None

    # -- low-level shortcuts ------------------------------------------------- #
    @property
    def users(self):
        return self.service.users()

    def email_address(self) -> str:
        """The authenticated mailbox's own address (cached); used for reply-all and send-as."""
        if not self._email:
            self._email = self.execute(self.users.getProfile(userId="me")).get("emailAddress")
        return self._email or ""

    def execute(self, request: Any) -> Any:
        return execute(request)

    # -- labels -------------------------------------------------------------- #
    def labels(self, *, refresh: bool = False) -> list[dict]:
        result = self.execute(self.users.labels().list(userId="me"))
        labels = result.get("labels", [])
        self._label_cache = {lbl["name"].lower(): lbl["id"] for lbl in labels}
        return labels

    def _label_map(self) -> dict[str, str]:
        if self._label_cache is None:
            self.labels()
        return self._label_cache or {}

    def resolve_label_id(self, name_or_id: str) -> str:
        """Map a human label name to its id; pass through values that already look like ids."""
        # System labels and Gmail's generated ids are accepted as-is.
        mapping = self._label_map()
        if name_or_id in mapping.values():
            return name_or_id
        found = mapping.get(name_or_id.lower())
        if found:
            return found
        # Refresh once in case the label was just created elsewhere.
        self.labels(refresh=True)
        mapping = self._label_map()
        if name_or_id in mapping.values():
            return name_or_id
        found = mapping.get(name_or_id.lower())
        if found:
            return found
        raise GmailMcpError(f"Label not found: {name_or_id}")

    def resolve_label_ids(self, names_or_ids: Iterable[str]) -> list[str]:
        return [self.resolve_label_id(n) for n in names_or_ids]

    def invalidate_labels(self) -> None:
        self._label_cache = None

    # -- message rendering --------------------------------------------------- #
    @staticmethod
    def headers_dict(payload: dict) -> dict[str, str]:
        return {h["name"]: h["value"] for h in payload.get("headers", [])}

    @classmethod
    def _walk(cls, payload: dict, texts: list[str], htmls: list[str], atts: list[dict]) -> None:
        mime = payload.get("mimeType", "")
        filename = payload.get("filename") or ""
        body = payload.get("body", {})
        if filename and body.get("attachmentId"):
            atts.append(
                {
                    "filename": filename,
                    "mimeType": mime,
                    "size": body.get("size"),
                    "attachmentId": body["attachmentId"],
                }
            )
        elif mime == "text/plain" and body.get("data"):
            texts.append(b64url_decode(body["data"]).decode("utf-8", "replace"))
        elif mime == "text/html" and body.get("data"):
            htmls.append(b64url_decode(body["data"]).decode("utf-8", "replace"))
        for part in payload.get("parts", []) or []:
            cls._walk(part, texts, htmls, atts)

    @classmethod
    def render_message(cls, msg: dict, *, include_body: bool = True) -> dict:
        """Turn a Gmail message resource into a compact, decoded dict."""
        payload = msg.get("payload", {})
        headers = cls.headers_dict(payload)
        out: dict[str, Any] = {
            "id": msg.get("id"),
            "threadId": msg.get("threadId"),
            "labelIds": msg.get("labelIds", []),
            "snippet": msg.get("snippet"),
            "internalDate": msg.get("internalDate"),
            "from": headers.get("From"),
            "to": headers.get("To"),
            "cc": headers.get("Cc"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),
        }
        texts: list[str] = []
        htmls: list[str] = []
        atts: list[dict] = []
        cls._walk(payload, texts, htmls, atts)
        out["attachments"] = atts
        if include_body:
            out["body_text"] = "\n".join(texts) if texts else None
            out["body_html"] = "\n".join(htmls) if htmls else None
        return out

    # -- helpers used by reply / forward ------------------------------------- #
    def fetch_message(self, message_id: str, fmt: str = "full") -> dict:
        return self.execute(
            self.users.messages().get(userId="me", id=message_id, format=fmt)
        )

    def download_attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
        att = self.execute(
            self.users.messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
        )
        return b64url_decode(att.get("data", ""))


def split_addresses(value: str | None) -> list[str]:
    """Parse a header value into a list of bare email addresses."""
    if not value:
        return []
    return [addr for _, addr in getaddresses([value]) if addr]
