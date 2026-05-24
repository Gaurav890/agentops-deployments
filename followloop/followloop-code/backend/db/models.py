"""
All Supabase queries for the FleetPanda Meeting Summary Agent.
No raw SQL anywhere outside this file.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from db import get_db


# ---------------------------------------------------------------------------
# PMs
# ---------------------------------------------------------------------------

def get_pm_by_email(email: str) -> dict | None:
    res = get_db().table("pms").select("*").eq("email", email).limit(1).execute()
    return res.data[0] if res.data else None


def get_pm_by_id(pm_id: str) -> dict | None:
    res = get_db().table("pms").select("*").eq("id", pm_id).limit(1).execute()
    return res.data[0] if res.data else None


def upsert_pm(email: str, name: str, google_sub: str) -> dict:
    """Create PM if not exists; update name/google_sub if they sign in again."""
    res = (
        get_db()
        .table("pms")
        .upsert(
            {"email": email, "name": name, "google_sub": google_sub},
            on_conflict="email",
        )
        .execute()
    )
    return res.data[0]


def update_pm_slack_id(pm_id: str, slack_user_id: str) -> None:
    get_db().table("pms").update({"slack_user_id": slack_user_id}).eq("id", pm_id).execute()


def set_onboarding_complete(pm_id: str) -> None:
    get_db().table("pms").update({"onboarding_complete": True}).eq("id", pm_id).execute()


# ---------------------------------------------------------------------------
# OAuth tokens
# ---------------------------------------------------------------------------

def get_oauth_token(pm_id: str) -> dict | None:
    res = (
        get_db()
        .table("oauth_tokens")
        .select("*")
        .eq("pm_id", pm_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def upsert_oauth_token(
    pm_id: str,
    access_token: str,
    refresh_token_encrypted: str,
    token_expiry: str,
    scopes: list[str],
) -> None:
    get_db().table("oauth_tokens").upsert(
        {
            "pm_id": pm_id,
            "access_token": access_token,
            "refresh_token": refresh_token_encrypted,
            "token_expiry": token_expiry,
            "scopes": scopes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="pm_id",
    ).execute()


def update_oauth_token(pm_id: str, access_token: str, token_expiry: str) -> None:
    get_db().table("oauth_tokens").update(
        {
            "access_token": access_token,
            "token_expiry": token_expiry,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("pm_id", pm_id).execute()


# ---------------------------------------------------------------------------
# Style samples
# ---------------------------------------------------------------------------

def get_style_samples(pm_id: str, meeting_type: str | None, limit: int = 3) -> list[dict]:
    """
    Return up to `limit` samples for pm_id.
    If meeting_type given: prefer that type first, backfill with others to reach limit.
    """
    db = get_db()

    if meeting_type:
        typed = (
            db.table("style_samples")
            .select("*")
            .eq("pm_id", pm_id)
            .eq("meeting_type", meeting_type)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        if len(typed) < limit:
            already_ids = [s["id"] for s in typed]
            q = (
                db.table("style_samples")
                .select("*")
                .eq("pm_id", pm_id)
                .order("created_at", desc=True)
                .limit(limit - len(typed))
            )
            # Only exclude already-fetched IDs when there are some
            if already_ids:
                q = q.not_.in_("id", already_ids)
            backfill = q.execute().data
            return typed + backfill
        return typed[:limit]

    return (
        db.table("style_samples")
        .select("*")
        .eq("pm_id", pm_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def add_style_sample(
    pm_id: str, meeting_type: str, email_body: str, client_name: str = ""
) -> dict:
    res = (
        get_db()
        .table("style_samples")
        .insert(
            {
                "pm_id": pm_id,
                "meeting_type": meeting_type,
                "email_body": email_body,
                "client_name": client_name,
            }
        )
        .execute()
    )
    return res.data[0]


def delete_style_sample(sample_id: str) -> None:
    get_db().table("style_samples").delete().eq("id", sample_id).execute()


# ---------------------------------------------------------------------------
# Draft history
# ---------------------------------------------------------------------------

def save_draft(
    pm_id: str,
    avoma_meeting_id: str,
    client_name: str,
    meeting_type: str,
    meeting_date: str,
    transcript: str,
    agent_draft: str,
    gmail_draft_id: str,
    # Enhancement 1 — persisted context for client memory
    meeting_summary: str = "",
    client_action_items: list | None = None,
    fleetpanda_action_items: list | None = None,
    client_company: str = "",
    client_email: str = "",
    next_steps: str = "",
    # Enhancement 3 — needed by regenerate endpoint
    gmail_subject: str = "",
    gmail_to_email: str = "",
    gmail_to_name: str = "",
    # Enhancement 2 — internal team note
    internal_note: str = "",
    # Gmail thread context
    client_email_thread: str = "",
    # Avoma meeting title
    meeting_title: str = "",
) -> dict:
    res = (
        get_db()
        .table("draft_history")
        .insert(
            {
                "pm_id": pm_id,
                "avoma_meeting_id": avoma_meeting_id,
                "client_name": client_name,
                "meeting_type": meeting_type,
                "meeting_date": meeting_date,
                "transcript": transcript,
                "agent_draft": agent_draft,
                "gmail_draft_id": gmail_draft_id,
                "status": "pending",
                "meeting_summary": meeting_summary,
                "client_action_items": client_action_items or [],
                "fleetpanda_action_items": fleetpanda_action_items or [],
                "client_company": client_company,
                "client_email": client_email,
                "next_steps": next_steps,
                "gmail_subject": gmail_subject,
                "gmail_to_email": gmail_to_email,
                "gmail_to_name": gmail_to_name,
                "internal_note": internal_note,
                "client_email_thread": client_email_thread,
                "meeting_title": meeting_title,
            }
        )
        .execute()
    )
    # If a unique constraint on (avoma_meeting_id, pm_id) blocks the insert
    # (race condition between concurrent pollers), data will be empty.
    return res.data[0] if res.data else None


def update_draft_status(
    draft_id: str, status: str, sent_draft: str | None = None
) -> None:
    update: dict[str, Any] = {"status": status}
    if sent_draft is not None:
        update["sent_draft"] = sent_draft
    get_db().table("draft_history").update(update).eq("id", draft_id).execute()


def update_draft_edit_info(
    draft_id: str, was_edited: bool, edit_diff: dict, sent_draft: str
) -> None:
    get_db().table("draft_history").update(
        {
            "was_edited": was_edited,
            "edit_diff": edit_diff,
            "sent_draft": sent_draft,
            "status": "sent",
        }
    ).eq("id", draft_id).execute()


def update_draft_slack_notified(draft_id: str) -> None:
    get_db().table("draft_history").update(
        {"slack_notified_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", draft_id).execute()


def get_draft_history(pm_id: str, limit: int = 50) -> list[dict]:
    return (
        get_db()
        .table("draft_history")
        .select("*")
        .eq("pm_id", pm_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def get_draft_by_id(draft_id: str) -> dict | None:
    res = (
        get_db()
        .table("draft_history")
        .select("*")
        .eq("id", draft_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_draft_by_avoma_id(avoma_meeting_id: str, pm_id: str | None = None) -> dict | None:
    """Used by the poller to deduplicate — returns existing draft if this meeting was already processed.
    If pm_id is provided, scopes the check to that specific PM (allows multiple PMs per meeting)."""
    q = (
        get_db()
        .table("draft_history")
        .select("id")
        .eq("avoma_meeting_id", avoma_meeting_id)
    )
    if pm_id:
        q = q.eq("pm_id", pm_id)
    res = q.limit(1).execute()
    return res.data[0] if res.data else None


def get_pending_drafts_older_than(minutes: int) -> list[dict]:
    """Used by edit detection job."""
    res = (
        get_db()
        .table("draft_history")
        .select("*")
        .eq("status", "pending")
        .lt("created_at", (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat())
        .execute()
    )
    return res.data


# ---------------------------------------------------------------------------
# OAuth scope check
# ---------------------------------------------------------------------------

def pm_needs_reauth(pm_id: str) -> bool:
    """True if the PM's stored scopes are missing gmail.readonly."""
    token = get_oauth_token(pm_id)
    if not token:
        return True
    scopes = token.get("scopes") or []
    return not any("gmail.readonly" in s for s in scopes)


