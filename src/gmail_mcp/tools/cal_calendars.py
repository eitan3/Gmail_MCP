"""Calendar management tools: secondary calendars (CRUD/clear) + calendar-list subscriptions."""

from __future__ import annotations

from ._common import calendar_for


def _calendar_list_entry(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "summary": item.get("summary"),
        "summaryOverride": item.get("summaryOverride"),
        "description": item.get("description"),
        "timeZone": item.get("timeZone"),
        "colorId": item.get("colorId"),
        "backgroundColor": item.get("backgroundColor"),
        "accessRole": item.get("accessRole"),
        "primary": item.get("primary", False),
        "selected": item.get("selected", False),
        "hidden": item.get("hidden", False),
        "defaultReminders": item.get("defaultReminders"),
    }


def register(mcp) -> None:
    @mcp.tool()
    def list_calendars(
        min_access_role: str | None = None,
        show_hidden: bool = False,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """List the calendars in this account (with access role, color, primary/selected flags).

        `min_access_role` ∈ freeBusyReader/reader/writer/owner filters the list.
        """
        c = calendar_for(account, password)
        resp = c.execute(
            c.calendar_list.list(minAccessRole=min_access_role, showHidden=show_hidden)
        )
        return {"calendars": [_calendar_list_entry(i) for i in resp.get("items", [])]}

    @mcp.tool()
    def get_calendar(
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Get a calendar's metadata (summary, description, timeZone, location)."""
        c = calendar_for(account, password)
        return c.execute(c.calendars.get(calendarId=calendar_id))

    @mcp.tool()
    def create_calendar(
        summary: str,
        description: str | None = None,
        time_zone: str | None = None,
        location: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Create a new secondary calendar."""
        c = calendar_for(account, password)
        body: dict = {"summary": summary}
        if description is not None:
            body["description"] = description
        if time_zone is not None:
            body["timeZone"] = time_zone
        if location is not None:
            body["location"] = location
        return c.execute(c.calendars.insert(body=body))

    @mcp.tool()
    def update_calendar(
        calendar_id: str,
        summary: str | None = None,
        description: str | None = None,
        time_zone: str | None = None,
        location: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Update a calendar's metadata (patch)."""
        c = calendar_for(account, password)
        body: dict = {}
        if summary is not None:
            body["summary"] = summary
        if description is not None:
            body["description"] = description
        if time_zone is not None:
            body["timeZone"] = time_zone
        if location is not None:
            body["location"] = location
        return c.execute(c.calendars.patch(calendarId=calendar_id, body=body))

    @mcp.tool()
    def delete_calendar(
        calendar_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Delete a secondary calendar (cannot delete the primary calendar)."""
        c = calendar_for(account, password)
        c.execute(c.calendars.delete(calendarId=calendar_id))
        return {"deleted": calendar_id}

    @mcp.tool()
    def clear_calendar(
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Delete ALL events from a primary calendar (only works on a primary calendar)."""
        c = calendar_for(account, password)
        c.execute(c.calendars.clear(calendarId=calendar_id))
        return {"cleared": calendar_id}

    @mcp.tool()
    def subscribe_calendar(
        calendar_id: str,
        color_id: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Add an existing calendar (by id) to this account's calendar list."""
        c = calendar_for(account, password)
        body: dict = {"id": calendar_id}
        if color_id is not None:
            body["colorId"] = color_id
        return c.execute(c.calendar_list.insert(body=body))

    @mcp.tool()
    def unsubscribe_calendar(
        calendar_id: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Remove a calendar from this account's calendar list (does not delete the calendar)."""
        c = calendar_for(account, password)
        c.execute(c.calendar_list.delete(calendarId=calendar_id))
        return {"unsubscribed": calendar_id}

    @mcp.tool()
    def update_calendar_subscription(
        calendar_id: str,
        color_id: str | None = None,
        selected: bool | None = None,
        hidden: bool | None = None,
        summary_override: str | None = None,
        default_reminders: list[dict] | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Change how a calendar appears in your list: color, selected, hidden, name override, reminders."""
        c = calendar_for(account, password)
        body: dict = {}
        if color_id is not None:
            body["colorId"] = color_id
        if selected is not None:
            body["selected"] = selected
        if hidden is not None:
            body["hidden"] = hidden
        if summary_override is not None:
            body["summaryOverride"] = summary_override
        if default_reminders is not None:
            body["defaultReminders"] = default_reminders
        return c.execute(c.calendar_list.patch(calendarId=calendar_id, body=body))
