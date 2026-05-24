import os
from datetime import timedelta
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env from the project root (one level up from backend/).
# override=True ensures .env values win over any stale shell exports.
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path, override=True)

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# Allow the Next.js frontend to call Flask directly from the browser.
# credentials=True requires a specific origin (not wildcard).
CORS(
    app,
    origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    supports_credentials=True,
)

# Auth blueprint (Google OAuth exchange endpoint)
from auth.google_oauth import auth_bp
app.register_blueprint(auth_bp)

# DB queries
from db.models import (
    get_style_samples,
    add_style_sample,
    delete_style_sample,
    get_pm_by_id,
    update_pm_slack_id,
    get_draft_history,
    get_draft_by_id,
    set_onboarding_complete,
    update_draft_agent_content,
    mark_draft_used,
    pm_needs_reauth,
    add_task,
    get_tasks,
    update_task_status,
    get_escalation_summary,
    get_recent_meetings_for_report,
)
from agent.generator import generate_email


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# PM profile
# ---------------------------------------------------------------------------

@app.route("/api/pm/<pm_id>", methods=["GET"])
def get_pm(pm_id):
    pm = get_pm_by_id(pm_id)
    if not pm:
        return jsonify({"error": "not found"}), 404
    return jsonify(pm)


@app.route("/api/pm/<pm_id>/needs-reauth", methods=["GET"])
def needs_reauth(pm_id):
    return jsonify({"needs_reauth": pm_needs_reauth(pm_id)})


# ---------------------------------------------------------------------------
# Style samples
# ---------------------------------------------------------------------------

@app.route("/api/samples", methods=["GET"])
def list_samples():
    pm_id = request.args.get("pm_id")
    samples = get_style_samples(pm_id, meeting_type=None, limit=50)
    return jsonify(samples)


@app.route("/api/samples", methods=["POST"])
def create_sample():
    data = request.get_json()
    sample = add_style_sample(
        pm_id=data["pm_id"],
        meeting_type=data["meeting_type"],
        email_body=data["email_body"],
        client_name=data.get("client_name", ""),
    )
    # Mark onboarding complete once PM has ≥3 style samples (Slack is optional)
    samples = get_style_samples(data["pm_id"], meeting_type=None, limit=50)
    if len(samples) >= 3:
        set_onboarding_complete(data["pm_id"])
    return jsonify(sample), 201


@app.route("/api/samples/<sample_id>", methods=["DELETE"])
def remove_sample(sample_id):
    delete_style_sample(sample_id)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Style preview
# ---------------------------------------------------------------------------

@app.route("/api/style-preview", methods=["POST"])
def style_preview():
    data = request.get_json()
    pm_id = data["pm_id"]
    draft = generate_email(pm_id=pm_id, transcript=None, context=None, preview_mode=True)
    return jsonify({"draft": draft})


@app.route("/api/test-gmail-draft", methods=["POST"])
def test_gmail_draft():
    """
    Dev-only: generates a draft using sample data and creates it in Gmail.
    POST body: { "pm_id": "..." }
    Returns the gmail_draft_id so you can verify it appeared in Gmail Drafts.
    """
    from integrations.gmail import create_gmail_draft
    data = request.get_json()
    pm_id = data["pm_id"]
    draft_body = generate_email(pm_id=pm_id, transcript=None, context=None, preview_mode=True)
    gmail_draft_id = create_gmail_draft(
        pm_id=pm_id,
        to_email="raj@acmecorp.com",
        to_name="Raj",
        subject="Follow-up: FleetPanda onboarding — Acme Corp",
        body=draft_body,
    )
    return jsonify({"ok": True, "gmail_draft_id": gmail_draft_id})


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

@app.route("/api/onboarding/slack", methods=["POST"])
def onboarding_slack():
    data = request.get_json()
    update_pm_slack_id(data["pm_id"], data["slack_user_id"])

    # Set onboarding complete once PM has ≥3 style samples
    samples = get_style_samples(data["pm_id"], meeting_type=None, limit=50)
    if len(samples) >= 3:
        set_onboarding_complete(data["pm_id"])

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Draft history
# ---------------------------------------------------------------------------

@app.route("/api/history", methods=["GET"])
def history():
    pm_id = request.args.get("pm_id")
    drafts = get_draft_history(pm_id, limit=50)
    return jsonify(drafts)


@app.route("/api/history/<draft_id>/transcript", methods=["GET"])
def transcript(draft_id):
    draft = get_draft_by_id(draft_id)
    if not draft:
        return jsonify({"error": "not found"}), 404
    return jsonify({"transcript": draft["transcript"]})


# ---------------------------------------------------------------------------
# Enhancement 3: in-dashboard draft regeneration
# ---------------------------------------------------------------------------

