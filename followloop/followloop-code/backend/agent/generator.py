from __future__ import annotations

"""
Claude calls per meeting:
  Call 1 (extractor.py): transcript → structured context JSON
  Call 2 (this file, generate_email): context + style → email draft
  Call 3 (this file, generate_internal_note): context → internal Slack note
  Call 4 (this file, extract_edit_lesson): diff → lesson for autonomous improvement
"""
import json
import os
import re

import anthropic

from agent.prompt_builder import build_prompts

_client = None

# Sample transcript used for style preview (preview_mode=True)
SAMPLE_TRANSCRIPT = """Sarah: Hi Raj, thanks for joining today! Really excited to get Acme Corp set up on FleetPanda.

Raj: Thanks Sarah, same here. We've been looking forward to this.

Sarah: So let's walk through the platform together. I'll share my screen and we can go through the main dashboard.

Raj: Sounds great. Can we also cover the driver app? That's a big concern for our team.

Sarah: Absolutely. So here you can see your full fleet — all 47 vehicles. Each one has real-time GPS, fuel level, and maintenance status.

Raj: This is impressive. How do drivers check in?

Sarah: They use the mobile app. I'll send you the download link after this. And here's a quick demo of the driver workflow.

Raj: Perfect. What about the admin side for our fleet manager?

Sarah: Your admin, Lisa, will have this dashboard. I'll send her a separate onboarding email and schedule a 30-min call. Can you send me her email?

Raj: Sure, it's lisa@acmecorp.com. What's the timeline for going live?

Sarah: We can have you live by next Friday if you complete the vehicle import this week. I'll send you the import template today.

Raj: That works. We'll get that done by Wednesday.

Sarah: Perfect. I'll follow up with the driver app link, Lisa's onboarding invite, and the import template. Any other questions?

Raj: I think that covers it. Thanks again!

Sarah: Thank you Raj, looking forward to working together!"""


def generate_email(
    pm_id: str,
    transcript: str | None,
    context: dict | None,
    preview_mode: bool = False,
    prior_meetings: list[dict] | None = None,
    pm_feedback: str | None = None,
    previous_draft: str | None = None,
    client_email_thread: list[dict] | None = None,
    edit_lessons: list[dict] | None = None,
) -> str:
    """
    Generate a post-meeting summary email.
    If preview_mode=True, uses hardcoded sample data.
    prior_meetings: list of recent drafts for same client (Enhancement 1).
    pm_feedback / previous_draft: used for in-dashboard regeneration (Enhancement 3).
    """
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if preview_mode:
        context = {
            "client_name": "Raj",
            "client_company": "Acme Corp",
            "client_email": "raj@acmecorp.com",
            "meeting_type": "onboarding",
            "meeting_date": "today",
            "meeting_summary": (
                "Onboarding call with Raj from Acme Corp. "
                "Walked through the FleetPanda dashboard, GPS tracking, and driver mobile app. "
                "Discussed admin onboarding for fleet manager Lisa and go-live timeline."
            ),
            "client_action_items": [
                {"action": "Complete vehicle import", "owner": "Raj", "due_date": "Wednesday"},
                {"action": "Share Lisa's email for admin onboarding", "owner": "Raj", "due_date": None},
            ],
            "fleetpanda_action_items": [
                {"action": "Send driver app download link", "owner": "Sarah", "due_date": "today"},
                {"action": "Send vehicle import template", "owner": "Sarah", "due_date": "today"},
                {"action": "Schedule Lisa's admin onboarding call", "owner": "Sarah", "due_date": "this week"},
            ],
            "next_steps": "Go live by next Friday pending vehicle import completion.",
        }
        transcript = SAMPLE_TRANSCRIPT

    system_prompt, user_prompt = build_prompts(
        pm_id=pm_id,
        context=context,
        transcript=transcript or "",
        prior_meetings=prior_meetings,
        pm_feedback=pm_feedback,
        previous_draft=previous_draft,
        client_email_thread=client_email_thread,
        edit_lessons=edit_lessons,
    )

    message = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text.strip()


def generate_internal_note(pm_name: str, context: dict, transcript: str) -> str:
    """
    Enhancement 2: Generate a short candid internal Slack note for the FleetPanda CS team.
    This is NOT sent to the client — it's posted to a shared internal channel.
    Three sections: meeting health, internal actions, flags for leadership (omit if none).
    """
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    fp_items = context.get("fleetpanda_action_items") or []
    fp_items_text = "\n".join(
        f"- {it.get('action', '')} ({it.get('owner', '?')})"
        for it in fp_items
    ) or "None"

    prompt = f"""Write a brief internal Slack note for the FleetPanda customer success team after a meeting.
This is NEVER sent to the client — be candid and direct.

PM: {pm_name}
Client: {context.get('client_name', '')} at {context.get('client_company', '')}
Meeting type: {context.get('meeting_type', '')}
Summary: {context.get('meeting_summary', '')}
Next steps: {context.get('next_steps', '')}

FleetPanda internal action items:
{fp_items_text}

Transcript (first 3000 chars for context):
{(transcript or '')[:3000]}

Write exactly 2-3 sections using Slack mrkdwn format:
1. *Meeting health* — one candid sentence about how the meeting went and client sentiment. Use :white_check_mark: (positive), :warning: (neutral/concern), or :rotating_light: (at-risk/urgent).
2. *Internal actions* — bullet list with named owners. Only items FleetPanda needs to do that are NOT already in the client email.
3. *Flags for leadership* — only include if there is something escalation-worthy (churn risk, competitor mention, contract question, blocker). Omit this section entirely if nothing to flag.

Keep it under 150 words total. No fluff."""

    message = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def extract_edit_lesson(
    agent_draft: str,
    sent_draft: str,
    edit_diff: dict,
    transcript: str,
    meeting_type: str,
) -> dict:
    """
    Call 4: analyze what the PM changed and extract a reusable lesson.
    Called by edit_detection.py when was_edited=True.
    Returns a structured dict stored in draft_history.edit_lesson.
    """
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    removed = "\n".join(edit_diff.get("removed", []))
    added = "\n".join(edit_diff.get("added", []))

    prompt = f"""A PM edited an AI-generated meeting summary email before sending it.
Analyze what was changed and extract one specific, actionable lesson to improve future drafts.

Meeting type: {meeting_type}

LINES REMOVED by PM:
{removed or "(none)"}

LINES ADDED by PM:
{added or "(none)"}

Transcript excerpt (first 2000 chars for context):
{(transcript or "")[:2000]}

Return ONLY valid JSON with no markdown:
{{
  "issue_type": "missing_info | wrong_tone | poor_organization | incorrect_detail | too_long | too_short | other",
  "severity": "minor | moderate | significant",
  "description": "one sentence: what specifically was wrong with the draft",
  "lesson": "one actionable instruction starting with a verb (e.g. 'Always include...', 'Never use...', 'When the client mentions X, include Y')"
}}"""

    message = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)
