"""Settings tools: signature (send-as) and vacation responder."""

from __future__ import annotations

from ._common import client_for


def register(mcp) -> None:
    @mcp.tool()
    def get_signature(
        send_as: str | None = None, account: str | None = None, password: str | None = None
    ) -> dict:
        """Get the HTML signature for a send-as address (defaults to the primary address)."""
        c = client_for(account, password)
        addr = send_as or c.email_address()
        sa = c.execute(c.users.settings().sendAs().get(userId="me", sendAsEmail=addr))
        return {"sendAsEmail": addr, "signature": sa.get("signature", "")}

    @mcp.tool()
    def update_signature(
        signature_html: str,
        send_as: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Set the HTML signature for a send-as address (defaults to the primary address)."""
        c = client_for(account, password)
        addr = send_as or c.email_address()
        sa = c.execute(
            c.users.settings()
            .sendAs()
            .patch(userId="me", sendAsEmail=addr, body={"signature": signature_html})
        )
        return {"sendAsEmail": addr, "signature": sa.get("signature", "")}

    @mcp.tool()
    def get_vacation_responder(
        account: str | None = None, password: str | None = None
    ) -> dict:
        """Get the vacation responder (auto-reply) settings."""
        c = client_for(account, password)
        return c.execute(c.users.settings().getVacation(userId="me"))

    @mcp.tool()
    def set_vacation_responder(
        enabled: bool,
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        restrict_to_contacts: bool | None = None,
        restrict_to_domain: bool | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        account: str | None = None,
        password: str | None = None,
    ) -> dict:
        """Enable or disable the vacation responder.

        `start_time`/`end_time` are epoch-milliseconds strings (omit for no bound).
        `restrict_to_contacts`/`restrict_to_domain` limit who receives the auto-reply.
        """
        c = client_for(account, password)
        body: dict = {"enableAutoReply": enabled}
        if subject is not None:
            body["responseSubject"] = subject
        if body_text is not None:
            body["responseBodyPlainText"] = body_text
        if body_html is not None:
            body["responseBodyHtml"] = body_html
        if restrict_to_contacts is not None:
            body["restrictToContacts"] = restrict_to_contacts
        if restrict_to_domain is not None:
            body["restrictToDomain"] = restrict_to_domain
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        return c.execute(c.users.settings().updateVacation(userId="me", body=body))
