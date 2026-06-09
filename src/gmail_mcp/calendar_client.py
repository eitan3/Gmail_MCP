"""Per-account Google Calendar service wrapper plus event-building / rendering helpers.

Mirrors :mod:`gmail_client`: calendar tools never touch the raw googleapiclient
resource directly — they go through a cached :class:`CalendarClient` built from the
same per-account credentials as Gmail (one token refresh serves both APIs).
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from googleapiclient.discovery import build

from .accounts import Account
from .auth import get_credentials
from .errors import execute

# One built Calendar service per account selector (separate from the Gmail cache).
_calendar_clients: dict[str, "CalendarClient"] = {}


def get_calendar_client(account: Account) -> "CalendarClient":
    client = _calendar_clients.get(account.selector)
    if client is None:
        creds = get_credentials(account)
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        client = CalendarClient(account, service)
        _calendar_clients[account.selector] = client
    return client


# --------------------------------------------------------------------------- #
# Event time + body helpers
# --------------------------------------------------------------------------- #
def time_field(value: str | None, time_zone: str | None = None, all_day: bool = False) -> dict | None:
    """Build a Calendar start/end object from a string.

    - all-day: ``all_day=True`` or a bare ``YYYY-MM-DD`` value -> ``{"date": ...}``
    - timed: an RFC3339 dateTime (e.g. ``2026-06-15T10:00:00``) -> ``{"dateTime": ..., "timeZone": ...}``
    """
    if value is None:
        return None
    if all_day or ("T" not in value and len(value) == 10):
        return {"date": value}
    field: dict[str, Any] = {"dateTime": value}
    if time_zone:
        field["timeZone"] = time_zone
    return field


def _attendees(emails: Iterable[str] | None, optional: bool) -> list[dict]:
    out = []
    for e in emails or []:
        entry = {"email": e}
        if optional:
            entry["optional"] = True
        out.append(entry)
    return out


def build_event_body(
    *,
    summary: str | None = None,
    description: str | None = None,
    location: str | None = None,
    start: str | None = None,
    end: str | None = None,
    time_zone: str | None = None,
    all_day: bool = False,
    attendees: Iterable[str] | None = None,
    optional_attendees: Iterable[str] | None = None,
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
) -> dict:
    """Assemble an event resource from high-level fields.

    Only provided fields are included, so the same builder works for both create (insert)
    and partial update (patch). ``extra_fields`` is merged last so any Calendar field can be
    set/overridden.
    """
    body: dict[str, Any] = {}
    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location

    start_field = time_field(start, time_zone, all_day)
    end_field = time_field(end, time_zone, all_day)
    if start_field:
        body["start"] = start_field
    if end_field:
        body["end"] = end_field

    people = _attendees(attendees, optional=False) + _attendees(optional_attendees, optional=True)
    if people:
        body["attendees"] = people

    if recurrence is not None:
        body["recurrence"] = recurrence

    if use_default_reminders is not None or reminders is not None:
        if reminders:
            body["reminders"] = {"useDefault": False, "overrides": reminders}
        else:
            body["reminders"] = {"useDefault": bool(use_default_reminders)}

    for key, value in (
        ("visibility", visibility),
        ("transparency", transparency),
        ("colorId", color_id),
        ("guestsCanInviteOthers", guests_can_invite_others),
        ("guestsCanModify", guests_can_modify),
        ("guestsCanSeeOtherGuests", guests_can_see_other_guests),
    ):
        if value is not None:
            body[key] = value

    if attachments is not None:
        body["attachments"] = attachments

    if add_meet:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    if extra_fields:
        body.update(extra_fields)
    return body


def render_event(event: dict) -> dict:
    """Compact, decoded view of an event resource."""
    conf = event.get("conferenceData") or {}
    entry_points = [ep.get("uri") for ep in conf.get("entryPoints", []) if ep.get("uri")]
    return {
        "id": event.get("id"),
        "status": event.get("status"),
        "summary": event.get("summary"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": event.get("start"),
        "end": event.get("end"),
        "allDay": "date" in (event.get("start") or {}),
        "recurrence": event.get("recurrence"),
        "recurringEventId": event.get("recurringEventId"),
        "organizer": event.get("organizer"),
        "creator": event.get("creator"),
        "attendees": [
            {
                "email": a.get("email"),
                "responseStatus": a.get("responseStatus"),
                "optional": a.get("optional", False),
                "organizer": a.get("organizer", False),
                "self": a.get("self", False),
            }
            for a in event.get("attendees", [])
        ],
        "reminders": event.get("reminders"),
        "colorId": event.get("colorId"),
        "visibility": event.get("visibility"),
        "transparency": event.get("transparency"),
        "hangoutLink": event.get("hangoutLink"),
        "conferenceLinks": entry_points,
        "htmlLink": event.get("htmlLink"),
        "iCalUID": event.get("iCalUID"),
        "created": event.get("created"),
        "updated": event.get("updated"),
    }


class CalendarClient:
    def __init__(self, account: Account, service: Any):
        self.account = account
        self.service = service

    def execute(self, request: Any) -> Any:
        return execute(request)

    @property
    def events(self):
        return self.service.events()

    @property
    def calendars(self):
        return self.service.calendars()

    @property
    def calendar_list(self):
        return self.service.calendarList()

    @property
    def acl(self):
        return self.service.acl()

    @property
    def settings(self):
        return self.service.settings()

    @property
    def freebusy(self):
        return self.service.freebusy()

    @property
    def colors(self):
        return self.service.colors()
