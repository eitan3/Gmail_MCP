"""Shared helpers for tool modules."""

from __future__ import annotations

from typing import Iterable

from ..gmail_client import GmailClient, get_client
from ..runtime import get_store


def client_for(account: str | None) -> GmailClient:
    """Resolve the ``account`` selector to a ready-to-use :class:`GmailClient`."""
    return get_client(get_store().resolve(account))


def as_list(value: str | Iterable[str] | None) -> list[str]:
    """Normalise a label/address argument that may be a single string or a list."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [v for v in value if v]