# ---------------------------------------------------------------------------
# Enhancement 1: client history lookup
# ---------------------------------------------------------------------------

def get_recent_drafts_for_client(
    pm_id: str, client_name: str, limit: int = 3, exclude_avoma_id: str | None = None
) -> list[dict]:
    """
    Return last `limit` meetings with this client (matched by name, case-insensitive).
    Used to inject prior meeting context + sent emails into the generator prompt.
    Falls back to agent_draft when sent_draft is not yet populated.
    """
    if not client_name:
        return []
    q = (
        get_db()
        .table("draft_history")
        .select(
            "id, meeting_type, meeting_date, meeting_summary, "
            "client_action_items, fleetpanda_action_items, "
            "sent_draft, agent_draft, status"
        )
        .eq("pm_id", pm_id)
        .ilike("client_name", f"%{client_name}%")
        .order("meeting_date", desc=True)
        .limit(limit)
    )
    if exclude_avoma_id:
        q = q.neq("avoma_meeting_id", exclude_avoma_id)
    return q.execute().data


# ---------------------------------------------------------------------------
# Autonomous edit learning
# ---------------------------------------------------------------------------

def update_draft_edit_lesson(draft_id: str, lesson: dict) -> None:
    """Store the Claude-extracted lesson from a PM's edit."""
    get_db().table("draft_history").update(
        {"edit_lesson": lesson}
    ).eq("id", draft_id).execute()


