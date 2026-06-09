"""Account model and registry.

With the shared-client OAuth model, every account uses the same ``client_id`` /
``client_secret`` and differs only by its refresh token. An :class:`Account`
bundles those three values plus the human-facing ``selector`` used to pick it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import AccountNotFoundError


@dataclass(frozen=True)
class Account:
    """Everything needed to mint credentials for one Gmail mailbox."""

    selector: str  # alias or email used to choose this account in tool calls
    client_id: str
    client_secret: str
    refresh_token: str


class AccountStore:
    """Holds the configured accounts and resolves a tool's ``account`` argument."""

    def __init__(self, client_id: str, client_secret: str, tokens: dict[str, str]):
        self._client_id = client_id
        self._client_secret = client_secret
        # Preserve insertion order so the single-account fast path is deterministic.
        self._accounts: dict[str, Account] = {
            selector: Account(selector, client_id, client_secret, token)
            for selector, token in tokens.items()
        }

    @property
    def selectors(self) -> list[str]:
        return list(self._accounts.keys())

    def __len__(self) -> int:
        return len(self._accounts)

    def resolve(self, selector: str | None) -> Account:
        """Return the requested account.

        - ``selector`` given: look it up (case-insensitive), else raise.
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

        if selector in self._accounts:
            return self._accounts[selector]

        # Case-insensitive fallback (emails/aliases are not case-sensitive in practice).
        lowered = selector.lower()
        for key, account in self._accounts.items():
            if key.lower() == lowered:
                return account

        raise AccountNotFoundError(
            f"Unknown account '{selector}'. Configured accounts: "
            + (", ".join(self.selectors) or "(none)")
        )
