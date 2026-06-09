"""MCP server entry point.

Builds a FastMCP server, registers all Gmail tools, loads the account store from
env vars, and runs over stdio.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .config import load_account_store
from .errors import ConfigError
from .runtime import set_store
from .tools import register_all

mcp = FastMCP("gmail")
register_all(mcp)


def main() -> None:
    try:
        store = load_account_store()
    except ConfigError as exc:
        print(f"[gmail-mcp] configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2)

    set_store(store)
    gate = "ON (password required per call)" if store.password_gate_enabled else "off"
    try:
        tool_count = len(mcp._tool_manager.list_tools())
    except Exception:  # pragma: no cover - defensive against FastMCP internals changing
        tool_count = "?"
    print(
        f"[gmail-mcp] {tool_count} tools | {len(store)} account(s): "
        f"{', '.join(store.selectors)} | password gate: {gate}",
        file=sys.stderr,
    )
    if store.password_gate_enabled:
        locked = store.accounts_without_password()
        if locked:
            print(
                f"[gmail-mcp] note: {len(locked)} account(s) have no password and are locked: "
                + ", ".join(locked),
                file=sys.stderr,
            )
    mcp.run()  # stdio transport is FastMCP's default


if __name__ == "__main__":
    main()
