"""Calendar sharing tools (ACL): list/share/update/unshare access rules."""

from __future__ import annotations

from ._common import calendar_for


def register(mcp) -> None:
    @mcp.tool()
    def list_acl(
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """List the access-control rules (who the calendar is shared with) and their ruleIds."""
        c = calendar_for(account, password)
        resp = c.execute(c.acl.list(calendarId=calendar_id))
        return {"rules": resp.get("items", [])}

    @mcp.tool()
    def share_calendar(
        role: str,
        scope_value: str | None = None,
        scope_type: str = "user",
        calendar_id: str = "primary",
        send_notifications: bool = True,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Share a calendar.

        `role` ∈ reader/writer/owner/freeBusyReader. `scope_type` ∈ user/group/domain/default;
        `scope_value` is the email/domain (omit for 'default' = public).
        """
        c = calendar_for(account, password)
        scope: dict = {"type": scope_type}
        if scope_value is not None:
            scope["value"] = scope_value
        body = {"role": role, "scope": scope}
        return c.execute(
            c.acl.insert(calendarId=calendar_id, body=body, sendNotifications=send_notifications)
        )

    @mcp.tool()
    def update_acl(
        rule_id: str,
        role: str,
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Change the role of an existing share (get ruleId from list_acl)."""
        c = calendar_for(account, password)
        return c.execute(
            c.acl.patch(calendarId=calendar_id, ruleId=rule_id, body={"role": role})
        )

    @mcp.tool()
    def unshare_calendar(
        rule_id: str,
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Remove a share / access rule (get ruleId from list_acl)."""
        c = calendar_for(account, password)
        c.execute(c.acl.delete(calendarId=calendar_id, ruleId=rule_id))
        return {"deleted": rule_id}
