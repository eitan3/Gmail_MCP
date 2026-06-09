# Gmail MCP Server

A multi-account [Model Context Protocol](https://modelcontextprotocol.io) server for Gmail.
Runs over **stdio**, installs via **uvx**, and takes **all credentials from environment
variables** — the host running the server never needs a `credentials.json` or `token.json` file.

- One shared Google OAuth "Desktop" client authorizes every account.
- Each account contributes only its **refresh token**.
- Every tool takes an optional `account` argument to pick the mailbox.

## How credentials work (2 env vars)

| Variable | Format | Example |
| --- | --- | --- |
| `GMAIL_CLIENT` | `client_id\|client_secret` | `123-abc.apps.googleusercontent.com\|GOCSPX-xxxx` |
| `GMAIL_ACCOUNTS` | `selector=refresh_token` pairs, separated by `;` or newlines | `alice@gmail.com=1//0gFoo;work=1//0gBar` |

The `selector` defaults to the account's email but you can rename it to a short alias
(`work`, `personal`). You never hand-write these values — the `gmail-mcp-auth` command prints them.

## One-time setup

### 1. Create a Google OAuth client (once)

1. In [Google Cloud Console](https://console.cloud.google.com/) create/select a project.
2. Enable the **Gmail API**.
3. Configure the **OAuth consent screen** (External is fine; add yourself as a Test user, or publish).
4. Create **OAuth client ID → Desktop app**. Note the **client id** and **client secret**.

### 2. Authorize each account (on a machine with a browser)

```bash
uvx --from . gmail-mcp-auth --client-id <ID> --client-secret <SECRET>
# or, after publishing the package:
uvx gmail-mcp-auth --client-id <ID> --client-secret <SECRET>
```

A browser opens for Google consent. On success the command prints:

```
GMAIL_CLIENT="<id>|<secret>"
GMAIL_ACCOUNTS="alice@gmail.com=1//0g..."
```

Add more accounts (re-uses the client from `GMAIL_CLIENT` in your env if set):

```bash
gmail-mcp-auth --merge --alias work     # prints the full merged GMAIL_ACCOUNTS
```

Headless host? Use `--no-browser` and open the printed URL yourself (forward the redirect
port over SSH if consent happens on another machine).

### 3. Configure your MCP client

```json
{
  "mcpServers": {
    "gmail": {
      "command": "uvx",
      "args": ["gmail-mcp"],
      "env": {
        "GMAIL_CLIENT": "…id…|…secret…",
        "GMAIL_ACCOUNTS": "alice@gmail.com=1//0g…;work=1//0g…"
      }
    }
  }
}
```

## Tools

**Send** `send_email` · `reply_to_message` · `forward_message`
**Drafts** `create_draft` · `list_drafts` · `send_draft` · `update_draft` · `delete_draft`
**Read** `get_profile` · `get_message` · `search_messages` · `search_threads` · `get_thread`
**Attachments** `get_message_attachments` · `download_attachment`
**Trash** `trash_message` · `untrash_message` · `trash_thread` · `untrash_thread`
**Labels** `list_labels` · `create_label` · `update_label` · `delete_label` ·
`label_message` · `unlabel_message` · `label_thread` · `unlabel_thread`
**Filters** `list_filters` · `create_filter` · `delete_filter`
**Signature** `get_signature` · `update_signature`
**Vacation** `get_vacation_responder` · `set_vacation_responder`
**State (extra)** `mark_read` · `mark_unread` · `star` · `unstar` · `archive` ·
`move_to_inbox` · `mark_important` · `mark_not_important`
**Batch (extra)** `batch_modify_messages` · `batch_trash` · `batch_untrash`

Every tool accepts `account` (alias or email). With a single configured account it's optional;
with several, omitting it returns an error listing the available selectors.

Label arguments accept human names (e.g. `Clients/Acme`) or raw label ids. Search tools use
[Gmail query syntax](https://support.google.com/mail/answer/7190) (e.g. `is:unread from:alice
newer_than:7d`).

## Scopes

`gmail.modify`, `gmail.compose`, `gmail.settings.basic`. No permanent delete — only Trash.

## Local development

```bash
uv sync --extra dev
uv run gmail-mcp-auth --client-id <ID> --client-secret <SECRET>   # mint a token
$env:GMAIL_CLIENT="…"; $env:GMAIL_ACCOUNTS="…"                     # PowerShell
uv run gmail-mcp                                                   # run the server (stdio)
npx @modelcontextprotocol/inspector uv run gmail-mcp              # interactive tool testing
uv run pytest                                                      # unit tests
```
