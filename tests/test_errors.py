from gmail_mcp.errors import _is_retryable


def test_retry_on_transient_statuses():
    for status in (429, 500, 502, 503, 504):
        assert _is_retryable(status, "whatever") is True


def test_retry_on_403_rate_limit():
    assert _is_retryable(403, "Rate Limit Exceeded") is True
    assert _is_retryable(403, "User Rate Limit Exceeded") is True
    assert _is_retryable(403, "Quota exceeded for quota metric") is True


def test_no_retry_on_403_permission_or_scope():
    assert _is_retryable(403, "Request had insufficient authentication scopes.") is False
    assert _is_retryable(403, "The user does not have permission") is False


def test_no_retry_on_client_errors():
    assert _is_retryable(404, "Not Found") is False
    assert _is_retryable(400, "Bad Request") is False
    assert _is_retryable(401, "Invalid Credentials") is False
