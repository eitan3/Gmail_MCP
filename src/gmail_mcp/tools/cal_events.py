"""Calendar event tools: CRUD, recurring instances, quick-add, move, search, RSVP, import."""

from __future__ import annotations

from ..calendar_client import build_event_body, render_event
from ..errors import GmailMcpError
from ._common import calendar_for


def register(mcp) -> None:
    @mcp.tool()
    def list_events(
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        query: str | None = None,
        max_results: int = 25,
        page_token: str | None = None,
        single_events: bool = True,
        order_by: str | None = "startTime",
        show_deleted: bool = False,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """List/search events on a calendar.

        `time_min`/`time_max` are RFC3339 (e.g. '2026-06-15T00:00:00Z'). `query` is free-text
        search. `single_events=True` expands recurring events into instances (required for
        `order_by='startTime'`). Returns rendered events + `next_page_token`.
        """
        c = calendar_for(account, password)
        resp = c.execute(
            c.events.list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                q=query,
                maxResults=max_results,
                pageToken=page_token,
                singleEvents=single_events,
                orderBy=order_by,
                showDeleted=show_deleted,
            )
        )
        return {
            "events": [render_event(e) for e in resp.get("items", [])],
            "next_page_token": resp.get("nextPageToken"),
            "time_zone": resp.get("timeZone"),
        }

    @mcp.tool()
    def get_event(
        event_id: str,
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Get a single event."""
        c = calendar_for(account, password)
        return render_event(c.execute(c.events.get(calendarId=calendar_id, eventId=event_id)))

    @mcp.tool()
    def create_event(
        summary: str,
        start: str | None = None,
        end: str | None = None,
        time_zone: str | None = None,
        all_day: bool = False,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        optional_attendees: list[str] | None = None,
        recurrence: list[str] | None = None,
        reminders: list[dict] | None = None,
        use_default_reminders: bool | None = None,
        visibility: str | None = None,
        transparency: str | None = None,
        color_id: str | None = None,
        guests_can_invite_others: bool | None = None,
        guests_can_modify: bool | None = None,
        guests_can_see_other_guests: bool | None = None,
        attachments: list[dict] | None = None,
        add_meet: bool = False,
        extra_fields: dict | None = None,
        calendar_id: str = "primary",
        send_updates: str = "none",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Create an event.

        Time: pass `start`/`end` as RFC3339 dateTimes with `time_zone` (IANA), or `all_day=true`
        with 'YYYY-MM-DD'. `recurrence` is a list of RRULE strings. `attendees`/`optional_attendees`
        are email lists. `add_meet=true` attaches a Google Meet link. `reminders` is a list of
        {method:'popup'|'email', minutes:int}. `send_updates` ∈ all/externalOnly/none. `extra_fields`
        merges any other Calendar event fields.
        """
        c = calendar_for(account, password)
        body = build_event_body(
            summary=summary,
            start=start,
            end=end,
            time_zone=time_zone,
            all_day=all_day,
            description=description,
            location=location,
            attendees=attendees,
            optional_attendees=optional_attendees,
            recurrence=recurrence,
            reminders=reminders,
            use_default_reminders=use_default_reminders,
            visibility=visibility,
            transparency=transparency,
            color_id=color_id,
            guests_can_invite_others=guests_can_invite_others,
            guests_can_modify=guests_can_modify,
            guests_can_see_other_guests=guests_can_see_other_guests,
            attachments=attachments,
            add_meet=add_meet,
            extra_fields=extra_fields,
        )
        kwargs: dict = {"calendarId": calendar_id, "body": body, "sendUpdates": send_updates}
        if add_meet:
            kwargs["conferenceDataVersion"] = 1
        if attachments:
            kwargs["supportsAttachments"] = True
        return render_event(c.execute(c.events.insert(**kwargs)))

    @mcp.tool()
    def update_event(
        event_id: str,
        summary: str | None = None,
        start: str | None = None,
        end: str | None = None,
        time_zone: str | None = None,
        all_day: bool = False,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        optional_attendees: list[str] | None = None,
        recurrence: list[str] | None = None,
        reminders: list[dict] | None = None,
        use_default_reminders: bool | None = None,
        visibility: str | None = None,
        transparency: str | None = None,
        color_id: str | None = None,
        guests_can_invite_others: bool | None = None,
        guests_can_modify: bool | None = None,
        guests_can_see_other_guests: bool | None = None,
        attachments: list[dict] | None = None,
        add_meet: bool = False,
        extra_fields: dict | None = None,
        calendar_id: str = "primary",
        send_updates: str = "none",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Update an event (patch — only the fields you pass are changed)."""
        c = calendar_for(account, password)
        body = build_event_body(
            summary=summary,
            start=start,
            end=end,
            time_zone=time_zone,
            all_day=all_day,
            description=description,
            location=location,
            attendees=attendees,
            optional_attendees=optional_attendees,
            recurrence=recurrence,
            reminders=reminders,
            use_default_reminders=use_default_reminders,
            visibility=visibility,
            transparency=transparency,
            color_id=color_id,
            guests_can_invite_others=guests_can_invite_others,
            guests_can_modify=guests_can_modify,
            guests_can_see_other_guests=guests_can_see_other_guests,
            attachments=attachments,
            add_meet=add_meet,
            extra_fields=extra_fields,
        )
        kwargs: dict = {
            "calendarId": calendar_id,
            "eventId": event_id,
            "body": body,
            "sendUpdates": send_updates,
        }
        if add_meet:
            kwargs["conferenceDataVersion"] = 1
        if attachments:
            kwargs["supportsAttachments"] = True
        return render_event(c.execute(c.events.patch(**kwargs)))

    @mcp.tool()
    def delete_event(
        event_id: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Delete an event. `send_updates` ∈ all/externalOnly/none notifies attendees."""
        c = calendar_for(account, password)
        c.execute(
            c.events.delete(calendarId=calendar_id, eventId=event_id, sendUpdates=send_updates)
        )
        return {"deleted": event_id}

    @mcp.tool()
    def quick_add_event(
        text: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Create an event from natural language (e.g. 'Lunch with Sam tomorrow 1pm')."""
        c = calendar_for(account, password)
        return render_event(
            c.execute(c.events.quickAdd(calendarId=calendar_id, text=text, sendUpdates=send_updates))
        )

    @mcp.tool()
    def move_event(
        event_id: str,
        destination_calendar_id: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Move an event from one calendar to another."""
        c = calendar_for(account, password)
        return render_event(
            c.execute(
                c.events.move(
                    calendarId=calendar_id,
                    eventId=event_id,
                    destination=destination_calendar_id,
                    sendUpdates=send_updates,
                )
            )
        )

    @mcp.tool()
    def list_event_instances(
        event_id: str,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 25,
        page_token: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """List the individual instances of a recurring event."""
        c = calendar_for(account, password)
        resp = c.execute(
            c.events.instances(
                calendarId=calendar_id,
                eventId=event_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                pageToken=page_token,
            )
        )
        return {
            "instances": [render_event(e) for e in resp.get("items", [])],
            "next_page_token": resp.get("nextPageToken"),
        }

    @mcp.tool()
    def respond_to_event(
        event_id: str,
        response: str,
        calendar_id: str = "primary",
        comment: str | None = None,
        send_updates: str = "all",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """RSVP to an event you're invited to. `response` ∈ accepted/declined/tentative."""
        c = calendar_for(account, password)
        event = c.execute(c.events.get(calendarId=calendar_id, eventId=event_id))
        attendees = event.get("attendees", [])
        me = next((a for a in attendees if a.get("self")), None)
        if me is None:
            raise GmailMcpError("This account is not an attendee of the event (cannot RSVP).")
        me["responseStatus"] = response
        if comment is not None:
            me["comment"] = comment
        updated = c.execute(
            c.events.patch(
                calendarId=calendar_id,
                eventId=event_id,
                body={"attendees": attendees},
                sendUpdates=send_updates,
            )
        )
        return render_event(updated)

    @mcp.tool()
    def import_event(
        i_cal_uid: str,
        start: str,
        end: str,
        summary: str | None = None,
        time_zone: str | None = None,
        all_day: bool = False,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        calendar_id: str = "primary",
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Import an event (adds a copy carrying an existing iCalUID, e.g. from an .ics)."""
        c = calendar_for(account, password)
        body = build_event_body(
            summary=summary,
            start=start,
            end=end,
            time_zone=time_zone,
            all_day=all_day,
            description=description,
            location=location,
            attendees=attendees,
        )
        body["iCalUID"] = i_cal_uid
        return render_event(c.execute(c.events.import_(calendarId=calendar_id, body=body)))
