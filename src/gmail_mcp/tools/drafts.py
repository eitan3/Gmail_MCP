"""Draft tools: create_draft, list_drafts, send_draft, update_draft, delete_draft."""

from __future__ import annotations

from ..gmail_client import build_mime, raw_of
from ._common import client_for

_SUMMARY_HEADERS = ["To", "Subject", "Date"]


def _draft_message_body(
    *, to, cc, bcc, subject, body_text, body_html, sender, attachments, thread_id
) -> dict:
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
    message = {"raw": raw_of(msg)}
    if thread_id:
        message["threadId"] = thread_id
    return {"message": message}


def register(mcp) -> None:
    @mcp.tool()
    def create_draft(
        to: list[str] | None = None,
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[str] | None = None,
        sender: str | None = None,
        thread_id: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Create a draft. `thread_id` attaches it to an existing thread (e.g. a reply draft)."""
        c = client_for(account, password)
        body = _draft_message_body(
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            sender=sender,
            attachments=attachments,
            thread_id=thread_id,
        )
        return c.execute(c.users.drafts().create(userId="me", body=body))

    @mcp.tool()
    def list_drafts(
        max_results: int = 25,
        page_token: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """List drafts with subject/recipient summaries and `next_page_token`."""
        c = client_for(account, password)
        resp = c.execute(
            c.users.drafts().list(userId="me", maxResults=max_results, pageToken=page_token)
        )
        drafts = []
        for stub in resp.get("drafts", []):
            full = c.execute(
                c.users.drafts().get(
                    userId="me", id=stub["id"], format="metadata"
                )
            )
            message = full.get("message", {})
            headers = c.headers_dict(message.get("payload", {}))
            drafts.append(
                {
                    "id": full.get("id"),
                    "messageId": message.get("id"),
                    "threadId": message.get("threadId"),
                    "snippet": message.get("snippet"),
                    "to": headers.get("To"),
                    "subject": headers.get("Subject"),
                }
            )
        return {"drafts": drafts, "next_page_token": resp.get("nextPageToken")}

    @mcp.tool()
    def send_draft(
        draft_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Send an existing draft."""
        c = client_for(account, password)
        return c.execute(c.users.drafts().send(userId="me", body={"id": draft_id}))

    @mcp.tool()
    def update_draft(
        draft_id: str,
        to: list[str] | None = None,
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[str] | None = None,
        sender: str | None = None,
        thread_id: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Replace a draft's contents (Gmail replaces the whole message — pass all fields you want)."""
        c = client_for(account, password)
        body = _draft_message_body(
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            sender=sender,
            attachments=attachments,
            thread_id=thread_id,
        )
        return c.execute(c.users.drafts().update(userId="me", id=draft_id, body=body))

    @mcp.tool()
    def delete_draft(
        draft_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Permanently delete a draft (the draft only — not a sent message)."""
        c = client_for(account, password)
        c.execute(c.users.drafts().delete(userId="me", id=draft_id))
        return {"deleted": draft_id}
