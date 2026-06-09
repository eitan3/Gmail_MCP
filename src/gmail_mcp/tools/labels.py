"""Label tools: CRUD plus (un)labeling messages and threads.

Label arguments accept human names (e.g. "Work/Receipts") or raw label ids; names
are resolved to ids via the per-account cache in :class:`GmailClient`.
"""

from __future__ import annotations

from ._common import as_list, client_for


def register(mcp) -> None:
    @mcp.tool()
    def list_labels(account: str | None = None, password: str | None = None) -> dict:
        """List all labels (system and user) with their ids."""
        c = client_for(account, password)
        return {"labels": c.labels(refresh=True)}

    @mcp.tool()
    def create_label(
        name: str,
        label_list_visibility: str = "labelShow",
        message_list_visibility: str = "show",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Create a label. Use '/' in `name` for nesting (e.g. 'Clients/Acme')."""
        c = client_for(account, password)
        body = {
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }
        label = c.execute(c.users.labels().create(userId="me", body=body))
        c.invalidate_labels()
        return label

    @mcp.tool()
    def update_label(
        label: str,
        name: str | None = None,
        label_list_visibility: str | None = None,
        message_list_visibility: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Rename or change visibility of a label (identified by name or id)."""
        c = client_for(account, password)
        label_id = c.resolve_label_id(label)
        body = {}
        if name is not None:
            body["name"] = name
        if label_list_visibility is not None:
            body["labelListVisibility"] = label_list_visibility
        if message_list_visibility is not None:
            body["messageListVisibility"] = message_list_visibility
        updated = c.execute(c.users.labels().patch(userId="me", id=label_id, body=body))
        c.invalidate_labels()
        return updated

    @mcp.tool()
    def delete_label(
        label: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Delete a label (identified by name or id)."""
        c = client_for(account, password)
        label_id = c.resolve_label_id(label)
        c.execute(c.users.labels().delete(userId="me", id=label_id))
        c.invalidate_labels()
        return {"deleted": label_id}

    @mcp.tool()
    def label_message(
        message_id: str,
        labels: list[str],
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Add one or more labels to a message."""
        c = client_for(account, password)
        ids = c.resolve_label_ids(as_list(labels))
        return c.execute(
            c.users.messages().modify(
                userId="me", id=message_id, body={"addLabelIds": ids}
            )
        )

    @mcp.tool()
    def unlabel_message(
        message_id: str,
        labels: list[str],
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Remove one or more labels from a message."""
        c = client_for(account, password)
        ids = c.resolve_label_ids(as_list(labels))
        return c.execute(
            c.users.messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ids}
            )
        )

    @mcp.tool()
    def label_thread(
        thread_id: str,
        labels: list[str],
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Add one or more labels to every message in a thread."""
        c = client_for(account, password)
        ids = c.resolve_label_ids(as_list(labels))
        return c.execute(
            c.users.threads().modify(
                userId="me", id=thread_id, body={"addLabelIds": ids}
            )
        )

    @mcp.tool()
    def unlabel_thread(
        thread_id: str,
        labels: list[str],
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Remove one or more labels from every message in a thread."""
        c = client_for(account, password)
        ids = c.resolve_label_ids(as_list(labels))
        return c.execute(
            c.users.threads().modify(
                userId="me", id=thread_id, body={"removeLabelIds": ids}
            )
        )
