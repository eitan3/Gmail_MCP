"""Tool registry: import every tool module and register its tools on the MCP server."""

from __future__ import annotations

from . import (
    attachments,
    batch,
    cal_calendars,
    cal_events,
    cal_misc,
    cal_sharing,
    drafts,
    filters,
    labels,
    read,
    send,
    settings,
    state,
    trash,
)

_MODULES = [
    # Gmail
    send,
    drafts,
    read,
    attachments,
    trash,
    labels,
    filters,
    settings,
    state,
    batch,
    # Calendar
    cal_events,
    cal_calendars,
    cal_sharing,
    cal_misc,
]


def register_all(mcp) -> None:
    for module in _MODULES:
        module.register(mcp)
