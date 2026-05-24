from __future__ import annotations

"""
Avoma API poller — replaces the inbound webhook approach.

Runs every 5 minutes. Queries the Avoma REST API for transcriptions
completed since the last poll, then feeds each new meeting through the
existing agent pipeline.

API reference: https://dev.avoma.com
Base URL: https://api.avoma.com/v1/
Auth: Authorization: Bearer {AVOMA_API_KEY}
Rate limit: 60 req/min
"""
import os
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from db.models import (
    get_pm_by_email, save_draft, update_draft_slack_notified, get_draft_by_avoma_id,
    get_recent_drafts_for_client, get_edit_lessons_for_pm, update_draft_escalation,
)
from agent.extractor import extract_context
from agent.analyzer import analyze_escalation
from agent.generator import generate_email, generate_internal_note
from integrations.gmail import create_gmail_draft
from integrations.slack import notify_pm, notify_eng_alert, post_internal_note

# ---------------------------------------------------------------------------
# Avoma API client
# ---------------------------------------------------------------------------

AVOMA_BASE = "https://api.avoma.com/v1"
POLL_INTERVAL_SECONDS = 5 * 60   # 5 minutes
# Avoma filters /transcriptions/ by meeting START TIME, not transcription-ready time.
# Transcription processing can take 30-60 min after meeting end.
# We always look back 4 hours so a meeting that started up to 4h ago is caught
# whenever its transcription finally becomes available.
# Deduplication via get_draft_by_avoma_id makes this safe — no double-drafts.
LOOKBACK_BUFFER_SECONDS = 4 * 60 * 60  # 4 hours

# File that stores the ISO timestamp of the last successful poll.
# Lives next to this file so it persists across restarts.
_LAST_POLL_FILE = Path(__file__).parent / ".avoma_last_poll"


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['AVOMA_API_KEY']}"}


def _get(path: str, params: dict | None = None) -> dict | list:
    url = f"{AVOMA_BASE}{path}"
    resp = requests.get(url, headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Transcript formatting
# ---------------------------------------------------------------------------

def _format_transcript(transcript_segments: list[dict], speakers: list[dict] | None = None) -> str:
    """
    Convert Avoma transcript array into readable plain text.

    Avoma v1 format: [{"speaker_id": 2, "transcript": "Hi...", "timestamps": [...], ...}, ...]
    speakers:        [{"id": 2, "name": "Gaurav", "email": "...", ...}, ...]
    """
    # Build speaker_id → name map from the speakers list
    id_to_name: dict[int, str] = {}
    if speakers:
        for s in speakers:
            sid = s.get("id")
            name = s.get("name", "")
            if sid is not None and name:
                id_to_name[sid] = name

    lines = []
    prev_speaker = None
    for seg in transcript_segments:
        # Support both Avoma v1 (speaker_id + transcript) and legacy (speaker + text)
        speaker_id = seg.get("speaker_id")
        if speaker_id is not None:
            speaker = id_to_name.get(speaker_id, f"Speaker {speaker_id}")
            text = seg.get("transcript", "").strip()
        else:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "").strip()

        if not text:
            continue
        if speaker != prev_speaker:
            lines.append(f"{speaker}: {text}")
            prev_speaker = speaker
        else:
            if lines:
                lines[-1] = lines[-1] + " " + text
            else:
                lines.append(f"{speaker}: {text}")
    return "\n\n".join(lines)


def _identify_fp_participants(speakers: list[dict], meeting: dict | None = None) -> list[str]:
    """
    Return emails of ALL @fleetpanda.com participants in the meeting.

    Checks TWO sources so we never miss a PM:
    1. Transcript speakers (audio-detected — can miss quiet/listening participants)
    2. Meeting attendees from the meeting object (roster-based — always complete)

    This handles the case where a PM organized or joined a meeting but wasn't
    detected as a distinct speaker by Avoma's audio processing.
    """
    emails: set[str] = set()

    # Source 1: transcript speakers
    for s in speakers:
        email = s.get("email", "")
        if "@fleetpanda.com" in email:
            emails.add(email.lower())

    # Source 2: meeting attendees list + organizer
    if meeting:
        # attendees array (includes everyone invited regardless of audio detection)
        for a in meeting.get("attendees") or []:
            email = a.get("email", "")
            if "@fleetpanda.com" in email:
                emails.add(email.lower())
        # organizer_email is a top-level string in Avoma's meeting object
        organizer_email = meeting.get("organizer_email", "")
        if "@fleetpanda.com" in organizer_email:
            emails.add(organizer_email.lower())

    return list(emails)


