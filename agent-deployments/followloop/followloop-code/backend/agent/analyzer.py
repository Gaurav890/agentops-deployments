"""
Call 3 of 3 Claude calls per meeting.
Analyzes transcript for escalation risk and customer sentiment.
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


def analyze_escalation(transcript: str, context: dict, meeting_type: str) -> dict:
    """
    Analyze customer sentiment and escalation risk from a meeting transcript.

    Returns:
        {
          "risk_level": "high" | "medium" | "low" | "healthy",
          "signals": ["specific quote or observation", ...],
          "sentiment_summary": "1-2 sentence plain-English summary of customer mood"
        }
    """
    client_name = context.get("client_name", "the client")
    client_company = context.get("client_company", "")

    prompt = f"""You are analyzing a meeting transcript to assess customer health and escalation risk.

Client: {client_company or client_name}
Meeting type: {meeting_type}

Transcript:
{transcript or ""}

Assess the customer's sentiment and flag any escalation risk. Look for:
- Explicit frustration or dissatisfaction ("this isn't working", "we're stuck", "frustrated", "disappointed")
- Repeated unresolved blockers from prior sessions mentioned in this meeting
- Deadline pressure or urgency signals ("we need this by", "running out of time", "executive is asking")
- Escalation language ("I'll need to escalate", "management is asking", "this is becoming a problem")
- Missed commitments or broken trust signals
- Positive signals that counter risk (successful milestones, praise, confidence expressed)

Risk level definitions:
- "high": Customer is frustrated, expressing urgency, or signaling potential escalation. Immediate attention needed.
- "medium": Some friction or unresolved issues, but no explicit frustration. Monitor closely.
- "low": Minor concerns mentioned but overall positive. Routine follow-up sufficient.
- "healthy": Customer is engaged, positive, meeting objectives. No concerns.

Return ONLY valid JSON:
{{
  "risk_level": "high|medium|low|healthy",
  "signals": ["specific quote or observation that drove the assessment", "..."],
  "sentiment_summary": "1-2 sentences describing customer mood and key dynamics"
}}

If the transcript is too short or unclear to assess, return risk_level "low" with an appropriate summary."""

    message = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "risk_level": "low",
            "signals": [],
            "sentiment_summary": "Unable to assess sentiment from this transcript.",
        }

    # Normalize risk_level
    if result.get("risk_level") not in ("high", "medium", "low", "healthy"):
        result["risk_level"] = "low"

    return result
