"""Multi-account Gmail MCP server.

Exposes Gmail operations across multiple accounts as MCP tools over stdio.
Credentials are supplied entirely through environment variables (no files on
the host): a single shared OAuth client plus one refresh token per account.
"""

__version__ = "0.1.0"

# Google OAuth scopes covering every tool in this package (Gmail + Calendar).
# Gmail:
#   - gmail.modify        : read, labels, trash, message-state changes, batch modify
#   - gmail.compose       : create/update/send drafts and send mail
#   - gmail.settings.basic: filters, signature (send-as), vacation responder
#   (We deliberately do NOT request https://mail.google.com/ — we only trash,
#    never permanently delete.)
# Calendar:
#   - calendar                  : read/write events, calendars, calendar list, ACL, free/busy, colors
#   - calendar.settings.readonly: read user calendar settings
#
# NOTE: changing this list means existing refresh tokens (granted an older scope
# set) must be re-consented via `gmail-mcp-auth` before the new APIs work.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.settings.readonly",
]
