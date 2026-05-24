from __future__ import annotations

"""
Gmail API integration — create drafts in PM's personal inbox.
Scopes: gmail.compose (drafts/send), gmail.readonly (read inbox+sent for thread context).
"""
import base64
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown as md
from googleapiclient.discovery import build

from auth.google_oauth import get_credentials_for_pm


def _markdown_to_html(text: str) -> str:
    """Convert markdown body to a clean HTML email."""
    html_body = md.markdown(text, extensions=["nl2br"])
    return f"""<html><body style="font-family:sans-serif;font-size:14px;line-height:1.6;color:#222;max-width:680px">
{html_body}
</body></html>"""


def create_gmail_draft(
    pm_id: str,
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> str:
    """
    Creates a Gmail draft and returns the gmail_draft_id.
    Sends as multipart/alternative with plain text + HTML so formatting renders.
    If to_email is empty/invalid, draft is created without a To header so the
    PM can fill it in manually.
    """
    creds = get_credentials_for_pm(pm_id)
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart("alternative")
    # Only set To header if we have a valid email — Gmail rejects empty/invalid To
    if to_email and "@" in to_email:
        to_header = f"{to_name} <{to_email}>" if to_name else to_email
        msg["To"] = to_header
    msg["Subject"] = subject

    # Plain text fallback (strip markdown symbols minimally)
    msg.attach(MIMEText(body, "plain"))
    # HTML version with rendered markdown
    msg.attach(MIMEText(_markdown_to_html(body), "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    result = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}},
    ).execute()

    return result["id"]


def update_gmail_draft(
    pm_id: str,
    gmail_draft_id: str,
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> None:
    """
    Enhancement 3: Replace an existing Gmail draft with a regenerated body.
    The draft_id stays the same — it updates in-place.
    """
    creds = get_credentials_for_pm(pm_id)
    service = build("gmail", "v1", credentials=creds)

    to_header = f"{to_name} <{to_email}>" if to_name else to_email

    msg = MIMEMultipart("alternative")
    msg["To"] = to_header
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(_markdown_to_html(body), "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service.users().drafts().update(
        userId="me",
        id=gmail_draft_id,
        body={"message": {"raw": raw}},
    ).execute()


def _extract_plain_text(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        result = _extract_plain_text(part)
        if result:
            return result
    return ""


def _get_header(msg: dict, name: str) -> str:
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def get_emails_with_client(
    pm_id: str,
    client_email: str,
    after_date: str,
    before_date: str,
) -> list[dict]:
    """
    Return all emails exchanged with a client's domain between two dates.
    Searches both inbox (from them) and sent (to them), sorted oldest → newest.
    Requires gmail.readonly scope.

    after_date / before_date: ISO date strings e.g. "2026-04-07"
    """
    if not client_email or "@" not in client_email:
        return []

    domain = client_email.split("@")[1]
    after = after_date[:10].replace("-", "/")
    before = before_date[:10].replace("-", "/")
    query = f"(from:@{domain} OR to:@{domain}) after:{after} before:{before}"

    creds = get_credentials_for_pm(pm_id)
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", q=query, maxResults=30
    ).execute()

    messages = results.get("messages", [])
    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        body = _extract_plain_text(msg.get("payload", {})).strip()
        if not body:
            continue

        internal_date_ms = int(msg.get("internalDate", 0))
        dt = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d %I:%M%p UTC")

        emails.append({
            "internal_date_ms": internal_date_ms,
            "date_str": date_str,
            "from_header": _get_header(msg, "from"),
            "to_header": _get_header(msg, "to"),
            "subject": _get_header(msg, "subject"),
            "body_text": body[:500],  # truncate to keep token usage bounded
        })

    # Sort oldest → newest
    emails.sort(key=lambda e: e["internal_date_ms"])
    # Remove the sort key before returning
    for e in emails:
        del e["internal_date_ms"]

    return emails


def get_sent_messages_since(pm_id: str, since_timestamp: str) -> list[dict]:
    """
    Returns SENT messages after since_timestamp (RFC 3339 string).
    Used by edit detection job.
    """
    creds = get_credentials_for_pm(pm_id)
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me",
        labelIds=["SENT"],
        q=f"after:{since_timestamp}",
    ).execute()

    messages = results.get("messages", [])
    full_messages = []
    for msg in messages:
        full = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()
        full_messages.append(full)

    return full_messages
