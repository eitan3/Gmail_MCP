"""Trash tools: trash_message, untrash_message, trash_thread, untrash_thread."""

from __future__ import annotations

from ._common import client_for


def register(mcp) -> None:
    @mcp.tool()
    def trash_message(
        message_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Move a message to Trash (recoverable; not a permanent delete)."""
        c = client_for(account, password)
        return c.execute(c.users.messages().trash(userId="me", id=message_id))

    @mcp.tool()
    def untrash_message(
        message_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Restore a message from Trash."""
        c = client_for(account, password)
        return c.execute(c.users.messages().untrash(userId="me", id=message_id))

    @mcp.tool()
    def trash_thread(
        thread_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Move an entire thread to Trash."""
        c = client_for(account, password)
        return c.execute(c.users.threads().trash(userId="me", id=thread_id))

    @mcp.tool()
    def untrash_thread(
        thread_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Restore an entire thread from Trash."""
        c = client_for(account, password)
        return c.execute(c.users.threads().untrash(userId="me", id=thread_id))