@app.route("/api/drafts/<draft_id>/regenerate", methods=["POST"])
def regenerate_draft(draft_id):
    """
    PM provides feedback on the current draft and gets a revised version.
    Reconstructs context from stored DB fields — no need to re-run the extractor.
    """
    data = request.get_json()
    feedback = data.get("feedback", "").strip()
    draft = get_draft_by_id(draft_id)
    if not draft:
        return jsonify({"error": "not found"}), 404

    context = {
        "client_name": draft.get("client_name", ""),
        "client_company": draft.get("client_company", ""),
        "client_email": draft.get("client_email", ""),
        "meeting_type": draft.get("meeting_type", "other"),
        "meeting_date": draft.get("meeting_date", ""),
        "meeting_summary": draft.get("meeting_summary", ""),
        "client_action_items": draft.get("client_action_items") or [],
        "fleetpanda_action_items": draft.get("fleetpanda_action_items") or [],
        "next_steps": draft.get("next_steps", ""),
    }

    new_email = generate_email(
        pm_id=draft["pm_id"],
        transcript=draft.get("transcript", ""),
        context=context,
        pm_feedback=feedback or None,
        previous_draft=draft.get("agent_draft", ""),
    )

    update_draft_agent_content(draft_id, new_email, pm_feedback=feedback or None)
    return jsonify({"new_draft": new_email})


@app.route("/api/drafts/<draft_id>/mark-used", methods=["POST"])
def mark_used(draft_id):
    """
    PM copied this draft and used it in a reply thread.
    Body: { "was_edited": bool }  — false = used verbatim, true = made changes first
    """
    data = request.get_json()
    was_edited = bool(data.get("was_edited", False))
    mark_draft_used(draft_id, was_edited)
    return jsonify({"ok": True})


@app.route("/api/drafts/<draft_id>/push-to-gmail", methods=["POST"])
def push_to_gmail(draft_id):
    """
    Replace the Gmail draft with the given body (after PM confirms the regenerated version).
    """
    from integrations.gmail import update_gmail_draft
    data = request.get_json()
    new_body = data.get("body", "")
    draft = get_draft_by_id(draft_id)
    if not draft:
        return jsonify({"error": "not found"}), 404

    update_gmail_draft(
        pm_id=draft["pm_id"],
        gmail_draft_id=draft["gmail_draft_id"],
        to_email=draft.get("gmail_to_email", ""),
        to_name=draft.get("gmail_to_name", ""),
        subject=draft.get("gmail_subject", ""),
        body=new_body,
    )
    update_draft_agent_content(draft_id, new_body)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Tasks board
# ---------------------------------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    pm_id = request.args.get("pm_id")
    return jsonify(get_tasks(pm_id))


@app.route("/api/tasks", methods=["POST"])
def create_tasks():
    """Create one or more tasks at once. Body: { pm_id, draft_id, client_name, descriptions: [str] }"""
    data = request.get_json()
    pm_id = data["pm_id"]
    draft_id = data["draft_id"]
    client_name = data.get("client_name", "")
    descriptions = data.get("descriptions", [])
    created = [
        add_task(pm_id=pm_id, draft_id=draft_id, client_name=client_name, description=desc)
        for desc in descriptions
        if desc.strip()
    ]
    return jsonify(created), 201


@app.route("/api/tasks/<task_id>", methods=["PATCH"])
def patch_task(task_id):
    data = request.get_json()
    update_task_status(task_id, data["status"])
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Escalation Radar
# ---------------------------------------------------------------------------

@app.route("/api/escalation", methods=["GET"])
def escalation():
    pm_id = request.args.get("pm_id")
    return jsonify(get_escalation_summary(pm_id))


# ---------------------------------------------------------------------------
# Debug / dev tools
# ---------------------------------------------------------------------------

