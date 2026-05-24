# Agent 5 — Feedback Loop Learner

**Pattern:** [Feedback Loop Learner](../../../agent-templates/feedback-loop-learner/) · **Pipeline position:** 5 of 6

The agent that makes Followloop *learn*. Runs on a 30-minute background loop, diffs each draft against what the PM actually sent, and extracts a generalizable lesson for future drafts.

- **Model:** `claude-sonnet-4-5`
- **Max tokens:** 256
- **Trigger:** edit-detection job (cron, 30 min interval) — only fires when `was_edited=True` and the diff is non-empty
- **Output:** structured JSON (`issue_type`, `severity`, `description`, `lesson`)

---

## Why this agent exists in isolation

Most LLM-powered tools are static after deployment. The PM corrects the same kind of error every week, and the system never learns. The Edit Lesson Extractor closes that loop without asking the PM to articulate anything explicitly — the only signal it needs is what the PM already does naturally: edit before sending.

This is also the agent the product is named for: the **loop** in Followloop.

---

## Mechanism (how it gets called)

1. Every 30 minutes, the background scheduler queries `pending` drafts older than 20 minutes.
2. For each, it pulls the PM's Gmail SENT folder and matches by subject + a 2-hour window.
3. It computes a line-level diff between the agent's draft and what was actually sent.
4. If `was_edited=True` and the diff is non-empty, the diff is passed to this prompt.
5. The returned lesson is stored on the draft row and injected into all future Email Generator system prompts (deduplicated).

The full mechanism lives in `jobs/edit_detection.py` in the production codebase.

---

## Prompt (verbatim)

```text
A PM edited an AI-generated meeting summary email before sending it.
Analyze what was changed and extract one specific, actionable lesson to improve future drafts.

Meeting type: {meeting_type}

LINES REMOVED by PM:
{removed lines, joined by newline}

LINES ADDED by PM:
{added lines, joined by newline}

Transcript excerpt (first 2000 chars for context):
{transcript[:2000]}

Return ONLY valid JSON with no markdown:
{
  "issue_type": "missing_info | wrong_tone | poor_organization | incorrect_detail | too_long | too_short | other",
  "severity": "minor | moderate | significant",
  "description": "one sentence: what specifically was wrong with the draft",
  "lesson": "one actionable instruction starting with a verb (e.g. 'Always include...', 'Never use...', 'When the client mentions X, include Y')"
}
```

---

## Design notes

### "One actionable instruction starting with a verb"

This is the single most important constraint in the prompt. Without it, the model returns lessons like *"the email was a bit too formal"* — which is **a description of the past, not a rule for the future**. A good lesson has the shape of a prompt-rule that can be appended verbatim to the Email Generator's system prompt: *"Never use 'I hope this email finds you well'."* The verb requirement enforces this shape.

### Why diff lines, not full draft + full sent

Sending both full versions costs 2x the tokens and gives the model too much room to invent reasons for the change. A diff is small, focused, and forces the analysis to be about *what actually changed*.

### Severity isn't used by the runtime — yet

`severity` is collected for future use (dedup priority, weekly review filtering) but the runtime currently injects all lessons regardless. Keeping the field in the schema means we can act on it later without re-running historical drafts.

### Fail-soft on extraction errors

The edit-detection job wraps this call in a try/except and continues — a failed lesson is non-fatal. The draft's edit info still gets recorded; only the lesson row is skipped. This is intentional: edit detection has to be reliable, lesson extraction is a nice-to-have.

---

## Where lessons go after extraction

The lesson string is injected into the Email Generator's system prompt under a `LESSONS FROM PAST DRAFTS YOU EDITED` block. See [agent-2-customer-email-writer.md](./agent-2-customer-email-writer.md) for the receiving end.

Deduplication is by lesson string equality with normalization. A more sophisticated approach (semantic dedup via embedding) is on the roadmap but hasn't been needed at current scale.

---

## What changes per deployment

- The `issue_type` enum — these are the failure modes specific to email follow-ups; other domains will have different ones (e.g. for a code-review agent: `wrong_severity`, `missed_security_issue`, `over-flagged`).
- The transcript context window — depends on what the source artifact looks like.
