"""Sending tools: send_email, reply_to_message, forward_message."""

from __future__ import annotations

from ..gmail_client import attach_bytes, build_mime, raw_of, split_addresses
from ._common import as_list, client_for

_REPLY_HEADERS = ["From", "To", "Cc", "Subject", "Message-ID", "Message-Id", "References"]


def register(mcp) -> None:
    @mcp.tool()
    def send_email(
        to: list[str],
        subject: str,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[str] | None = None,
        sender: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Send a new email.

        `to`/`cc`/`bcc`: recipient address lists. `attachments`: file paths on the server host.
        `sender`: optional explicit From (defaults to the account's primary send-as address).
        Provide `body_text` and/or `body_html`.
        `password`: the account's password — required when password protection is enabled.
        """
        c = client_for(account, password)
        msg = build_mime(
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            sender=sender,
            attachments=attachments,
        )
        return c.execute(c.users.messages().send(userId="me", body={"raw": raw_of(msg)}))

    @mcp.tool()
    def reply_to_message(
        message_id: str,
        body_text: str | None = None,
        body_html: str | None = None,
        reply_all: bool = False,
        cc: list[str] | None = None,
        attachments: list[str] | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Reply to a message, keeping it in the same thread.

        `reply_all=True` also copies the original To/Cc recipients (minus yourself).
        """
        c = client_for(account, password)
        orig = c.execute(
            c.users.messages().get(
                userId="me", id=message_id, format="metadata", metadataHeaders=_REPLY_HEADERS
            )
        )
        h = c.headers_dict(orig.get("payload", {}))
        thread_id = orig.get("threadId")
        message_id_header = h.get("Message-ID") or h.get("Message-Id")
        references = h.get("References")

        subject = h.get("Subject") or ""
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        to = split_addresses(h.get("From"))
        cc_addrs = as_list(cc)
        if reply_all:
            me = c.email_address().lower()
            already = {a.lower() for a in to} | {me}
            for addr in split_addresses(h.get("To")) + split_addresses(h.get("Cc")):
                if addr.lower() not in already and addr.lower() not in {x.lower() for x in cc_addrs}:
                    cc_addrs.append(addr)

        refs = " ".join(x for x in (references, message_id_header) if x).strip() or None
        extra_headers = {}
        if message_id_header:
            extra_headers["In-Reply-To"] = message_id_header
        if refs:
            extra_headers["References"] = refs

        msg = build_mime(
            to=to,
            cc=cc_addrs or None,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            extra_headers=extra_headers,
        )
        return c.execute(
            c.users.messages().send(
                userId="me", body={"raw": raw_of(msg), "threadId": thread_id}
            )
        )

    @mcp.tool()
    def forward_message(
        message_id: str,
        to: list[str],
        body_text: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        include_attachments: bool = True,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Forward a message to new recipients, optionally re-attaching its attachments.

        `body_text` is prepended before the quoted original. Starts a new thread.
        """
        c = client_for(account, password)
        orig = c.fetch_message(message_id, "full")
        rendered = c.render_message(orig, include_body=True)
        h = c.headers_dict(orig.get("payload", {}))

        subject = h.get("Subject") or ""
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"

        prefix = f"{body_text}\n\n" if body_text else ""
        original = rendered.get("body_text") or rendered.get("snippet") or ""
        fwd_text = (
            f"{prefix}---------- Forwarded message ----------\n"
            f"From: {h.get('From')}\n"
            f"Date: {h.get('Date')}\n"
            f"Subject: {h.get('Subject')}\n"
            f"To: {h.get('To')}\n\n"
            f"{original}"
        )

        msg = build_mime(to=to, cc=cc, bcc=bcc, subject=subject, body_text=fwd_text)
        if include_attachments:
            for att in rendered.get("attachments", []):
                data = c.download_attachment_bytes(message_id, att["attachmentId"])
                attach_bytes(msg, data, att["filename"], att.get("mimeType"))

        return c.execute(c.users.messages().send(userId="me", body={"raw": raw_of(msg)}))
