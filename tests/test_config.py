import pytest

from gmail_mcp.accounts import AccountStore
from gmail_mcp.config import load_account_store, parse_accounts, parse_client, parse_passwords
from gmail_mcp.errors import AccountNotFoundError, ConfigError, InvalidPasswordError


def test_parse_client_ok():
    assert parse_client("id.apps.googleusercontent.com|GOCSPX-secret") == (
        "id.apps.googleusercontent.com",
        "GOCSPX-secret",
    )


def test_parse_client_missing_pipe():
    with pytest.raises(ConfigError):
        parse_client("just-an-id")


def test_parse_accounts_semicolon_and_newline():
    raw = "alice@gmail.com=1//tokenA;\n work=1//tokenB \n"
    assert parse_accounts(raw) == {"alice@gmail.com": "1//tokenA", "work": "1//tokenB"}


def test_parse_accounts_splits_on_first_equals():
    # Refresh tokens shouldn't contain '=', but split must be on the first one regardless.
    assert parse_accounts("a@b.com=1//tok==tail") == {"a@b.com": "1//tok==tail"}


def test_parse_accounts_rejects_duplicates():
    with pytest.raises(ConfigError):
        parse_accounts("a@b.com=1;a@b.com=2")


def test_parse_accounts_rejects_empty():
    with pytest.raises(ConfigError):
        parse_accounts("   ")


def test_load_account_store_from_env():
    env = {
        "GMAIL_CLIENT": "cid|csecret",
        "GMAIL_ACCOUNTS": "alice@gmail.com=1//A;work=1//B",
    }
    store = load_account_store(env)
    assert store.selectors == ["alice@gmail.com", "work"]
    assert store.resolve("work").refresh_token == "1//B"
    assert store.resolve("work").client_id == "cid"


def test_store_single_account_default_resolves():
    store = AccountStore("cid", "csec", {"only@x.com": "tok"})
    assert store.resolve(None).selector == "only@x.com"


def test_store_multi_account_requires_selector():
    store = AccountStore("cid", "csec", {"a@x.com": "t1", "b@x.com": "t2"})
    with pytest.raises(AccountNotFoundError):
        store.resolve(None)


def test_store_case_insensitive_and_unknown():
    store = AccountStore("cid", "csec", {"Alice@X.com": "t"})
    assert store.resolve("alice@x.com").refresh_token == "t"
    with pytest.raises(AccountNotFoundError):
        store.resolve("nope")


# --------------------------------------------------------------------------- #
# Password gate
# --------------------------------------------------------------------------- #
def test_parse_passwords():
    assert parse_passwords("a@b.com=secret1;work=secret2") == {"a@b.com": "secret1", "work": "secret2"}


def test_parse_passwords_rejects_malformed():
    with pytest.raises(ConfigError):
        parse_passwords("no-equals-sign")
    with pytest.raises(ConfigError):
        parse_passwords("a@b.com=p;a@b.com=q")  # duplicate


def test_gate_disabled_when_no_passwords():
    store = AccountStore("cid", "csec", {"a@x.com": "t"})
    assert store.password_gate_enabled is False
    # password is ignored when the gate is off
    assert store.authenticate("a@x.com", None).selector == "a@x.com"
    assert store.authenticate("a@x.com", "whatever").selector == "a@x.com"


def test_load_account_store_enables_gate():
    env = {
        "GMAIL_CLIENT": "cid|csecret",
        "GMAIL_ACCOUNTS": "a@x.com=1//A;work=1//B",
        "PASSWORDS": "a@x.com=pw1;work=pw2",
    }
    store = load_account_store(env)
    assert store.password_gate_enabled is True
    assert store.authenticate("work", "pw2").refresh_token == "1//B"


def test_authenticate_wrong_and_missing_password():
    store = AccountStore("cid", "csec", {"a@x.com": "t"}, passwords={"a@x.com": "pw"})
    assert store.authenticate("a@x.com", "pw").selector == "a@x.com"
    with pytest.raises(InvalidPasswordError):
        store.authenticate("a@x.com", "wrong")
    with pytest.raises(InvalidPasswordError):
        store.authenticate("a@x.com", None)


def test_authenticate_account_without_password_is_locked():
    # Gate on, but this account has no configured password -> no password can unlock it.
    store = AccountStore("cid", "csec", {"a@x.com": "t", "b@x.com": "t2"}, passwords={"a@x.com": "pw"})
    with pytest.raises(InvalidPasswordError):
        store.authenticate("b@x.com", "pw")
    with pytest.raises(InvalidPasswordError):
        store.authenticate("b@x.com", None)


def test_authenticate_unknown_account_still_raises_not_found():
    store = AccountStore("cid", "csec", {"a@x.com": "t"}, passwords={"a@x.com": "pw"})
    with pytest.raises(AccountNotFoundError):
        store.authenticate("nope", "pw")


# --------------------------------------------------------------------------- #
# Hardening (from adversarial audit)
# --------------------------------------------------------------------------- #
def test_parse_accounts_rejects_case_insensitive_duplicate():
    with pytest.raises(ConfigError):
        parse_accounts("Alice=1//A;alice=1//B")


def test_parse_passwords_rejects_case_insensitive_duplicate():
    with pytest.raises(ConfigError):
        parse_passwords("Work=p1;work=p2")


def test_separator_only_passwords_fail_closed():
    # Content-free but non-empty PASSWORDS must error, not silently disable the gate.
    env = {"GMAIL_CLIENT": "cid|csec", "GMAIL_ACCOUNTS": "a@x.com=1//A", "PASSWORDS": ";;;"}
    with pytest.raises(ConfigError):
        load_account_store(env)


def test_empty_passwords_disables_gate():
    env = {"GMAIL_CLIENT": "cid|csec", "GMAIL_ACCOUNTS": "a@x.com=1//A", "PASSWORDS": "   "}
    store = load_account_store(env)
    assert store.password_gate_enabled is False


def test_passwords_unknown_selector_rejected():
    env = {
        "GMAIL_CLIENT": "cid|csec",
        "GMAIL_ACCOUNTS": "a@x.com=1//A",
        "PASSWORDS": "typo@x.com=pw",
    }
    with pytest.raises(ConfigError):
        load_account_store(env)


def test_password_binds_to_exact_account_case_insensitively():
    # Selector case in the call or in PASSWORDS doesn't matter; it still binds to the one account.
    env = {
        "GMAIL_CLIENT": "cid|csec",
        "GMAIL_ACCOUNTS": "Work@x.com=1//W",
        "PASSWORDS": "work@x.com=secret",
    }
    store = load_account_store(env)
    assert store.authenticate("WORK@X.COM", "secret").refresh_token == "1//W"
    with pytest.raises(InvalidPasswordError):
        store.authenticate("Work@x.com", "nope")


def test_accounts_without_password_listed():
    store = AccountStore("cid", "csec", {"a@x.com": "t", "b@x.com": "t2"}, passwords={"a@x.com": "pw"})
    assert store.accounts_without_password() == ["b@x.com"]