def get_edit_lessons_for_pm(pm_id: str, limit: int = 5) -> list[dict]:
    """
    Return the most recent edit lessons for this PM.
    Injected into future prompts so the agent improves automatically.
    """
    res = (
        get_db()
        .table("draft_history")
        .select("edit_lesson, meeting_type, created_at")
        .eq("pm_id", pm_id)
        .eq("was_edited", True)
        .not_.is_("edit_lesson", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [row["edit_lesson"] for row in res.data if row.get("edit_lesson")]


# ---------------------------------------------------------------------------
# Enhancement 3: in-dashboard regenerate
# ---------------------------------------------------------------------------

def update_draft_agent_content(
    draft_id: str, new_draft: str, pm_feedback: str | None = None
) -> None:
    """
    Overwrite agent_draft with regenerated content and store the PM's feedback.
    Increments regeneration_count so we can track how often drafts need fixing.
    """
    update: dict[str, Any] = {"agent_draft": new_draft}
    if pm_feedback is not None:
        update["pm_feedback"] = pm_feedback
    # Increment regeneration_count via a read-then-write (Supabase has no SQL increment via REST)
    res = (
        get_db()
        .table("draft_history")
        .select("regeneration_count")
        .eq("id", draft_id)
        .limit(1)
        .execute()
    )
    current = (res.data[0].get("regeneration_count") or 0) if res.data else 0
    update["regeneration_count"] = current + 1
    get_db().table("draft_history").update(update).eq("id", draft_id).execute()


# ---------------------------------------------------------------------------
# Draft usage tracking (copy-paste workflow)
# ---------------------------------------------------------------------------

def mark_draft_used(draft_id: str, was_edited: bool) -> None:
    """
    Record that the PM copied and used this draft.
    was_edited=False → used verbatim (~20 min saved)
    was_edited=True  → edited before sending (~10 min saved)
    """
    get_db().table("draft_history").update({
        "status": "sent",
        "was_edited": was_edited,
    }).eq("id", draft_id).execute()


# ---------------------------------------------------------------------------
# Tasks board
# ---------------------------------------------------------------------------

def add_task(pm_id: str, draft_id: str, client_name: str, description: str) -> dict:
    res = (
        get_db()
        .table("tasks")
        .insert({
            "pm_id": pm_id,
            "draft_id": draft_id,
            "client_name": client_name,
            "description": description,
            "status": "pending",
        })
        .execute()
    )
    return res.data[0]


def get_tasks(pm_id: str) -> list[dict]:
    res = (
        get_db()
        .table("tasks")
        .select("*")
        .eq("pm_id", pm_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def update_task_status(task_id: str, status: str) -> None:
    update: dict[str, Any] = {"status": status}
    if status == "done":
        update["completed_at"] = datetime.now(timezone.utc).isoformat()
    else:
        update["completed_at"] = None
    get_db().table("tasks").update(update).eq("id", task_id).execute()


# ---------------------------------------------------------------------------
# Escalation detection
# ---------------------------------------------------------------------------

def update_draft_escalation(
    draft_id: str, risk_level: str, risk_signals: list, sentiment_summary: str
) -> None:
    get_db().table("draft_history").update({
        "escalation_risk": risk_level,
        "risk_signals": risk_signals,
        "sentiment_summary": sentiment_summary,
    }).eq("id", draft_id).execute()


def get_escalation_summary(pm_id: str) -> list[dict]:
    """
    Return the latest meeting per client with escalation fields.
    Used by the Escalation Radar page.
    """
    res = (
        get_db()
        .table("draft_history")
        .select(
            "id, client_name, client_company, meeting_type, meeting_date, "
            "escalation_risk, risk_signals, sentiment_summary, created_at"
        )
        .eq("pm_id", pm_id)
        .not_.in_("escalation_risk", ["unknown", ""])
        .order("meeting_date", desc=True)
        .execute()
    )

    # Keep only the latest meeting per client
    seen: set[str] = set()
    results = []
    for row in res.data:
        key = row.get("client_company") or row.get("client_name") or ""
        if key and key not in seen:
            seen.add(key)
            results.append(row)

    # Sort: high → medium → low → healthy
    order = {"high": 0, "medium": 1, "low": 2, "healthy": 3, "unknown": 4}
    results.sort(key=lambda r: order.get(r.get("escalation_risk", "unknown"), 4))
    return results


# ---------------------------------------------------------------------------
# Weekly report
# ---------------------------------------------------------------------------

def get_recent_meetings_for_report(
    pm_id: str, client_name: str, days: int = 7
) -> list[dict]:
    """Pull last N days of meetings for a client. Used by weekly report generator."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = (
        get_db()
        .table("draft_history")
        .select(
            "meeting_type, meeting_date, meeting_summary, "
            "client_action_items, fleetpanda_action_items, next_steps, "
            "escalation_risk, sentiment_summary, client_name, client_company, "
            "client_email, client_email_thread"
        )
        .eq("pm_id", pm_id)
        .or_(f"client_name.ilike.%{client_name}%,client_company.ilike.%{client_name}%")
        .gt("created_at", cutoff)
        .order("meeting_date", desc=True)
        .execute()
    )
    return res.data


# ---------------------------------------------------------------------------
# Data retention
# ---------------------------------------------------------------------------

def prune_old_transcripts(cutoff: datetime) -> int:
    """Null out transcript on records older than cutoff. Returns count of rows updated."""
    res = (
        get_db()
        .table("draft_history")
        .update({"transcript": None})
        .lt("created_at", cutoff.isoformat())
        .not_.is_("transcript", "null")
        .execute()
    )
    return len(res.data)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session(pm_id: str) -> str:
    token = str(uuid.uuid4())
    get_db().table("sessions").insert({"pm_id": pm_id, "token": token}).execute()
    return token


def get_session(token: str) -> dict | None:
    res = (
        get_db()
        .table("sessions")
        .select("*, pms(*)")
        .eq("token", token)
        .gt("expires_at", datetime.now(timezone.utc).isoformat())
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None
