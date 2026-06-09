"""Shared helpers for tool modules."""

from __future__ import annotations

from typing import Iterable

from ..gmail_client import GmailClient, get_client
from ..runtime import get_store


def client_for(account: str | None, password: str | None = None) -> GmailClient:
    """Resolve ``account`` + enforce the password gate, returning a :class:`GmailClient`.

    Raises ``InvalidPasswordError`` when password protection is enabled and ``password`` is
    missing or wrong, so the wrapped tool never touches Gmail.
    """
    return get_client(get_store().authenticate(account, password))


def as_list(value: str | Iterable[str] | None) -> list[str]:
    """Normalise a label/address argument that may be a single string or a list."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [v for v in value if v]
