import pytest

from gmail_mcp.accounts import AccountStore
from gmail_mcp.calendar_client import build_event_body, render_event, time_field
from gmail_mcp.errors import InvalidPasswordError
from gmail_mcp import runtime
from gmail_mcp.tools._common import calendar_for


# --------------------------------------------------------------------------- #
# time_field
# --------------------------------------------------------------------------- #
def test_time_field_all_day_from_date():
    assert time_field("2026-06-15") == {"date": "2026-06-15"}


def test_time_field_all_day_flag():
    assert time_field("2026-06-15T10:00:00", all_day=True) == {"date": "2026-06-15T10:00:00"}


def test_time_field_timed_with_tz():
    assert time_field("2026-06-15T10:00:00", "Asia/Jerusalem") == {
        "dateTime": "2026-06-15T10:00:00",
        "timeZone": "Asia/Jerusalem",
    }


def test_time_field_timed_without_tz():
    assert time_field("2026-06-15T10:00:00Z") == {"dateTime": "2026-06-15T10:00:00Z"}


def test_time_field_none():
    assert time_field(None) is None


# --------------------------------------------------------------------------- #
# build_event_body
# --------------------------------------------------------------------------- #
def test_build_event_body_basic_timed():
    body = build_event_body(
        summary="Sync",
        start="2026-06-15T10:00:00",
        end="2026-06-15T11:00:00",
        time_zone="UTC",
    )
    assert body["summary"] == "Sync"
    assert body["start"] == {"dateTime": "2026-06-15T10:00:00", "timeZone": "UTC"}
    assert body["end"] == {"dateTime": "2026-06-15T11:00:00", "timeZone": "UTC"}


def test_build_event_body_attendees_and_recurrence():
    body = build_event_body(
        summary="x",
        attendees=["a@x.com"],
        optional_attendees=["b@x.com"],
        recurrence=["RRULE:FREQ=WEEKLY;COUNT=3"],
    )
    assert {"email": "a@x.com"} in body["attendees"]
    assert {"email": "b@x.com", "optional": True} in body["attendees"]
    assert body["recurrence"] == ["RRULE:FREQ=WEEKLY;COUNT=3"]


def test_build_event_body_reminders_overrides_vs_default():
    overrides = build_event_body(summary="x", reminders=[{"method": "popup", "minutes": 10}])
    assert overrides["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 10}],
    }
    default = build_event_body(summary="x", use_default_reminders=True)
    assert default["reminders"] == {"useDefault": True}


def test_build_event_body_meet_and_extra_fields_override():
    body = build_event_body(summary="x", add_meet=True, extra_fields={"summary": "override"})
    assert body["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"] == "hangoutsMeet"
    assert body["conferenceData"]["createRequest"]["requestId"]  # uuid present
    assert body["summary"] == "override"  # extra_fields merged last


def test_build_event_body_patch_only_includes_provided():
    body = build_event_body(summary="only summary")
    assert body == {"summary": "only summary"}  # no start/end/attendees/etc.


# --------------------------------------------------------------------------- #
# render_event
# --------------------------------------------------------------------------- #
def test_render_event_extracts_fields_and_meet_link():
    event = {
        "id": "ev1",
        "status": "confirmed",
        "summary": "Demo",
        "start": {"date": "2026-06-15"},
        "end": {"date": "2026-06-16"},
        "attendees": [{"email": "a@x.com", "responseStatus": "accepted", "self": True}],
        "conferenceData": {"entryPoints": [{"uri": "https://meet.google.com/abc-defg-hij"}]},
        "htmlLink": "https://calendar.google.com/event?eid=...",
    }
    out = render_event(event)
    assert out["id"] == "ev1"
    assert out["allDay"] is True
    assert out["attendees"][0]["responseStatus"] == "accepted"
    assert out["conferenceLinks"] == ["https://meet.google.com/abc-defg-hij"]


# --------------------------------------------------------------------------- #
# calendar_for shares the password gate
# --------------------------------------------------------------------------- #
def test_calendar_for_enforces_password_gate():
    runtime.set_store(
        AccountStore("cid", "csec", {"a@x.com": "tok"}, passwords={"a@x.com": "pw"})
    )
    try:
        with pytest.raises(InvalidPasswordError):
            calendar_for("a@x.com", "wrong")
    finally:
        runtime._store = None  # reset global for other tests
