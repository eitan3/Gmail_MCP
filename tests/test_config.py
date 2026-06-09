import pytest

from gmail_mcp.accounts import AccountStore
from gmail_mcp.config import load_account_store, parse_accounts, parse_client
from gmail_mcp.errors import AccountNotFoundError, ConfigError


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
