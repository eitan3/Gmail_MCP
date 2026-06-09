import base64
import email
from email import policy

from gmail_mcp.gmail_client import GmailClient, build_mime, raw_of, split_addresses


def _decode_raw(raw: str):
    padded = raw + "=" * (-len(raw) % 4)
    return email.message_from_bytes(base64.urlsafe_b64decode(padded), policy=policy.default)


def test_build_mime_headers_and_body():
    msg = build_mime(
        to=["a@x.com", "b@x.com"],
        cc="c@x.com",
        subject="Hi",
        body_text="hello",
    )
    parsed = _decode_raw(raw_of(msg))
    assert parsed["To"] == "a@x.com, b@x.com"
    assert parsed["Cc"] == "c@x.com"
    assert parsed["Subject"] == "Hi"
    assert "hello" in parsed.get_content()


def test_build_mime_html_alternative():
    msg = build_mime(to="a@x.com", subject="H", body_text="plain", body_html="<b>rich</b>")
    parsed = _decode_raw(raw_of(msg))
    assert parsed.is_multipart()
    subtypes = {p.get_content_subtype() for p in parsed.walk() if not p.is_multipart()}
    assert {"plain", "html"} <= subtypes


def test_split_addresses():
    assert split_addresses("Alice <a@x.com>, b@x.com") == ["a@x.com", "b@x.com"]
    assert split_addresses(None) == []


def test_render_message_decodes_body_and_attachments():
    text = base64.urlsafe_b64encode(b"body text").decode()
    msg = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX"],
        "snippet": "snip",
        "payload": {
            "headers": [{"name": "Subject", "value": "Hello"}, {"name": "From", "value": "x@y.com"}],
            "mimeType": "multipart/mixed",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": text}},
                {
                    "mimeType": "application/pdf",
                    "filename": "doc.pdf",
                    "body": {"attachmentId": "att1", "size": 10},
                },
            ],
        },
    }
    out = GmailClient.render_message(msg)
    assert out["subject"] == "Hello"
    assert out["from"] == "x@y.com"
    assert out["body_text"] == "body text"
    assert out["attachments"][0]["filename"] == "doc.pdf"
    assert out["attachments"][0]["attachmentId"] == "att1"
