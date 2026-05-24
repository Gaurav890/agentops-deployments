# Prompt Design

## Overview

Two Claude calls per meeting. Both use `claude-sonnet-4-5`.

---

## Call 1: Context Extraction (`agent/extractor.py`)

**Purpose:** Parse raw transcript + meeting metadata into structured JSON.

**System prompt:** None (single-turn extraction task)

**User prompt structure:**
```
Extract structured information from this meeting transcript and metadata.

Meeting title: {title}
Attendees: {attendees_json}

Transcript:
{transcript, truncated to 4000 chars}

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

**Fallback logic in code:** If `client_email` is empty, use first non-FleetPanda attendee email from Avoma metadata.

---

## Call 2: Email Generation (`agent/generator.py`)

**Purpose:** Write the actual email in the PM's personal style.

**System prompt structure:**
```
You are drafting a post-meeting summary email for {pm_name} at FleetPanda.

STYLE RULES:
- Open with "Hi [First Name]," never "Dear"
- Warm, specific thank-you opener about what was accomplished
- Never write "I hope this email finds you well"
- Bold section headers when 3+ topics covered
- TL;DR bullets only when 4+ topics covered
- Every action item has an explicit named owner
- Close with "Best, {pm_name}" always
- Concise and warm, not corporate

HERE ARE REAL EMAILS {PM_NAME} HAS WRITTEN:

--- EXAMPLE 1 ({meeting_type}) ---
{sample_email_1}
--- END ---

--- EXAMPLE 2 ({meeting_type}) ---
{sample_email_2}
--- END ---

Match {pm_name}'s exact tone, opener style, and sign-off. Do not add sections they don't use.
```

**User prompt structure:**
```
Write a post-meeting summary email for this meeting.

CLIENT: {client_name} at {client_company}
MEETING TYPE: {meeting_type}
DATE: {date}

SUMMARY: {meeting_summary}

CLIENT ACTION ITEMS:
{formatted list}

FLEETPANDA ACTION ITEMS:
{formatted list}

NEXT STEPS: {next_steps}

TRANSCRIPT (for specific details and tone):
{transcript, truncated to 5000 chars}

Write only the email body. No subject line. Start with "Hi {client_name},"
```

---

## Style sample selection logic

In `prompt_builder.py`:

1. Query `style_samples` where `pm_id = X` AND `meeting_type = current_type`, ordered by `created_at DESC`, limit 2
2. If fewer than 2 results, backfill with any samples for that PM (different meeting types), limit to total of 3
3. If PM has 0 samples, omit the examples block entirely (agent will still work, just without style calibration)

## Style preview (frontend training page)

Same generation call but with:
- Hardcoded sample transcript (defined in `generator.py` as `SAMPLE_TRANSCRIPT`)
- Fake context: onboarding meeting, client "Raj", Acme Corp
- `preview_mode=True` parameter

This lets PMs see how their style samples affect the output before going live.

---

## Email output format (what Claude should produce)

Plain text only. No HTML. Gmail renders plain text cleanly.

For simple meetings (1-2 topics):
```
Hi [Name],

[Warm 1-line opener specific to what was accomplished]

[2-3 sentence summary]

Your action items:
1. [Action] — [Owner]

Our action items:
1. [Action] — [Owner] — [Due date if mentioned]

[Next steps / closing line]

Best,
[PM Name]
```

For complex meetings (3+ topics): add bold headers. For 4+ topics: add TL;DR bullets after opener.
