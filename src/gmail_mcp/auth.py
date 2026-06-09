"""Build and cache Google OAuth credentials from env-var values (no files).

Each :class:`~gmail_mcp.accounts.Account` carries the shared client id/secret and
its own refresh token. We construct a ``google.oauth2.credentials.Credentials``
object directly from those values; google-auth fetches and refreshes the
short-lived access token on demand whenever the credential is used.
"""

from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from . import SCOPES
from .accounts import Account

TOKEN_URI = "https://oauth2.googleapis.com/token"

# Credentials are cached per account selector so the access token is reused
# across tool calls (and refreshed in place when it expires).
_creds_cache: dict[str, Credentials] = {}


def build_credentials(account: Account) -> Credentials:
    """Create a fresh Credentials object for an account (not cached)."""
    return Credentials(
        token=None,
        refresh_token=account.refresh_token,
        client_id=account.client_id,
        client_secret=account.client_secret,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )


def get_credentials(account: Account) -> Credentials:
    """Return cached credentials for an account, building them on first use."""
    creds = _creds_cache.get(account.selector)
    if creds is None:
        creds = build_credentials(account)
        _creds_cache[account.selector] = creds
    return creds


def refresh_now(creds: Credentials) -> Credentials:
    """Force an immediate token refresh (used by the bootstrap auth flow / health checks)."""
    creds.refresh(Request())
    return creds