# ---------------------------------------------------------------------------
# Last-poll timestamp helpers
# ---------------------------------------------------------------------------

def _read_last_poll() -> datetime:
    """Return the timestamp of the last poll, or 10 minutes ago if no file."""
    if _LAST_POLL_FILE.exists():
        try:
            ts = _LAST_POLL_FILE.read_text().strip()
            return datetime.fromisoformat(ts)
        except Exception:
            pass
    return datetime.now(timezone.utc) - timedelta(hours=2)


def _write_last_poll(ts: datetime) -> None:
    _LAST_POLL_FILE.write_text(ts.isoformat())


# ---------------------------------------------------------------------------
# Core poll-and-process logic
# ---------------------------------------------------------------------------

def poll_once() -> None:
    """
    Fetch transcriptions completed since last poll and process each new one.
    Safe to call repeatedly — deduplicates against draft_history.
    """
    now = datetime.now(timezone.utc)
    last_poll = _read_last_poll()

    # Add a small lookback buffer so we don't miss anything near the boundary
    from_dt = last_poll - timedelta(seconds=LOOKBACK_BUFFER_SECONDS)

    print(f"[avoma_poller] Checking for transcriptions from {from_dt.isoformat()} to {now.isoformat()}")

    try:
        data = _get("/transcriptions/", params={
            "from_date": from_dt.isoformat(),
            "to_date": now.isoformat(),
            "page_size": 50,
        })
    except requests.HTTPError as e:
        print(f"[avoma_poller] API error fetching transcriptions: {e}")
        return

    transcriptions = data.get("results", data) if isinstance(data, dict) else data
    print(f"[avoma_poller] Found {len(transcriptions)} transcription(s)")

    for txn in transcriptions:
        meeting_uuid = txn.get("meeting_uuid") or txn.get("uuid")
        if not meeting_uuid:
            continue
        try:
            _process_transcription(txn, meeting_uuid)
        except Exception:
            print(f"[avoma_poller] Failed on meeting {meeting_uuid}:\n{traceback.format_exc()}")
            _alert_eng(f"Avoma poller failed on meeting {meeting_uuid}:\n```{traceback.format_exc()[-800:]}```")

    _write_last_poll(now)


