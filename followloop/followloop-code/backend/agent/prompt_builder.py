"""
Builds the system and user prompts for email generation (Call 2).
Fetches style samples from DB and injects them as few-shot examples.
"""
from db.models import get_style_samples, get_pm_by_id


def _format_prior_meetings(meetings: list[dict]) -> str:
    """
    Format the last N meetings with this client (oldest first) for injection into
    the system prompt. Includes what was sent to the client, so Claude knows actual
    commitments made — not just what was discussed in the meeting.
    """
    if not meetings:
        return ""
    parts = []
    for i, m in enumerate(reversed(meetings), 1):  # reverse so oldest prints first
        date = (m.get("meeting_date") or "")[:10]
        mtype = (m.get("meeting_type") or "").replace("_", " ")
        summary = m.get("meeting_summary") or ""
        items = m.get("client_action_items") or []
        items_text = "\n".join(
            f"  - {it.get('action', '')} (owner: {it.get('owner', '?')})"
            for it in items
        ) or "  - None recorded"
        # Prefer the actual sent email; fall back to the agent draft
        email_sent = m.get("sent_draft") or m.get("agent_draft") or ""
        email_block = (
            f"Email sent to client after this meeting:\n{email_sent}"
            if email_sent
            else "Email: not yet sent"
        )
        parts.append(
            f"Meeting {i} — {date} ({mtype})\n"
            f"Summary: {summary}\n"
            f"{email_block}\n"
            f"Client action items from that meeting:\n{items_text}"
        )
    total = len(meetings)
    return (
        f"\nPRIOR MEETINGS WITH THIS CLIENT ({total} previous session{'s' if total != 1 else ''}, oldest → newest):\n\n"
        + "\n\n".join(parts)
        + "\n\nReference relevant history naturally where it adds value. "
          "The sent emails reflect actual commitments made to this client — treat them as ground truth. "
          "If client action items from previous meetings appear unresolved in the current transcript, "
          "note they are still open."
    )


def _format_email_thread(emails: list[dict]) -> str:
    """
    Format the email thread between PM and client since the last meeting.
    Gives Claude full visibility into what was already communicated and resolved.
    """
    if not emails:
        return ""
    parts = []
    for e in emails:
        parts.append(
            f"{e['date_str']} | {e['from_header']} → {e['to_header']}\n"
            f"Subject: {e['subject']}\n"
            f"{e['body_text']}"
        )
    return (
        "\nEMAIL THREAD WITH THIS CLIENT SINCE LAST MEETING (oldest → newest):\n\n"
        + "\n\n---\n\n".join(parts)
        + "\n\nUse this to understand what was already communicated and resolved. "
          "Do not repeat information already covered in these emails. "
          "If something from these emails is still pending or unresolved, note it."
    )


def _format_edit_lessons(lessons: list[dict]) -> str:
    """
    Format lessons extracted from previous drafts the PM edited.
    Injected into system prompt so the agent improves without any manual input.
    """
    if not lessons:
        return ""
    lines = [f"- {l.get('lesson', '')}" for l in lessons if l.get("lesson")]
    if not lines:
        return ""
    return (
        "\nLESSONS FROM PAST DRAFTS YOU EDITED (apply to every email):\n"
        + "\n".join(lines)
    )


def build_prompts(
    pm_id: str,
    context: dict,
    transcript: str,
    prior_meetings: list[dict] | None = None,
    pm_feedback: str | None = None,
    previous_draft: str | None = None,
    client_email_thread: list[dict] | None = None,
    edit_lessons: list[dict] | None = None,
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for the email generation call.
    """
    pm = get_pm_by_id(pm_id)
    pm_name = pm["name"] if pm else "the PM"
    meeting_type = context.get("meeting_type", "other")

    # Fetch up to 3 style samples, prefer same meeting type
    samples = get_style_samples(pm_id, meeting_type=meeting_type, limit=3)

    # Build examples block
    examples_block = ""
    if samples:
        parts = []
        for i, sample in enumerate(samples, start=1):
            parts.append(
                f"--- EXAMPLE {i} ({sample['meeting_type']}) ---\n"
                f"{sample['email_body']}\n"
                f"--- END ---"
            )
        examples_block = (
            f"\nHERE ARE REAL EMAILS {pm_name.upper()} HAS WRITTEN:\n\n"
            + "\n\n".join(parts)
        )

    # Build context blocks
    edit_lessons_block = _format_edit_lessons(edit_lessons or [])
    prior_meetings_block = _format_prior_meetings(prior_meetings or [])
    email_thread_block = _format_email_thread(client_email_thread or [])

    system_prompt = f"""You are drafting a post-meeting summary email for {pm_name} at FleetPanda.

STYLE RULES:
- Open with "Hi [First Name]," never "Dear"
- Warm, specific thank-you opener about what was accomplished
- Never write "I hope this email finds you well"
- Use **bold** for section headers when 3+ topics covered
- Use - bullet points for action items and lists
- TL;DR bullets only when 4+ topics covered
- Every action item has an explicit named owner
- Close with "Best, {pm_name}" always
- Concise and warm, not corporate
{edit_lessons_block}
{prior_meetings_block}
{email_thread_block}
{examples_block}
Match {pm_name}'s exact tone, opener style, and sign-off. Do not add sections they don't use."""

    # Format action items
    client_items = context.get("client_action_items", [])
    fp_items = context.get("fleetpanda_action_items", [])

    def fmt_items(items: list) -> str:
        if not items:
            return "None"
        lines = []
        for item in items:
            due = f" — {item['due_date']}" if item.get("due_date") else ""
            lines.append(f"- {item['action']} — {item.get('owner', 'TBD')}{due}")
        return "\n".join(lines)

    # Enhancement 3: session number for continuity
    total_sessions = len(prior_meetings) + 1 if prior_meetings else 1
    session_prefix = f"SESSION {total_sessions}" if prior_meetings else ""

    # Enhancement 3: prepend PM feedback for regeneration calls
    feedback_block = ""
    if pm_feedback:
        prev = f"\n\nPrevious draft for reference:\n{previous_draft}" if previous_draft else ""
        feedback_block = (
            f"PM FEEDBACK ON PREVIOUS DRAFT (incorporate this):\n{pm_feedback}"
            f"{prev}\n\n"
        )

    user_prompt = f"""{feedback_block}Write a post-meeting summary email for this meeting.

CLIENT: {context.get('client_name', '')} at {context.get('client_company', '')}
MEETING TYPE: {meeting_type}{f' | {session_prefix}' if session_prefix else ''}
DATE: {context.get('meeting_date', '')}

SUMMARY: {context.get('meeting_summary', '')}

CLIENT ACTION ITEMS:
{fmt_items(client_items)}

FLEETPANDA ACTION ITEMS:
{fmt_items(fp_items)}

NEXT STEPS: {context.get('next_steps', '')}

TRANSCRIPT (for specific details and tone):
{transcript or ""}

Write only the email body. No subject line. Start with "Hi {context.get('client_name', '[Name]')},"
"""

    return system_prompt, user_prompt
