"""
Weekly status report generator.
Produces copy-paste text following the FleetPanda status report template.
"""
import os
from datetime import datetime

import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def generate_weekly_report(
    pm_name: str,
    pm_email: str,
    client_name: str,
    client_company: str,
    contact_name: str,
    week_ending: str,
    recent_meetings: list[dict],
    email_thread: str = "",
) -> str:
    """
    Generate a weekly status report following the FleetPanda template.

    Args:
        pm_name: PM's full name (e.g. "Gaurav Chaulagain")
        pm_email: PM's email
        client_name: Primary contact first name
        client_company: Company name (e.g. "Valley Pacific Petroleum")
        contact_name: Full name of client contact to address report to
        week_ending: ISO date string for the week (e.g. "2026-04-15")
        recent_meetings: List of draft_history records from the past 7 days

    Returns:
        Plain text report ready to copy-paste, following the FleetPanda template.
    """
    # Build meeting context for Claude
    meeting_context_parts = []
    for m in recent_meetings:
        date = (m.get("meeting_date") or m.get("created_at") or "")[:10]
        summary = m.get("meeting_summary", "")
        completed_items = m.get("fleetpanda_action_items") or []
        client_items = m.get("client_action_items") or []
        next_steps = m.get("next_steps", "")
        escalation_risk = m.get("escalation_risk", "healthy")
        sentiment = m.get("sentiment_summary", "")

        # Format action items (handle both string and {action, owner} format)
        def fmt_items(items):
            out = []
            for item in items:
                if isinstance(item, dict):
                    out.append(item.get("action", ""))
                else:
                    out.append(str(item))
            return [x for x in out if x]

        fp_items = fmt_items(completed_items)
        cl_items = fmt_items(client_items)

        part = f"Meeting ({date}, {m.get('meeting_type', 'other')}):\n"
        if summary:
            part += f"Summary: {summary}\n"
        if fp_items:
            part += "FleetPanda items: " + "; ".join(fp_items) + "\n"
        if cl_items:
            part += "Client items: " + "; ".join(cl_items) + "\n"
        if next_steps:
            part += f"Next steps: {next_steps}\n"
        if sentiment:
            part += f"Sentiment: {sentiment} (risk: {escalation_risk})\n"
        meeting_context_parts.append(part)

    if meeting_context_parts:
        # Label meetings as "this week" vs "last week" relative to week_ending
        from datetime import date, timedelta
        try:
            week_end_date = date.fromisoformat(week_ending) if week_ending else date.today()
            week_start_date = week_end_date - timedelta(days=6)  # Monday of this week
        except Exception:
            week_start_date = None

        labeled_parts = []
        for i, (m, part) in enumerate(zip(recent_meetings, meeting_context_parts)):
            meeting_date_str = (m.get("meeting_date") or m.get("created_at") or "")[:10]
            if week_start_date and meeting_date_str:
                try:
                    mdate = date.fromisoformat(meeting_date_str)
                    label = "THIS WEEK" if mdate >= week_start_date else "LAST WEEK"
                    labeled_parts.append(f"[{label}]\n{part}")
                except Exception:
                    labeled_parts.append(part)
            else:
                labeled_parts.append(part)
        meetings_text = "\n---\n".join(labeled_parts)
    else:
        meetings_text = "No meetings in the past two weeks."

    # Combine auto-fetched email threads from meetings + manually pasted thread
    auto_email_threads = []
    for m in recent_meetings:
        thread = (m.get("client_email_thread") or "").strip()
        if thread:
            auto_email_threads.append(thread)
    combined_email_context = "\n\n---\n\n".join(filter(None, auto_email_threads + [email_thread.strip()]))

    # Infer overall status from escalation risk of most recent meeting
    latest_risk = (recent_meetings[0].get("escalation_risk") or "healthy") if recent_meetings else "healthy"
    status_map = {"high": "Red", "medium": "Yellow", "low": "Yellow", "healthy": "Green", "unknown": "Green"}
    overall_status = status_map.get(latest_risk, "Green")

    week_ending_fmt = datetime.fromisoformat(week_ending).strftime("%m-%d-%Y") if week_ending else ""

    email_context_section = ""
    if combined_email_context:
        email_context_section = f"""
EMAIL CORRESPONDENCE WITH CUSTOMER THIS WEEK:
---
{combined_email_context}
---
Use this to surface any commitments made via email, customer concerns raised outside of meetings,
and any context that should appear in Issues for Management Attention or Client Responsibilities.
"""

    prompt = f"""You are writing a weekly status report for a FleetPanda implementation manager.
Follow the EXACT template structure below. Write in a professional, concise, client-facing tone.

CLIENT: {client_company or client_name}
TO: {contact_name}
DATE: {week_ending_fmt}
PREPARED BY: {pm_name} | {pm_email}
OVERALL PROJECT STATUS: {overall_status}

MEETINGS (this week + last week — labeled accordingly):
{meetings_text}
{email_context_section}
Use [THIS WEEK] meetings to populate "work completed" and "next steps".
Use [LAST WEEK] meetings as background context for what was previously committed or in progress.
Use the email correspondence to surface any commitments made via email, customer questions answered,
or items promised/delivered between meetings that are not covered by meeting summaries.

Generate the report with these EXACT sections in this EXACT order. Use bullet points (•) for all lists.
Do NOT add extra sections. Do NOT include section numbers.

---TEMPLATE START---

[CLIENT COMPANY] — [Project Phase, inferred from context]
To: [contact_name]  Date: [date]
Prepared by: [pm_name]  [pm_email]

Issues for Management Attention
• [2-4 bullet points: current blockers, risks, or items needing exec awareness. Be specific.]

Milestone  |  Start Date  |  End Date  |  Status
[MILESTONE TABLE PLACEHOLDER — Fill in your project milestones here]

Summary of work completed this period
• [3-5 bullet points summarizing what was accomplished this week, based on the meeting data]

Summary of work planned for next period
• [3-5 bullet points of what will be done next week, based on next steps and planned items]

Client Responsibilities
• [2-4 bullet points of what the client needs to do]

Overall Project Status: {overall_status}

Next Steps / Joint Action Items
• [3-5 bullet points of the most important next steps for both sides]

---TEMPLATE END---

Write the full report now. Replace all [...] placeholders with real content from the meeting data.
Keep the milestone table row as a literal placeholder text since we don't have that data automatically."""

    message = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
