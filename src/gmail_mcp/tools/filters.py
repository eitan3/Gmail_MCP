"""Filter tools: list_filters, create_filter, delete_filter.

`create_filter` exposes Gmail's filter model through friendly arguments and maps
common actions (mark read, archive, star, important, spam, trash) onto the
system labels Gmail uses under the hood.
"""

from __future__ import annotations

from ._common import as_list, client_for


def register(mcp) -> None:
    @mcp.tool()
    def list_filters(account: str | None = None) -> dict:
        """List all filters with their ids, criteria, and actions."""
        c = client_for(account)
        resp = c.execute(c.users.settings().filters().list(userId="me"))
        return {"filters": resp.get("filter", [])}

    @mcp.tool()
    def create_filter(
        from_address: str | None = None,
        to_address: str | None = None,
        subject: str | None = None,
        query: str | None = None,
        negated_query: str | None = None,
        has_attachment: bool | None = None,
        exclude_chats: bool | None = None,
        size: int | None = None,
        size_comparison: str | None = None,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
        forward_to: str | None = None,
        mark_read: bool = False,
        archive: bool = False,
        star: bool = False,
        mark_important: bool = False,
        never_mark_important: bool = False,
        never_spam: bool = False,
        trash: bool = False,
        account: str | None = None,
    ) -> dict:
        """Create a filter.

        Criteria: `from_address`, `to_address`, `subject`, `query` (Gmail search syntax),
        `negated_query`, `has_attachment`, `exclude_chats`, `size` + `size_comparison`
        ('larger'/'smaller').
        Actions: `add_labels`/`remove_labels` (names or ids), `forward_to`, and the booleans
        `mark_read`, `archive` (skip Inbox), `star`, `mark_important`, `never_mark_important`,
        `never_spam`, `trash`.
        """
        c = client_for(account)

        criteria: dict = {}
        if from_address:
            criteria["from"] = from_address
        if to_address:
            criteria["to"] = to_address
        if subject:
            criteria["subject"] = subject
        if query:
            criteria["query"] = query
        if negated_query:
            criteria["negatedQuery"] = negated_query
        if has_attachment is not None:
            criteria["hasAttachment"] = has_attachment
        if exclude_chats is not None:
            criteria["excludeChats"] = exclude_chats
        if size is not None:
            criteria["size"] = size
        if size_comparison:
            criteria["sizeComparison"] = size_comparison

        add_ids = c.resolve_label_ids(as_list(add_labels)) if add_labels else []
        remove_ids = c.resolve_label_ids(as_list(remove_labels)) if remove_labels else []
        if mark_read:
            remove_ids.append("UNREAD")
        if archive:
            remove_ids.append("INBOX")
        if never_mark_important:
            remove_ids.append("IMPORTANT")
        if never_spam:
            remove_ids.append("SPAM")
        if star:
            add_ids.append("STARRED")
        if mark_important:
            add_ids.append("IMPORTANT")
        if trash:
            add_ids.append("TRASH")

        action: dict = {}
        if add_ids:
            action["addLabelIds"] = list(dict.fromkeys(add_ids))
        if remove_ids:
            action["removeLabelIds"] = list(dict.fromkeys(remove_ids))
        if forward_to:
            action["forward"] = forward_to

        if not criteria:
            from ..errors import GmailMcpError

            raise GmailMcpError("create_filter needs at least one criterion.")
        if not action:
            from ..errors import GmailMcpError

            raise GmailMcpError("create_filter needs at least one action.")

        return c.execute(
            c.users.settings()
            .filters()
            .create(userId="me", body={"criteria": criteria, "action": action})
        )

    @mcp.tool()
    def delete_filter(filter_id: str, account: str | None = None) -> dict:
        """Delete a filter by id (get ids from list_filters)."""
        c = client_for(account)
        c.execute(c.users.settings().filters().delete(userId="me", id=filter_id))
        return {"deleted": filter_id}
