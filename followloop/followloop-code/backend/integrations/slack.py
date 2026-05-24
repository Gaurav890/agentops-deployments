from __future__ import annotations

"""
Slack integration — DM the PM when their Gmail draft is ready.
Slack is optional: if SLACK_BOT_TOKEN is not set, notifications are silently skipped.
"""
import os


def _get_client():
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        return None
    from slack_sdk import WebClient
    return WebClient(token=token)


def notify_pm(slack_user_id: str, client_name: str, meeting_type: str) -> None:
    """DM the PM with a Block Kit message linking to Gmail Drafts."""
    client = _get_client()
    if not client:
        print("[slack] SLACK_BOT_TOKEN not set — skipping PM notification")
        return

    meeting_type_display = meeting_type.replace("_", " ").title()
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":email: *New meeting summary draft ready*\n"
                    f"Meeting with *{client_name}* ({meeting_type_display})\n"
                    f"Your draft is waiting in Gmail."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Gmail Drafts"},
                    "url": "https://mail.google.com/mail/u/0/#drafts",
                    "style": "primary",
                }
            ],
        },
    ]

    try:
        client.chat_postMessage(channel=slack_user_id, blocks=blocks)
    except Exception as e:
        print(f"[slack] Failed to notify PM {slack_user_id}: {e}")


def notify_eng_alert(message: str) -> None:
    """Post to #eng-alerts. No-ops silently if Slack is not configured."""
    client = _get_client()
    if not client:
        return
    try:
        client.chat_postMessage(channel="#eng-alerts", text=message)
    except Exception as e:
        print(f"[slack] Failed to send eng-alert: {e}")


def post_internal_note(
    pm_name: str,
    client_name: str,
    meeting_type: str,
    internal_note: str,
    channel: str | None = None,
) -> None:
    """
    Enhancement 2: Post candid internal meeting note to a shared CS team channel.
    No-ops silently if SLACK_BOT_TOKEN or SLACK_INTERNAL_CHANNEL not set.
    """
    client = _get_client()
    if not client:
        print("[slack] SLACK_BOT_TOKEN not set — skipping internal note")
        return

    target = channel or os.environ.get("SLACK_INTERNAL_CHANNEL", "")
    if not target:
        print("[slack] SLACK_INTERNAL_CHANNEL not set — skipping internal note")
        return

    meeting_type_display = meeting_type.replace("_", " ").title()
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{client_name} ({meeting_type_display}) — {pm_name}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": internal_note},
        },
        {"type": "divider"},
    ]

    try:
        client.chat_postMessage(channel=target, blocks=blocks)
    except Exception as e:
        print(f"[slack] Failed to post internal note to {target}: {e}")


def lookup_slack_user_id(email: str) -> str | None:
    """Look up a PM's Slack user ID by email. Returns None if Slack not configured."""
    client = _get_client()
    if not client:
        return None
    try:
        res = client.users_lookupByEmail(email=email)
        return res["user"]["id"]
    except Exception:
        return None
