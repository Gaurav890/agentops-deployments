# Agent 1 — Structured Extractor

**Pattern:** [Structured Extraction](../../../agent-templates/structured-extraction/) · **Pipeline position:** 1 of 6

Parses the raw transcript + meeting metadata into a structured JSON context object that every downstream agent consumes. Never writes prose.

- **Model:** `claude-sonnet-4-5`
- **Max tokens:** 4096
- **Output:** structured JSON (parsed, with markdown-fence stripping as a defensive belt)

---

## Why this agent exists in isolation

Extraction errors compound. If the extractor confuses a client-side action item with an internal one, every downstream agent inherits the mistake — the email assigns the wrong owner, the internal note misroutes the follow-up, the weekly report rolls up against the wrong column. By forcing the first stage to produce *only* a typed schema (no prose, no commentary), parsing failures are loud rather than silent.

This is the single biggest quality unlock in the Followloop architecture: **don't ask one prompt to parse and generate**.

---

## Prompt (verbatim from production)

```text
Extract structured information from this meeting transcript and metadata.

Meeting title: {title}
Attendees: {attendees_json}

Transcript:
{transcript}

Return ONLY valid JSON with this exact structure:
{
  "client_name": "first name of primary client contact",
  "client_company": "company name",
  "client_email": "primary client email",
  "meeting_type": "onboarding|weekly_sync|qbr|kickoff|escalation|other",
  "meeting_summary": "2-3 sentences on what was covered",
  "client_action_items": [
    {"action": "...", "owner": "name", "due_date": "date or null"}
  ],
  "fleetpanda_action_items": [
    {"action": "...", "owner": "PM name", "due_date": "date or null"}
  ],
  "next_steps": "suggested follow-up"
}
```

---

## Design notes

- **Fixed enum for `meeting_type`.** Free-text classification drifts; downstream agents (especially the Email Generator) branch on this field, so it must be one of a known set.
- **Action items split by owner side.** `client_action_items` vs. `fleetpanda_action_items` is the load-bearing distinction — every agent below uses it to decide what to communicate to whom.
- **Defensive markdown stripping.** Even with a "return ONLY JSON" instruction, models occasionally wrap the response in ```` ```json ... ``` ````. Strip it before parsing rather than tightening the prompt — cheaper than a retry.
- **Attendee fallback.** If the model doesn't return `client_email`, the calling code falls back to the first non-internal-domain attendee. Defensive code, not a prompt fix.

---

## What changes per deployment

- The enum values for `meeting_type` (your domain has different ones)
- The owner-side split (`fleetpanda_action_items` → your team's name)
- The schema fields themselves, if downstream agents need different inputs
