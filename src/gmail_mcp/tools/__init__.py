"""Tool registry: import every tool module and register its tools on the MCP server."""

from __future__ import annotations

from . import (
    attachments,
    batch,
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
]


def register_all(mcp) -> None:
    for module in _MODULES:
        module.register(mcp)
