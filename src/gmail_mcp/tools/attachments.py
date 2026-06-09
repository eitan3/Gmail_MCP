"""Attachment tools: get_message_attachments, download_attachment."""

from __future__ import annotations

import os

from ._common import client_for


def register(mcp) -> None:
    @mcp.tool()
    def get_message_attachments(message_id: str, account: str | None = None) -> dict:
        """List a message's attachments (filename, mimeType, size, attachmentId)."""
        c = client_for(account)
        msg = c.fetch_message(message_id, "full")
        rendered = c.render_message(msg, include_body=False)
        return {"messageId": message_id, "attachments": rendered["attachments"]}

    @mcp.tool()
    def download_attachment(
        message_id: str,
        attachment_id: str,
        save_path: str,
        account: str | None = None,
    ) -> dict:
        """Download an attachment to `save_path` on the server host.

        Get `attachment_id` from `get_message_attachments` or `get_message`.
        """
        c = client_for(account)
        data = c.download_attachment_bytes(message_id, attachment_id)
        directory = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(directory, exist_ok=True)
        with open(save_path, "wb") as fh:
            fh.write(data)
        return {"path": os.path.abspath(save_path), "bytes": len(data)}