def _process_transcription(txn: dict, meeting_uuid: str) -> None:
    # --- Fetch meeting details for subject / start_time ---
    try:
        meeting = _get(f"/meetings/{meeting_uuid}/")
    except requests.HTTPError as e:
        print(f"[avoma_poller] Could not fetch meeting {meeting_uuid}: {e}")
        return

    # --- Find ALL FleetPanda participants (speakers + attendees) ---
    speakers = txn.get("speakers", [])
    fp_emails = _identify_fp_participants(speakers, meeting=meeting)
    if not fp_emails:
        print(f"[avoma_poller] No FleetPanda participants for meeting {meeting_uuid} — skipping")
        return
    print(f"[avoma_poller] FP participants for {meeting_uuid}: {fp_emails}")

    # --- Build common transcript + metadata (done once, shared across all PMs) ---
    transcript_segments = txn.get("transcript", [])
    transcript_text = _format_transcript(transcript_segments, speakers=speakers)

    attendees = [
        {"name": s.get("name", ""), "email": s.get("email", "")}
        for s in speakers
        if s.get("email")
    ]
    metadata = {
        "id": meeting_uuid,
        "title": meeting.get("subject") or meeting.get("title") or "",
        "start_time": meeting.get("start_at") or meeting.get("start_time") or meeting.get("startTime") or "",
        "attendees": attendees,
    }

    # Extract context once — same for all PMs
    context = extract_context(transcript_text, metadata)

    # Analyze escalation risk once — shared across all PMs for this meeting
    escalation_result = {"risk_level": "unknown", "signals": [], "sentiment_summary": ""}
    try:
        escalation_result = analyze_escalation(
            transcript=transcript_text,
            context=context,
            meeting_type=context.get("meeting_type", "other"),
        )
        print(f"[avoma_poller] Escalation risk: {escalation_result.get('risk_level')} — {escalation_result.get('sentiment_summary', '')[:60]}")
    except Exception as e:
        print(f"[avoma_poller] Escalation analysis failed (non-fatal): {e}")

    # --- Generate a draft for each registered, onboarded FleetPanda participant ---
    processed = 0
    for fp_email in fp_emails:
        pm = get_pm_by_email(fp_email)
        if not pm:
            print(f"[avoma_poller] PM not found for {fp_email} — skipping")
            continue
        if not pm.get("onboarding_complete"):
            print(f"[avoma_poller] PM {fp_email} has not completed onboarding — skipping")
            continue

        pm_id = pm["id"]

        # Dedup per (avoma_id, pm_id) so multiple PMs can each get their own draft
        if get_draft_by_avoma_id(meeting_uuid, pm_id=pm_id):
            print(f"[avoma_poller] Already processed meeting {meeting_uuid} for {fp_email} — skipping")
            continue

        print(f"[avoma_poller] Processing meeting {meeting_uuid} for PM {fp_email}")
        try:
            draft = _generate_draft_for_pm(pm, pm_id, context, transcript_text, metadata, meeting_uuid)
            if draft is None:
                # save_draft hit a unique constraint violation — another process already inserted
                print(f"[avoma_poller] Duplicate insert blocked for {meeting_uuid} / {fp_email} — skipping")
                continue
            # Store escalation result on the saved draft
            if draft and escalation_result.get("risk_level") != "unknown":
                try:
                    update_draft_escalation(
                        draft_id=draft["id"],
                        risk_level=escalation_result["risk_level"],
                        risk_signals=escalation_result.get("signals", []),
                        sentiment_summary=escalation_result.get("sentiment_summary", ""),
                    )
                except Exception as e:
                    print(f"[avoma_poller] Escalation store failed (non-fatal): {e}")
            processed += 1
        except Exception:
            print(f"[avoma_poller] Failed draft for {fp_email} on {meeting_uuid}:\n{traceback.format_exc()}")
            _alert_eng(f"Draft failed for {fp_email} on meeting {meeting_uuid}:\n```{traceback.format_exc()[-800:]}```")

    if processed == 0 and fp_emails:
        print(f"[avoma_poller] Meeting {meeting_uuid} — all FP participants already processed or not onboarded")


