"""Message-state tools (EXTRA): read/unread, star, archive, important.

All are thin wrappers over ``messages.modify`` adding/removing Gmail's system
labels (UNREAD, STARRED, INBOX, IMPORTANT).
"""

from __future__ import annotations

from ._common import client_for


def _modify(client, message_id, add=None, remove=None):
    body = {}
    if add:
        body["addLabelIds"] = add
    if remove:
        body["removeLabelIds"] = remove
    return client.execute(
        client.users.messages().modify(userId="me", id=message_id, body=body)
    )


def register(mcp) -> None:
    @mcp.tool()
    def mark_read(message_id: str, account: str | None = None) -> dict:
        """Mark a message as read (removes the UNREAD label)."""
        return _modify(client_for(account), message_id, remove=["UNREAD"])

    @mcp.tool()
    def mark_unread(message_id: str, account: str | None = None) -> dict:
        """Mark a message as unread (adds the UNREAD label)."""
        return _modify(client_for(account), message_id, add=["UNREAD"])

    @mcp.tool()
    def star(message_id: str, account: str | None = None) -> dict:
        """Star a message."""
        return _modify(client_for(account), message_id, add=["STARRED"])

    @mcp.tool()
    def unstar(message_id: str, account: str | None = None) -> dict:
        """Remove the star from a message."""
        return _modify(client_for(account), message_id, remove=["STARRED"])

    @mcp.tool()
    def archive(message_id: str, account: str | None = None) -> dict:
        """Archive a message (removes it from the Inbox)."""
        return _modify(client_for(account), message_id, remove=["INBOX"])

    @mcp.tool()
    def move_to_inbox(message_id: str, account: str | None = None) -> dict:
        """Move a message back to the Inbox."""
        return _modify(client_for(account), message_id, add=["INBOX"])

    @mcp.tool()
    def mark_important(message_id: str, account: str | None = None) -> dict:
        """Mark a message as important."""
        return _modify(client_for(account), message_id, add=["IMPORTANT"])

    @mcp.tool()
    def mark_not_important(message_id: str, account: str | None = None) -> dict:
        """Mark a message as not important."""
        return _modify(client_for(account), message_id, remove=["IMPORTANT"])
