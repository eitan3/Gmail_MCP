"""`gmail-mcp-auth` — one-time OAuth consent flow that prints env-var values.

Run this on a machine with a browser (your laptop). It performs Google's consent
flow for one account (Gmail + Calendar scopes) using only the shared client
id/secret (no credentials.json file), then prints the exact ``GMAIL_CLIENT`` and
``GMAIL_ACCOUNTS`` values to paste into the server's environment. Re-run with
``--merge`` to add more accounts — or to re-consent an existing account after a
scope upgrade (the new token replaces the old one for that selector).

Cross-platform: uses a localhost redirect + your default browser. For a headless
host, use ``--no-browser`` and open the printed URL yourself (forward the local
redirect port over SSH if the consent happens on another machine).
"""

from __future__ import annotations

import argparse
import os
import sys

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from . import SCOPES
from .config import ACCOUNTS_ENV, CLIENT_ENV, parse_accounts, parse_client


def _client_config(client_id: str, client_secret: str) -> dict:
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _resolve_client(args) -> tuple[str, str]:
    client_id, client_secret = args.client_id, args.client_secret
    if not (client_id and client_secret):
        env_client = os.environ.get(CLIENT_ENV)
        if env_client:
            client_id, client_secret = parse_client(env_client)
    if not client_id:
        client_id = input("OAuth client_id: ").strip()
    if not client_secret:
        client_secret = input("OAuth client_secret: ").strip()
    if not (client_id and client_secret):
        print("client_id and client_secret are required.", file=sys.stderr)
        raise SystemExit(2)
    return client_id, client_secret


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="gmail-mcp-auth",
        description="Authorize one Gmail account and print the env-var values to paste.",
    )
    parser.add_argument("--client-id", help="OAuth client id (else read GMAIL_CLIENT or prompt)")
    parser.add_argument("--client-secret", help="OAuth client secret (else read GMAIL_CLIENT or prompt)")
    parser.add_argument("--alias", help="Use this selector instead of the account's email")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing GMAIL_ACCOUNTS from the environment and print the full value",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open a browser; print the URL to visit (headless hosts)",
    )
    parser.add_argument(
        "--port", type=int, default=0, help="Local redirect port (0 = pick a free port)"
    )
    args = parser.parse_args(argv)

    client_id, client_secret = _resolve_client(args)

    flow = InstalledAppFlow.from_client_config(_client_config(client_id, client_secret), SCOPES)
    creds = flow.run_local_server(
        port=args.port,
        open_browser=not args.no_browser,
        access_type="offline",
        prompt="consent",
    )

    if not creds.refresh_token:
        print(
            "No refresh token was returned. Revoke prior access at "
            "https://myaccount.google.com/permissions and re-run.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    email = service.users().getProfile(userId="me").execute().get("emailAddress")
    selector = args.alias or email

    if args.merge:
        existing = os.environ.get(ACCOUNTS_ENV, "")
        tokens = parse_accounts(existing) if existing.strip() else {}
        tokens[selector] = creds.refresh_token
        accounts_value = ";".join(f"{k}={v}" for k, v in tokens.items())
    else:
        accounts_value = f"{selector}={creds.refresh_token}"

    print(f"\nAuthorized {email} (selector: {selector})\n", file=sys.stderr)
    print("# --- Set these in the server's environment (e.g. your MCP client config) ---")
    print(f'GMAIL_CLIENT="{client_id}|{client_secret}"')
    print(f'GMAIL_ACCOUNTS="{accounts_value}"')
    if not args.merge:
        print(
            "# Add more accounts: re-run with --merge, or append "
            '";<selector>=<refresh_token>" to GMAIL_ACCOUNTS.',
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
