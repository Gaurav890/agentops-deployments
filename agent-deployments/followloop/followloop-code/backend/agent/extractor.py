"""
Call 1 of 2 Claude calls per meeting.
Parses raw transcript + metadata into a structured context dict.
"""
import json
import os
import re

import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def extract_context(transcript: str, metadata: dict) -> dict:
    """
    Returns a dict with keys:
      client_name, client_company, client_email, meeting_type,
      meeting_summary, client_action_items, fleetpanda_action_items, next_steps
    """
    attendees_json = json.dumps(metadata.get("attendees", []))

    prompt = f"""Extract structured information from this meeting transcript and metadata.

Meeting title: {metadata.get('title', '')}
Attendees: {attendees_json}

Transcript:
{transcript or ""}

Return ONLY valid JSON with this exact structure:
{{
  "client_name": "first name of primary client contact",
  "client_company": "company name",
  "client_email": "primary client email",
  "meeting_type": "onboarding|weekly_sync|qbr|kickoff|escalation|other",
  "meeting_summary": "2-3 sentences on what was covered",
  "client_action_items": [
    {{"action": "...", "owner": "name", "due_date": "date or null"}}
  ],
  "fleetpanda_action_items": [
    {{"action": "...", "owner": "PM name", "due_date": "date or null"}}
  ],
  "next_steps": "suggested follow-up"
}}"""

    message = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown code fences
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    context = json.loads(raw)

    # Fallback: if client_email is empty, use first non-FleetPanda attendee
    if not context.get("client_email"):
        for attendee in metadata.get("attendees", []):
            email = attendee.get("email", "")
            if email and "@fleetpanda.com" not in email:
                context["client_email"] = email
                break

    return context
