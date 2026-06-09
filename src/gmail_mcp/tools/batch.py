"""Bulk tools (EXTRA): batch_modify_messages, batch_trash, batch_untrash.

Uses Gmail's ``messages.batchModify`` to act on many message ids in one request.
"""

from __future__ import annotations

from ._common import as_list, client_for


def register(mcp) -> None:
    @mcp.tool()
    def batch_modify_messages(
        message_ids: list[str],
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Add and/or remove labels across many messages in one call.

        `add_labels`/`remove_labels` accept label names or ids.
        """
        c = client_for(account, password)
        body: dict = {"ids": message_ids}
        if add_labels:
            body["addLabelIds"] = c.resolve_label_ids(as_list(add_labels))
        if remove_labels:
            body["removeLabelIds"] = c.resolve_label_ids(as_list(remove_labels))
        c.execute(c.users.messages().batchModify(userId="me", body=body))
        return {"modified": len(message_ids)}

    @mcp.tool()
    def batch_trash(
        message_ids: list[str], account: str | None = None, password: str | None = None
    ) -> dict:
        """Move many messages to Trash in one call."""
        c = client_for(account, password)
        c.execute(
            c.users.messages().batchModify(
                userId="me", body={"ids": message_ids, "addLabelIds": ["TRASH"]}
            )
        )
        return {"trashed": len(message_ids)}

    @mcp.tool()
    def batch_untrash(
        message_ids: list[str], account: str | None = None, password: str | None = None
    ) -> dict:
        """Restore many messages from Trash in one call."""
        c = client_for(account, password)
        c.execute(
            c.users.messages().batchModify(
                userId="me", body={"ids": message_ids, "removeLabelIds": ["TRASH"]}
            )
        )
        return {"untrashed": len(message_ids)}
