# Followloop Prompts

The six system prompts that run Followloop in production, captured verbatim from the deployed code. Each prompt is a domain-specific instance of one of the patterns in [/agent-templates/](../../../agent-templates/) — read these to see what a pattern looks like when it's pinned to one workflow.

---

## Pipeline order

```
Avoma webhook
     │ (transcript ready)
     ▼
┌───────────────────────────────┐
│ Agent 1 — Structured Extractor│  ← parses transcript → typed JSON context
└───────────────┬───────────────┘
                │
   ┌────────────┼────────────────────────┐
   ▼            ▼                        ▼
┌─────────┐ ┌──────────┐         ┌────────────────┐
│ Agent 2 │ │ Agent 3  │         │ Agent 4        │
│ Email   │ │ Internal │         │ Risk           │
│ Writer  │ │ Note     │         │ Classifier     │
└────┬────┘ └──────────┘         └────────────────┘
     │
     │ (draft → user edits → sends)
     ▼
┌───────────────────────────────┐
│ Agent 5 — Feedback Loop       │  ← async, every 30 min
│ Learner                       │     diffs draft vs sent → rule
└───────────────┬───────────────┘
                │ (rules injected back into Agent 2)
                ▼
       feeds future drafts

Separately, on-demand or weekly cron:

┌───────────────────────────────┐
│ Agent 6 — Weekly Rollup Writer│  ← rolls up 14 days for one client
└───────────────────────────────┘
```

---

## The six agents

| # | File | Pattern | One-line job |
| --- | --- | --- | --- |
| 1 | [agent-1-structured-extractor.md](./agent-1-structured-extractor.md) | [Structured Extraction](../../../agent-templates/structured-extraction/) | Parse transcript + metadata into typed JSON. Never writes prose. |
| 2 | [agent-2-customer-email-writer.md](./agent-2-customer-email-writer.md) | [Voice-Matching Writer](../../../agent-templates/voice-matching-writer/) | Draft the customer-facing follow-up email in the PM's voice. |
| 3 | [agent-3-internal-note-writer.md](./agent-3-internal-note-writer.md) | sibling of Voice-Matching Writer, internal audience | Candid Slack note for the CS team. Never sent to the customer. |
| 4 | [agent-4-risk-classifier.md](./agent-4-risk-classifier.md) | [Risk Classifier](../../../agent-templates/risk-classifier/) | Read the same transcript for sentiment + escalation risk. |
| 5 | [agent-5-feedback-loop-learner.md](./agent-5-feedback-loop-learner.md) | [Feedback Loop Learner](../../../agent-templates/feedback-loop-learner/) | Diff draft vs sent → imperative rule. Injected back into Agent 2. |
| 6 | [agent-6-weekly-rollup-writer.md](./agent-6-weekly-rollup-writer.md) | rollup writer (different cadence) | Generate the weekly status report from 14 days of accumulated context. |

---

## How to read these

If you're studying the **patterns**, start at [/agent-templates/](../../../agent-templates/). Each template links to its Followloop instance as a reference implementation.

If you're studying the **deployment**, start at the [Followloop case study](../README.md), then come here for the prompt-level detail.

If you're trying to **port a pattern** to your own deployment: read the template first to understand the abstract shape, then read the corresponding Followloop prompt to see what concrete prompt-engineering choices were made and why.

---

## What's portable, what's not

The structure of each prompt is portable; the content is not. Specifically:

- **Portable:** the schema shapes, the prompt-block layout (system vs. user, cached vs. volatile), the design rules (no-prose extractor, quote-grounded signals, verb-imperative lessons).
- **Situated:** trigger phrases, meeting-type enums, channel-specific formatting (Slack mrkdwn, the FleetPanda template), the 14-day rollup window.
- **Untransferable:** the PM's writing voice, the customer-relationship calibration, the lessons accumulated against this specific user.

Don't copy these prompts into your own deployment. Use the templates and write prompts grounded in your own domain.
