"""Calendar misc tools: free/busy, settings, color palette."""

from __future__ import annotations

from ._common import calendar_for


def register(mcp) -> None:
    @mcp.tool()
    def get_freebusy(
        time_min: str,
        time_max: str,
        calendar_ids: list[str] | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Query busy time ranges across one or more calendars between time_min and time_max (RFC3339).

        `calendar_ids` defaults to ['primary']. Returns busy slots per calendar.
        """
        c = calendar_for(account, password)
        items = [{"id": cid} for cid in (calendar_ids or ["primary"])]
        resp = c.execute(
            c.freebusy.query(body={"timeMin": time_min, "timeMax": time_max, "items": items})
        )
        return {
            "timeMin": time_min,
            "timeMax": time_max,
            "calendars": resp.get("calendars", {}),
        }

    @mcp.tool()
    def list_settings(account: str | None = None, password: str | None = None) -> dict:
        """List all user calendar settings (timezone, week start, default reminders, etc.)."""
        c = calendar_for(account, password)
        resp = c.execute(c.settings.list())
        return {"settings": resp.get("items", [])}

    @mcp.tool()
    def get_setting(
        setting: str, account: str | None = None, password: str | None = None
    ) -> dict:
        """Get a single user calendar setting by id (e.g. 'timezone', 'weekStart')."""
        c = calendar_for(account, password)
        return c.execute(c.settings.get(setting=setting))

    @mcp.tool()
    def get_colors(account: str | None = None, password: str | None = None) -> dict:
        """Get the calendar and event color palettes (colorId -> hex values)."""
        c = calendar_for(account, password)
        return c.execute(c.colors.get())