@app.route("/api/debug/gmail-scope", methods=["GET"])
def debug_gmail_scope():
    """Check what Gmail scopes the stored token actually has, and test a read call."""
    pm_id = request.args.get("pm_id")
    if not pm_id:
        return jsonify({"error": "pm_id required"}), 400
    try:
        from auth.google_oauth import get_credentials_for_pm
        from googleapiclient.discovery import build
        creds = get_credentials_for_pm(pm_id)
        service = build("gmail", "v1", credentials=creds)
        # Try getProfile (works with gmail.compose)
        profile = service.users().getProfile(userId="me").execute()
        # Try messages.list — this requires gmail.readonly specifically
        service.users().messages().list(userId="me", maxResults=1).execute()
        return jsonify({
            "ok": True,
            "gmail_read": True,
            "email": profile.get("emailAddress"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "scopes": sorted(creds.scopes or []) if 'creds' in dir() else []})

@app.route("/api/debug/poll-now", methods=["POST"])
def debug_poll_now():
    """
    Manually trigger one Avoma poll cycle. Returns a summary of what was found/processed.
    POST body (optional): { "hours_back": 6 }  — override lookback window
    """
    import io, contextlib
    from jobs.avoma_poller import poll_once, _read_last_poll, _write_last_poll, LOOKBACK_BUFFER_SECONDS
    from datetime import datetime, timezone, timedelta

    data = request.get_json(silent=True) or {}
    hours_back = int(data.get("hours_back", 0))

    if hours_back:
        # Temporarily push last_poll back so we look further
        fake_last = datetime.now(timezone.utc) - timedelta(hours=hours_back) + timedelta(seconds=LOOKBACK_BUFFER_SECONDS)
        _write_last_poll(fake_last)

    # Capture stdout from poll_once
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            poll_once()
        except Exception as e:
            return jsonify({"error": str(e), "log": buf.getvalue()}), 500

    return jsonify({"ok": True, "log": buf.getvalue()})


@app.route("/api/debug/avoma-transcriptions", methods=["GET"])
def debug_avoma_transcriptions():
    """
    Show raw Avoma /transcriptions/ results for the last N hours (default 6).
    GET ?hours=6
    """
    from jobs.avoma_poller import _get, LOOKBACK_BUFFER_SECONDS
    from datetime import datetime, timezone, timedelta

    hours = int(request.args.get("hours", 6))
    now = datetime.now(timezone.utc)
    from_dt = now - timedelta(hours=hours)

    try:
        data = _get("/transcriptions/", params={
            "from_date": from_dt.isoformat(),
            "to_date": now.isoformat(),
            "page_size": 50,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    transcriptions = data.get("results", data) if isinstance(data, dict) else data
    summary = []
    for t in transcriptions:
        from jobs.avoma_poller import _get as avoma_get
        uuid = t.get("meeting_uuid") or t.get("uuid", "")
        speakers = [s.get("email", "") for s in t.get("speakers", []) if s.get("email")]
        summary.append({
            "uuid": uuid,
            "speakers": speakers,
            "has_transcript": bool(t.get("transcript")),
            "segment_count": len(t.get("transcript", [])),
        })

    return jsonify({"count": len(summary), "from": from_dt.isoformat(), "meetings": summary})


# ---------------------------------------------------------------------------
# Weekly status report
# ---------------------------------------------------------------------------

@app.route("/api/reports/weekly", methods=["POST"])
def weekly_report():
    from agent.report_generator import generate_weekly_report
    data = request.get_json()
    pm_id = data["pm_id"]
    client_name = data["client_name"]
    week_ending = data.get("week_ending", "")

    pm = get_pm_by_id(pm_id)
    if not pm:
        return jsonify({"error": "PM not found"}), 404

    # Pull meetings from the past 14 days (this week + last week)
    recent_meetings = get_recent_meetings_for_report(pm_id, client_name, days=14)
    manual_email_thread = data.get("email_thread", "")

    # Use client_company / contact info from most recent meeting if available
    client_company = ""
    contact_name = client_name
    client_email = ""
    if recent_meetings:
        client_company = recent_meetings[0].get("client_company") or ""
        contact_name = recent_meetings[0].get("client_name") or client_name
        client_email = recent_meetings[0].get("client_email") or ""

    # Auto-pull current week's emails with this client (Mon → today)
    # Requires gmail.readonly scope — fails silently if not yet re-authorized
    from datetime import date
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()  # Monday
    week_end = today.isoformat()

    auto_gmail_thread = ""
    if client_email:
        try:
            from integrations.gmail import get_emails_with_client
            emails = get_emails_with_client(
                pm_id=pm_id,
                client_email=client_email,
                after_date=week_start,
                before_date=week_end,
            )
            if emails:
                auto_gmail_thread = "\n\n---\n\n".join(
                    f"{e['date_str']} | {e['from_header']}\nSubject: {e['subject']}\n{e['body_text']}"
                    for e in emails
                )
                print(f"[weekly_report] Pulled {len(emails)} emails with {client_email} for report")
        except Exception as e:
            print(f"[weekly_report] Gmail email fetch failed (non-fatal): {e}")

    # Combine: auto-pulled Gmail + manually pasted (manual takes priority at the end)
    combined_email_thread = "\n\n---\n\n".join(filter(None, [auto_gmail_thread, manual_email_thread]))

    report_text = generate_weekly_report(
        pm_name=pm.get("name", ""),
        pm_email=pm.get("email", ""),
        client_name=contact_name,
        client_company=client_company or client_name,
        contact_name=contact_name,
        week_ending=week_ending,
        recent_meetings=recent_meetings,
        email_thread=combined_email_thread,
    )
    return jsonify({"report_text": report_text})


# ---------------------------------------------------------------------------
# Background jobs (start once at app boot)
# ---------------------------------------------------------------------------

from jobs.avoma_poller import start_avoma_poller
from jobs.edit_detection import start_background_scheduler
from jobs.retention import start_retention_scheduler

start_avoma_poller()
start_background_scheduler()
start_retention_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="127.0.0.1", port=port)
