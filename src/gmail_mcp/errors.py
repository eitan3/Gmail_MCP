"""Error types and a small retry helper for Gmail API calls."""

from __future__ import annotations

import random
import time
from typing import Any, Callable, TypeVar

try:  # googleapiclient is a runtime dependency, but keep import soft for unit tests
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - exercised only when the dep is missing
    HttpError = None  # type: ignore[assignment]


class GmailMcpError(Exception):
    """Base class for all errors surfaced by this server."""


class ConfigError(GmailMcpError):
    """Raised when the GMAIL_CLIENT / GMAIL_ACCOUNTS env vars are missing or malformed."""


class AccountNotFoundError(GmailMcpError):
    """Raised when a tool is called with an `account` selector that isn't configured."""


class GmailApiError(GmailMcpError):
    """A Gmail API call failed. Carries the HTTP status and Google's reason when available."""

    def __init__(self, message: str, status: int | None = None, reason: str | None = None):
        super().__init__(message)
        self.status = status
        self.reason = reason


T = TypeVar("T")

# HTTP statuses worth retrying with backoff (rate limits + transient server errors).
_RETRY_STATUSES = {429, 500, 502, 503, 504}


def _status_of(err: "HttpError") -> int | None:
    status = getattr(getattr(err, "resp", None), "status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def execute(request: Any, *, retries: int = 4, base_delay: float = 0.5) -> Any:
    """Execute a googleapiclient request with retry/backoff, raising GmailApiError on failure.

    `request` is the object returned by e.g. ``service.users().messages().get(...)`` —
    anything with an ``.execute()`` method.
    """
    attempt = 0
    while True:
        try:
            return request.execute()
        except Exception as err:  # noqa: BLE001 - normalise to our own error type
            if HttpError is not None and isinstance(err, HttpError):
                status = _status_of(err)
                if status in _RETRY_STATUSES and attempt < retries:
                    delay = base_delay * (2**attempt) + random.uniform(0, 0.25)
                    time.sleep(delay)
                    attempt += 1
                    continue
                reason = None
                try:
                    reason = err._get_reason()  # type: ignore[attr-defined]
                except Exception:  # pragma: no cover
                    reason = str(err)
                raise GmailApiError(
                    f"Gmail API error ({status}): {reason}", status=status, reason=reason
                ) from err
            raise
