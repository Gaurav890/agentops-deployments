# Agent 6 — Weekly Rollup Writer

**Pattern:** rollup writer (different cadence from Agent 2 — runs per-week, not per-meeting) · **Pipeline position:** 6 of 6

On-demand, generates a formatted weekly status report for any active customer by rolling up the last ~14 days of accumulated context.

- **Model:** `claude-sonnet-4-5`
- **Max tokens:** 2048
- **Inputs:** PM/client metadata, recent meeting records (with extractor + analyzer outputs already attached), email thread excerpts, week-ending date
- **Output:** plain-text report following an exact six-section template

---

## Why this agent exists in isolation

Different cadence. Different rollup. Different consumer.

The Email Generator and Internal Note run **per-meeting** on a single transcript. The Weekly Report runs **per-week per-client** and needs to:

- Differentiate THIS WEEK from LAST WEEK across multiple meetings
- Surface commitments made over email between meetings
- Roll up sentiment trend across multiple meetings into one overall status color
- Conform to a fixed external template the customer expects

A per-meeting agent has none of this machinery. Forcing one prompt to handle both cadences was the architectural smell that motivated splitting it out.

---

## Prompt (verbatim)

```text
You are writing a weekly status report for a FleetPanda implementation manager.
Follow the EXACT template structure below. Write in a professional, concise, client-facing tone.

CLIENT: {client_company or client_name}
TO: {contact_name}
DATE: {week_ending_fmt}
PREPARED BY: {pm_name} | {pm_email}
OVERALL PROJECT STATUS: {overall_status}

MEETINGS (this week + last week — labeled accordingly):
{meetings_text}

{email_context_section, only present if email thread has content:
EMAIL CORRESPONDENCE WITH CUSTOMER THIS WEEK:
---
{combined_email_context}
---
Use this to surface any commitments made via email, customer concerns raised outside of meetings,
and any context that should appear in Issues for Management Attention or Client Responsibilities.
}

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
Keep the milestone table row as a literal placeholder text since we don't have that data automatically.
```

---

## Where the inputs come from

### `meetings_text` — labeled per-meeting context

For each meeting in the rollup window, the calling code formats:

```text
[THIS WEEK]
Meeting (2026-04-12, weekly_sync):
Summary: ...
FleetPanda items: ...; ...
Client items: ...; ...
Next steps: ...
Sentiment: {sentiment_summary} (risk: {escalation_risk})
```

Meetings are bucketed into `[THIS WEEK]` vs `[LAST WEEK]` based on `week_ending - 6 days`. The agent uses the labels to allocate content to "work completed" vs. "background."

### `overall_status` — derived, not generated

The Red/Yellow/Green status is computed by the calling code from the most recent meeting's `escalation_risk` (mapping `high → Red`, `medium/low → Yellow`, `healthy → Green`). The agent doesn't decide status — it consumes a precomputed value. This avoids the model second-guessing risk levels that the dedicated Escalation Analyzer already produced.

### `email_context_section` — conditionally injected

The block is only added if there are non-empty email threads to surface. Omitting an empty block is cleaner than letting the model handle "(none)" gracefully.

---

## Design notes

### EXACT template, EXACT order

Capitalized "EXACT" in the prompt is deliberate. The receiving customer expects the same six sections in the same order every week. Deviation costs more credibility than verbosity does.

### Why the milestone row is a placeholder, not omitted

The structured milestone table can't be auto-filled (the PM owns it manually outside this system). Telling the model to *omit* the row would break the template integrity for the reader; telling it to leave a literal placeholder preserves the template and makes the manual edit obvious.

### `[THIS WEEK]` vs `[LAST WEEK]` labels

Without the labels, the model treats all meetings as equally recent and over-reports last week as current progress. Pre-bucketing the meetings is a cheap way to encode time without making the model do date math.

### Defensive `If the transcript is too short` clause is **not** in this prompt

Unlike the Extractor or Escalation Analyzer, the Weekly Report assumes input is well-formed because the upstream pipeline has already structured it. Defensive fallbacks belong on the boundary agents, not the rollup ones.

---

## What changes per deployment

- The six-section template — your customers expect a different structure
- The status color mapping (Red/Yellow/Green vs. RAG vs. numeric)
- The rollup window (14-day default; some teams want monthly, some bi-weekly)
- The "Issues for Management Attention" framing — sales teams might want "Deal Risks Surfaced This Week" instead
