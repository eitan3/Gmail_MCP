"""Account model and registry.

With the shared-client OAuth model, every account uses the same ``client_id`` /
``client_secret`` and differs only by its refresh token. An :class:`Account`
bundles those three values plus the human-facing ``selector`` used to pick it.

Selectors are matched case-insensitively. To keep that matching unambiguous, the
store indexes accounts and passwords by the *casefolded* selector, and the config
layer rejects selectors that collide case-insensitively. This guarantees a password
can only ever unlock the exact account it was configured for.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from .errors import AccountNotFoundError, InvalidPasswordError


@dataclass(frozen=True)
class Account:
    """Everything needed to mint credentials for one Gmail mailbox."""

    selector: str  # alias or email used to choose this account in tool calls
    client_id: str
    client_secret: str
    refresh_token: str


class AccountStore:
    """Holds the configured accounts and resolves a tool's ``account`` argument."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tokens: dict[str, str],
        passwords: dict[str, str] | None = None,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        # Index by casefolded selector for unambiguous case-insensitive lookup, while the
        # Account keeps the original-case selector for display. Insertion order preserved.
        self._accounts: dict[str, Account] = {}
        for selector, token in tokens.items():
            self._accounts[selector.casefold()] = Account(
                selector, client_id, client_secret, token
            )
        self._passwords: dict[str, str] = {
            selector.casefold(): pw for selector, pw in (passwords or {}).items()
        }

    @property
    def selectors(self) -> list[str]:
        """Display selectors (original case), in configuration order."""
        return [a.selector for a in self._accounts.values()]

    @property
    def password_gate_enabled(self) -> bool:
        """True when a non-empty PASSWORDS map was configured — passwords are then required."""
        return bool(self._passwords)

    def __len__(self) -> int:
        return len(self._accounts)

    def accounts_without_password(self) -> list[str]:
        """Display selectors that have no configured password (locked while the gate is on)."""
        return [a.selector for key, a in self._accounts.items() if key not in self._passwords]

    def resolve(self, selector: str | None) -> Account:
        """Return the requested account.

        - ``selector`` given: look it up (case-insensitively), else raise.
        - ``selector`` omitted and exactly one account configured: use it.
        - ``selector`` omitted and multiple accounts: raise, listing the choices.
        """
        if selector is None or selector == "":
            if len(self._accounts) == 1:
                return next(iter(self._accounts.values()))
            raise AccountNotFoundError(
                "Multiple Gmail accounts are configured; pass `account` with one of: "
                + ", ".join(self.selectors)
            )

        account = self._accounts.get(selector.casefold())
        if account is not None:
            return account

        raise AccountNotFoundError(
            f"Unknown account '{selector}'. Configured accounts: "
            + (", ".join(self.selectors) or "(none)")
        )

    def authenticate(self, selector: str | None, password: str | None) -> Account:
        """Resolve an account AND enforce the password gate (when enabled).

        - Always resolves the account first (raising AccountNotFoundError if unknown / if a
          selector is required but omitted).
        - When the gate is enabled, the supplied ``password`` must match the account's
          configured password using a constant-time comparison; otherwise
          :class:`InvalidPasswordError` is raised. An account with no configured password is
          treated as locked (no password can satisfy it).
        """
        account = self.resolve(selector)
        if not self.password_gate_enabled:
            return account

        expected = self._passwords.get(account.selector.casefold())
        if expected is None:
            raise InvalidPasswordError(
                f"Invalid password: no password is configured for account '{account.selector}'."
            )
        # Encode to bytes so non-ASCII passwords compare correctly (compare_digest rejects
        # non-ASCII str). Comparison is constant-time to avoid leaking length/contents via timing.
        if password is None or not hmac.compare_digest(
            str(password).encode("utf-8"), str(expected).encode("utf-8")
        ):
            raise InvalidPasswordError(
                f"Invalid password for account '{account.selector}'."
            )
        return account
