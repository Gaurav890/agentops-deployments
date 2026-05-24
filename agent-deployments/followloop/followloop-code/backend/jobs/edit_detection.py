"""
Edit detection background job.
Runs every 30 minutes. For each 'pending' draft older than 20 minutes:
- Queries the PM's Gmail SENT folder
- Matches by subject + timing
- Computes diff between agent_draft and what was actually sent
- Updates draft_history record
"""
import base64
import difflib
import email
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from db.models import get_pending_drafts_older_than, update_draft_edit_info, update_draft_status, update_draft_edit_lesson
from integrations.gmail import get_sent_messages_since
from integrations.slack import notify_eng_alert


def _extract_body_from_gmail_message(msg: dict) -> str:
    """Extract plain text body from a Gmail API message object."""
    payload = msg.get("payload", {})

    def _walk(part) -> str:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for sub in part.get("parts", []):
            result = _walk(sub)
            if result:
                return result
        return ""

    return _walk(payload).strip()


def _get_subject(msg: dict) -> str:
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "subject":
            return h["value"]
    return ""


def _compute_diff(original: str, revised: str) -> dict:
    orig_lines = original.splitlines()
    rev_lines = revised.splitlines()
    removed = [line for line in orig_lines if line not in set(rev_lines)]
    added = [line for line in rev_lines if line not in set(orig_lines)]
    return {"removed": removed, "added": added}


def run_edit_detection_once() -> None:
    """Check pending drafts and update edit info. Called by scheduler."""
    pending = get_pending_drafts_older_than(minutes=20)
    print(f"[edit_detection] Checking {len(pending)} pending drafts")

    for draft in pending:
        try:
            _check_draft(draft)
        except Exception:
            print(f"[edit_detection] Error on draft {draft['id']}:\n{traceback.format_exc()}")


def _check_draft(draft: dict) -> None:
    pm_id = draft["pm_id"]
    created_at = datetime.fromisoformat(draft["created_at"].replace("Z", "+00:00"))

    # Only check drafts within 48h; after that mark discarded
    if datetime.now(timezone.utc) - created_at > timedelta(hours=48):
        update_draft_status(draft["id"], "discarded")
        print(f"[edit_detection] Draft {draft['id']} expired — marking discarded")
        return

    # Look in SENT folder for messages in the 2 hours after draft creation
    since = created_at.strftime("%Y/%m/%d")
    sent_messages = get_sent_messages_since(pm_id, since)

    client_name = draft.get("client_name", "")
    subject_prefix = client_name  # drafts are titled "<Company> — Meeting Summary <date>"

    for msg in sent_messages:
        subject = _get_subject(msg)
        msg_date_ms = int(msg.get("internalDate", 0))
        msg_date = datetime.fromtimestamp(msg_date_ms / 1000, tz=timezone.utc)

        # Match: subject contains client name AND message sent within 2h of draft creation
        time_diff = msg_date - created_at
        if subject_prefix.lower() in subject.lower() and timedelta(0) <= time_diff <= timedelta(hours=2):
            sent_body = _extract_body_from_gmail_message(msg)
            agent_draft = draft.get("agent_draft", "")
            was_edited = sent_body.strip() != agent_draft.strip()
            diff = _compute_diff(agent_draft, sent_body) if was_edited else {"removed": [], "added": []}

            update_draft_edit_info(
                draft_id=draft["id"],
                was_edited=was_edited,
                edit_diff=diff,
                sent_draft=sent_body,
            )
            print(f"[edit_detection] Draft {draft['id']} — was_edited={was_edited}")

            # Autonomous learning: extract a lesson from significant edits
            if was_edited and (diff.get("removed") or diff.get("added")):
                try:
                    from agent.generator import extract_edit_lesson
                    lesson = extract_edit_lesson(
                        agent_draft=draft.get("agent_draft", ""),
                        sent_draft=sent_body,
                        edit_diff=diff,
                        transcript=draft.get("transcript", ""),
                        meeting_type=draft.get("meeting_type", "other"),
                    )
                    update_draft_edit_lesson(draft["id"], lesson)
                    print(f"[edit_detection] Lesson: [{lesson.get('issue_type')}] {lesson.get('description','')[:80]}")
                except Exception as e:
                    print(f"[edit_detection] Lesson extraction failed (non-fatal): {e}")

            return


def start_background_scheduler() -> None:
    """Start the edit detection loop in a daemon thread. Call once at app startup."""
    def _loop():
        while True:
            time.sleep(30 * 60)  # 30 minutes
            try:
                run_edit_detection_once()
            except Exception:
                print(f"[edit_detection] Scheduler error:\n{traceback.format_exc()}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("[edit_detection] Background scheduler started (30-min interval)")
