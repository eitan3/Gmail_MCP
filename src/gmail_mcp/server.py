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
    print(
        f"[gmail-mcp] ready with {len(store)} account(s): {', '.join(store.selectors)}",
        file=sys.stderr,
    )
    mcp.run()  # stdio transport is FastMCP's default


if __name__ == "__main__":
    main()
