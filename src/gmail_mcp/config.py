"""Parse the two environment variables into an :class:`AccountStore`.

The deployment host has no credential files; everything arrives as env vars:

    GMAIL_CLIENT   = "<client_id>|<client_secret>"
    GMAIL_ACCOUNTS = "<selector>=<refresh_token>;<selector>=<refresh_token>;..."

Accounts may also be separated by newlines instead of ';'. Each pair is split on
the *first* '=' only, since refresh tokens never contain '=' but may contain
other punctuation.
"""

from __future__ import annotations

import os
import re

from .accounts import AccountStore
from .errors import ConfigError

CLIENT_ENV = "GMAIL_CLIENT"
ACCOUNTS_ENV = "GMAIL_ACCOUNTS"

# Accounts are separated by ';' or any newline/CR; surrounding whitespace ignored.
_ACCOUNT_SPLIT = re.compile(r"[;\r\n]+")


def parse_client(raw: str) -> tuple[str, str]:
    """Split ``GMAIL_CLIENT`` into (client_id, client_secret)."""
    raw = raw.strip()
    if "|" not in raw:
        raise ConfigError(
            f"{CLIENT_ENV} must be '<client_id>|<client_secret>' (missing '|' separator)."
        )
    client_id, client_secret = raw.split("|", 1)
    client_id, client_secret = client_id.strip(), client_secret.strip()
    if not client_id or not client_secret:
        raise ConfigError(f"{CLIENT_ENV} has an empty client_id or client_secret.")
    return client_id, client_secret


def parse_accounts(raw: str) -> dict[str, str]:
    """Split ``GMAIL_ACCOUNTS`` into {selector: refresh_token}."""
    tokens: dict[str, str] = {}
    for chunk in _ACCOUNT_SPLIT.split(raw):
        pair = chunk.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ConfigError(
                f"{ACCOUNTS_ENV} entry '{pair}' is not 'selector=refresh_token'."
            )
        selector, token = pair.split("=", 1)
        selector, token = selector.strip(), token.strip()
        if not selector or not token:
            raise ConfigError(
                f"{ACCOUNTS_ENV} has an entry with an empty selector or token: '{pair}'."
            )
        if selector in tokens:
            raise ConfigError(f"{ACCOUNTS_ENV} has a duplicate account selector: '{selector}'.")
        tokens[selector] = token
    if not tokens:
        raise ConfigError(f"{ACCOUNTS_ENV} did not contain any 'selector=refresh_token' entries.")
    return tokens


def load_account_store(env: dict[str, str] | None = None) -> AccountStore:
    """Build an :class:`AccountStore` from the process environment."""
    env = os.environ if env is None else env

    client_raw = env.get(CLIENT_ENV)
    if not client_raw:
        raise ConfigError(
            f"Missing {CLIENT_ENV}. Run `gmail-mcp-auth` to generate it, then set it in the "
            f"server's environment."
        )
    accounts_raw = env.get(ACCOUNTS_ENV)
    if not accounts_raw:
        raise ConfigError(
            f"Missing {ACCOUNTS_ENV}. Run `gmail-mcp-auth` to authorize at least one account."
        )

    client_id, client_secret = parse_client(client_raw)
    tokens = parse_accounts(accounts_raw)
    return AccountStore(client_id, client_secret, tokens)
