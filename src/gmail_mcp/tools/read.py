"""Read & search tools: get_profile, get_message, search_messages, search_threads, get_thread."""

from __future__ import annotations

from ._common import client_for

_SUMMARY_HEADERS = ["From", "To", "Subject", "Date"]


def _summaries(client, messages: list[dict]) -> list[dict]:
    """Fetch lightweight metadata (headers + snippet) for a list of message stubs."""
    out = []
    for stub in messages:
        msg = client.execute(
            client.users.messages().get(
                userId="me", id=stub["id"], format="metadata", metadataHeaders=_SUMMARY_HEADERS
            )
        )
        headers = client.headers_dict(msg.get("payload", {}))
        out.append(
            {
                "id": msg.get("id"),
                "threadId": msg.get("threadId"),
                "labelIds": msg.get("labelIds", []),
                "snippet": msg.get("snippet"),
                "from": headers.get("From"),
                "to": headers.get("To"),
                "subject": headers.get("Subject"),
                "date": headers.get("Date"),
            }
        )
    return out


def register(mcp) -> None:
    @mcp.tool()
    def get_profile(account: str | None = None) -> dict:
        """Get the Gmail profile (email address, message/thread totals, historyId).

        `account`: which configured account to use (alias or email). Optional when only one
        account is configured.
        """
        c = client_for(account)
        return c.execute(c.users.getProfile(userId="me"))

    @mcp.tool()
    def get_message(message_id: str, include_body: bool = True, account: str | None = None) -> dict:
        """Get a single message fully decoded: headers, snippet, text/HTML body, attachment list."""
        c = client_for(account)
        msg = c.fetch_message(message_id, "full")
        return c.render_message(msg, include_body=include_body)

    @mcp.tool()
    def search_messages(
        query: str = "",
        max_results: int = 25,
        page_token: str | None = None,
        include_spam_trash: bool = False,
        account: str | None = None,
    ) -> dict:
        """Search messages using Gmail query syntax (e.g. 'is:unread from:alice newer_than:7d').

        Returns message summaries plus `next_page_token` for pagination.
        """
        c = client_for(account)
        resp = c.execute(
            c.users.messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
                pageToken=page_token,
                includeSpamTrash=include_spam_trash,
            )
        )
        return {
            "messages": _summaries(c, resp.get("messages", [])),
            "next_page_token": resp.get("nextPageToken"),
            "result_size_estimate": resp.get("resultSizeEstimate"),
        }

    @mcp.tool()
    def search_threads(
        query: str = "",
        max_results: int = 25,
        page_token: str | None = None,
        include_spam_trash: bool = False,
        account: str | None = None,
    ) -> dict:
        """Search threads using Gmail query syntax. Returns thread stubs + `next_page_token`."""
        c = client_for(account)
        resp = c.execute(
            c.users.threads().list(
                userId="me",
                q=query,
                maxResults=max_results,
                pageToken=page_token,
                includeSpamTrash=include_spam_trash,
            )
        )
        return {
            "threads": resp.get("threads", []),
            "next_page_token": resp.get("nextPageToken"),
            "result_size_estimate": resp.get("resultSizeEstimate"),
        }

    @mcp.tool()
    def get_thread(
        thread_id: str, include_body: bool = True, account: str | None = None
    ) -> dict:
        """Get a full thread with every message decoded."""
        c = client_for(account)
        thread = c.execute(c.users.threads().get(userId="me", id=thread_id, format="full"))
        return {
            "id": thread.get("id"),
            "historyId": thread.get("historyId"),
            "messages": [
                c.render_message(m, include_body=include_body)
                for m in thread.get("messages", [])
            ],
        }
