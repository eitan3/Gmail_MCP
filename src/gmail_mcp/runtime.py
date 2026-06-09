"""Process-wide handle to the configured :class:`AccountStore`.

The store is built once from env vars at server startup (``server.main``) and
read by every tool when resolving its ``account`` argument.
"""

from __future__ import annotations

from .accounts import AccountStore
from .errors import ConfigError

_store: AccountStore | None = None


def set_store(store: AccountStore) -> None:
    global _store
    _store = store


def get_store() -> AccountStore:
    if _store is None:
        raise ConfigError("Account store is not initialised (server did not start correctly).")
    return _store
