# Agent 3 — Internal Note Writer

**Pattern:** sibling of Voice-Matching Writer, but for an internal audience · **Pipeline position:** 3 of 6

Generates a candid internal Slack note for the customer-success team after each meeting. **Never sent to the customer.**

- **Model:** `claude-sonnet-4-5`
- **Max tokens:** 512
- **Output:** Slack mrkdwn-formatted note, ≤150 words

---

## Why this agent exists in isolation

Customer-facing and internal-facing writing have different optimization targets:

- The **customer email** optimizes for clarity, trust, and a tone the PM wants the client to receive.
- The **internal note** optimizes for actionability, candor, and risk surfacing — including things the PM would never say in front of the customer.

Trying to derive one from the other compromises both. The customer email turns gossipy when it inherits internal candor; the internal note turns sanitized when it inherits customer-facing politeness. Different audience, different prompt, different agent.

---

## Prompt (verbatim)

```text
Write a brief internal Slack note for the FleetPanda customer success team after a meeting.
This is NEVER sent to the client — be candid and direct.

PM: {pm_name}
Client: {client_name} at {client_company}
Meeting type: {meeting_type}
Summary: {meeting_summary}
Next steps: {next_steps}

FleetPanda internal action items:
- {action} ({owner})
...

Transcript (first 3000 chars for context):
{transcript[:3000]}

Write exactly 2-3 sections using Slack mrkdwn format:
1. *Meeting health* — one candid sentence about how the meeting went and client sentiment. Use :white_check_mark: (positive), :warning: (neutral/concern), or :rotating_light: (at-risk/urgent).
2. *Internal actions* — bullet list with named owners. Only items FleetPanda needs to do that are NOT already in the client email.
3. *Flags for leadership* — only include if there is something escalation-worthy (churn risk, competitor mention, contract question, blocker). Omit this section entirely if nothing to flag.

Keep it under 150 words total. No fluff.
```

---

## Design notes

### "Never sent to the client — be candid and direct"

This single instruction is what unlocks the agent. Without it, the model defaults to its corporate-voice default and produces a shorter version of the customer email. The candor framing is load-bearing.

### Health emoji as a one-glance summary

The CS team scans Slack at speed. A `:rotating_light:` in the first line of the note routes attention faster than any prose. The emoji is part of the *interface*, not decoration.

### "Only items NOT already in the client email"

The internal note is supposed to be **additive** to the customer email, not a duplicate. Without this constraint, the agent re-lists every fleet-side action item, which adds noise without value. The instruction cuts the note in half on most meetings.

### Conditional "Flags for leadership"

Most meetings don't have leadership-worthy flags. Forcing the section to always be present trains readers to skip it; making it conditional ("Omit this section entirely if nothing to flag") preserves the signal value.

### Why the Escalation Analyzer is still separate

This agent has a "meeting health" line, but it's a one-sentence narrative read for human eyes. The Escalation Analyzer produces a structured `risk_level` field with quote-grounded `signals` for cross-portfolio sorting. Different shape, different consumer, different agent.

---

## What changes per deployment

- Team name (`FleetPanda customer success team`)
- Section names — your team has different categories (e.g. for a sales team: `Deal health`, `Next-step risk`, `Coach asks`)
- Slack mrkdwn → whatever channel formatting your team uses (Teams, Discord, plain email digest)
- The 150-word cap — calibrate to how your team actually reads
