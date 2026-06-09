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
PASSWORDS_ENV = "PASSWORDS"

# Accounts/passwords are separated by ';' or any newline/CR; surrounding whitespace ignored.
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
        if any(selector.casefold() == existing.casefold() for existing in tokens):
            raise ConfigError(
                f"{ACCOUNTS_ENV} has a duplicate account selector (case-insensitive): '{selector}'."
            )
        tokens[selector] = token
    if not tokens:
        raise ConfigError(f"{ACCOUNTS_ENV} did not contain any 'selector=refresh_token' entries.")
    return tokens


def parse_passwords(raw: str) -> dict[str, str]:
    """Split ``PASSWORDS`` into {selector: password}.

    Same shape as ``GMAIL_ACCOUNTS``: ``selector=password`` pairs separated by ';' or
    newlines, split on the first '='. Passwords therefore must not contain '=' or ';'.
    """
    passwords: dict[str, str] = {}
    for chunk in _ACCOUNT_SPLIT.split(raw):
        pair = chunk.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ConfigError(
                f"{PASSWORDS_ENV} entry '{pair}' is not 'selector=password'."
            )
        selector, password = pair.split("=", 1)
        selector, password = selector.strip(), password.strip()
        if not selector or not password:
            raise ConfigError(
                f"{PASSWORDS_ENV} has an entry with an empty selector or password: '{pair}'."
            )
        if any(selector.casefold() == existing.casefold() for existing in passwords):
            raise ConfigError(
                f"{PASSWORDS_ENV} has a duplicate account selector (case-insensitive): '{selector}'."
            )
        passwords[selector] = password
    return passwords


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

    # PASSWORDS is optional. When present with real content it turns on the password gate:
    # every tool call must then supply the matching password for its account.
    passwords_raw = env.get(PASSWORDS_ENV)
    passwords: dict[str, str] = {}
    if passwords_raw is not None and passwords_raw.strip():
        passwords = parse_passwords(passwords_raw)
        if not passwords:
            # Non-empty but content-free (e.g. only ';'/newlines): fail closed rather than
            # silently disabling protection the operator believes is on.
            raise ConfigError(
                f"{PASSWORDS_ENV} is set but contains no valid 'selector=password' entries."
            )
        account_keys = {s.casefold() for s in tokens}
        unknown = [sel for sel in passwords if sel.casefold() not in account_keys]
        if unknown:
            raise ConfigError(
                f"{PASSWORDS_ENV} references account(s) not present in {ACCOUNTS_ENV}: "
                + ", ".join(unknown)
            )

    return AccountStore(client_id, client_secret, tokens, passwords=passwords)
