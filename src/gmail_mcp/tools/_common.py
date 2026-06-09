"""Shared helpers for tool modules."""

from __future__ import annotations

from typing import Iterable

from ..calendar_client import CalendarClient, get_calendar_client
from ..gmail_client import GmailClient, get_client
from ..runtime import get_store


def client_for(account: str | None, password: str | None = None) -> GmailClient:
    """Resolve ``account`` + enforce the password gate, returning a :class:`GmailClient`.

    Raises ``InvalidPasswordError`` when password protection is enabled and ``password`` is
    missing or wrong, so the wrapped tool never touches Gmail.
    """
    return get_client(get_store().authenticate(account, password))


def calendar_for(account: str | None, password: str | None = None) -> CalendarClient:
    """Resolve ``account`` + enforce the password gate, returning a :class:`CalendarClient`.

    Same gate as :func:`client_for` (shared ``AccountStore.authenticate``), so every Calendar
    tool is password-protected exactly like the Gmail tools.
    """
    return get_calendar_client(get_store().authenticate(account, password))


def as_list(value: str | Iterable[str] | None) -> list[str]:
    """Normalise a label/address argument that may be a single string or a list."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [v for v in value if v]