def _generate_draft_for_pm(
    pm: dict, pm_id: str, context: dict, transcript_text: str, metadata: dict, meeting_uuid: str
) -> None:
    """Generate and save a Gmail draft for a single PM for a given meeting."""
    client_name = context.get("client_name", "")

    # Pull prior meetings with same client for continuity context
    prior_meetings = get_recent_drafts_for_client(
        pm_id=pm_id,
        client_name=client_name,
        limit=3,
        exclude_avoma_id=meeting_uuid,
    )
    if prior_meetings:
        print(f"[avoma_poller] Found {len(prior_meetings)} prior meeting(s) with {client_name} for {pm.get('email')}")

    # Pull email thread with client since the last meeting.
    # Requires gmail.readonly scope — fails silently if PM hasn't re-authorized yet.
    client_email_thread = []
    client_email = context.get("client_email", "")
    if prior_meetings and client_email:
        last_meeting_date = (prior_meetings[0].get("meeting_date") or "")[:10]
        current_meeting_date = (metadata["start_time"] or "")[:10]
        if last_meeting_date and current_meeting_date:
            try:
                from integrations.gmail import get_emails_with_client
                client_email_thread = get_emails_with_client(
                    pm_id=pm_id,
                    client_email=client_email,
                    after_date=last_meeting_date,
                    before_date=current_meeting_date,
                )
                if client_email_thread:
                    print(f"[avoma_poller] Found {len(client_email_thread)} emails with client since last meeting")
            except Exception:
                pass  # Scope not yet granted — silently skip

    # Pull autonomous edit lessons for this PM
    edit_lessons = get_edit_lessons_for_pm(pm_id, limit=5)
    if edit_lessons:
        print(f"[avoma_poller] Injecting {len(edit_lessons)} edit lesson(s) into prompt")

    email_body = generate_email(
        pm_id=pm_id,
        transcript=transcript_text,
        context=context,
        prior_meetings=prior_meetings,
        client_email_thread=client_email_thread or None,
        edit_lessons=edit_lessons or None,
    )

    client_company = context.get("client_company", "")
    meeting_date = (metadata["start_time"] or "")[:10]
    subject = f"{client_company or client_name} — Meeting Summary {meeting_date}".strip(" —")

    gmail_draft_id = create_gmail_draft(
        pm_id=pm_id,
        to_email=client_email,
        to_name=client_name,
        subject=subject,
        body=email_body,
    )

    # Generate internal team note (only once — posted by the first PM processed)
    internal_note = ""
    try:
        internal_note = generate_internal_note(
            pm_name=pm.get("name", "PM"),
            context=context,
            transcript=transcript_text,
        )
    except Exception:
        print(f"[avoma_poller] Internal note generation failed (non-fatal)")

    draft = save_draft(
        pm_id=pm_id,
        avoma_meeting_id=meeting_uuid,
        client_name=client_name,
        meeting_type=context.get("meeting_type", "other"),
        meeting_date=metadata["start_time"] or "",
        transcript=transcript_text,
        agent_draft=email_body,
        gmail_draft_id=gmail_draft_id,
        meeting_summary=context.get("meeting_summary", ""),
        client_action_items=context.get("client_action_items", []),
        fleetpanda_action_items=context.get("fleetpanda_action_items", []),
        client_company=client_company,
        client_email=client_email,
        next_steps=context.get("next_steps", ""),
        gmail_subject=subject,
        gmail_to_email=client_email,
        gmail_to_name=client_name,
        internal_note=internal_note,
        client_email_thread="\n\n---\n\n".join(
            f"{e['date_str']} | {e['from_header']}\nSubject: {e['subject']}\n{e['body_text']}"
            for e in client_email_thread
        ) if client_email_thread else "",
        meeting_title=metadata.get("title", ""),
    )

    slack_user_id = pm.get("slack_user_id")
    if slack_user_id:
        notify_pm(
            slack_user_id=slack_user_id,
            client_name=client_name,
            meeting_type=context.get("meeting_type", "other"),
        )
        update_draft_slack_notified(draft["id"])

    if internal_note:
        try:
            post_internal_note(
                pm_name=pm.get("name", "PM"),
                client_name=client_name,
                meeting_type=context.get("meeting_type", "other"),
                internal_note=internal_note,
            )
        except Exception as e:
            print(f"[avoma_poller] Internal note Slack post failed (non-fatal): {e}")

    print(f"[avoma_poller] Done — pm={pm.get('email')} draft_id={draft['id']} gmail_draft_id={gmail_draft_id}")
    return draft


# ---------------------------------------------------------------------------
# Eng alerts
# ---------------------------------------------------------------------------

def _alert_eng(message: str) -> None:
    notify_eng_alert(message)


# ---------------------------------------------------------------------------
# Background scheduler
# ---------------------------------------------------------------------------

def start_avoma_poller() -> None:
    """
    Start the Avoma polling loop in a daemon thread.
    Polls every 5 minutes. Call once at app startup.
    """
    def _loop():
        # Stagger initial poll by 10 seconds to let app finish starting up
        time.sleep(10)
        while True:
            try:
                poll_once()
            except Exception:
                print(f"[avoma_poller] Unexpected error:\n{traceback.format_exc()}")
            time.sleep(POLL_INTERVAL_SECONDS)

    t = threading.Thread(target=_loop, daemon=True, name="avoma-poller")
    t.start()
    print("[avoma_poller] Started — polling every 5 minutes")
