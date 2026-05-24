# Risk Classifier

> **The pattern:** read a source artifact (transcript, ticket, message, log) and emit a structured risk/sentiment assessment — an enumerated risk level, quote-grounded signals, and a short narrative read. The optimization target is the **opposite** of summarization: preserve and amplify signal, don't neutralize it.

This pattern is what turns a stack of per-artifact reads into a portfolio-level view that ranks subjects by risk and recency.

---

## What problem this solves

Summarizers and generators have an instinct to **neutralize** emotional or signal-heavy content. "Customer sounded frustrated about the timeline" becomes "follow up on the timeline" — a tidy action item with the actual signal scrubbed off.

For risk and sentiment work, that instinct is exactly wrong. You want the verbatim quote, the urgency word, the unresolved-from-last-time pattern, the trust-broken signal. A risk classifier is built to do the opposite of summarization.

It must be a separate agent. A combined prompt produces:

- **Sentiment leaks into summary** — the customer-facing email turns passive-aggressive
- **Summarizer instinct dominates risk read** — the risk output gets sanitized into action items, missing the actual escalation language

Same artifact, opposite jobs, two agents.

---

## Where this pattern shows up

| Domain | Source | Risk dimensions |
| --- | --- | --- |
| Customer success | Meeting transcript / support thread | Churn risk, escalation signal, trust erosion |
| Support ops | Inbound ticket / chat | Severity, urgency, customer-loss likelihood |
| Sales | Discovery / negotiation call | Deal risk, competitor threat, timeline slippage |
| Compliance / Trust & Safety | User content, account activity | Policy violation likelihood, harm severity |
| Code review | PR diff + discussion | Production risk, breaking-change probability |
| Incident response | On-call alerts, postmortems | Incident severity, recurrence risk |
| Healthcare ops | Clinical notes / patient messages | Triage urgency, deterioration signals |

---

## Input / output contract

**Input:** the raw source artifact + minimal metadata (subject ID, artifact type, optional prior-context snapshot).

**Output:** structured JSON with an enumerated risk level, quote-grounded signals, and a 1–2 sentence narrative read.

```json
{
  "risk_level": "high | medium | low | healthy",
  "signals": [
    "specific quote or observation that drove the assessment",
    "..."
  ],
  "summary": "1-2 sentences describing the dynamics and key drivers"
}
```

The exact enum values vary by domain (4 levels for customer health, 3 for ticket severity, binary for moderation queues). The shape — **enum + quote-grounded signals + narrative summary** — is portable.

---

## Why quote-grounding is non-negotiable

The most common failure mode for sentiment/risk models is **confident hallucination of mood**. The model decides a subject is at risk without specific evidence and writes a coherent justification.

The structural fix: the schema **requires** `signals` to be specific quotes or observations from the source. This:

- Forces the assessment to be evidence-grounded
- Gives a human reviewer a 5-second way to validate the call
- Surfaces the actual phrase that mattered, which is often more useful than the risk label

---

## Recall > precision

For risk/escalation detection, **false negatives are far more expensive** than false positives.

- **False positive:** a 2-minute review by the human reviewer
- **False negative:** the situation arrives from above with no warning, the team is caught flat-footed, the patience window is already gone

Tune the prompt to bias toward catching:

- Enumerate trigger phrases explicitly in the prompt (the language people actually use when they're frustrated, urgent, or signaling escalation)
- Define risk levels by **observable behavior**, not by feeling. ("`high` = subject is signaling escalation," not "`high` = very upset")
- Include a `medium` level for "friction without explicit escalation" so the model has a place for ambiguous cases instead of forcing them down to `low`

A typical well-tuned classifier publishes high recall (target: 100% on the cases that actually escalate) at the cost of moderate precision (60–75%). That tradeoff is correct for this class of agent.

---

## Defensive normalization

If the model returns a value outside the enum, the calling code should coerce to the **lowest-risk class** rather than retry. A miscategorized-low row is a recoverable miss on the next read; a parse failure that drops the row entirely takes the subject out of the cross-subject risk view.

---

## When the classifier feeds a portfolio view

The structured output is most valuable when it **accumulates across artifacts** and feeds a cross-cutting view ("rank all my subjects by risk-level and recency").

Make sure the output shape supports cross-row aggregation:

- Enumerated risk levels (rankable)
- Timestamps (recency)
- Subject IDs (joins to the entity table)
- Signals as queryable strings (text search, audit trail)

This is the differentiated use case for the pattern — a single per-artifact flag is incremental; a sorted portfolio view is a category change.

---

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Confident calls with no evidence | `signals` not required by schema | Make `signals` required, non-empty |
| Everything classified as `low` | Risk levels defined by feeling, not behavior | Redefine in observable terms, list trigger phrases |
| Inconsistent classifications across runs | No anchoring on prior subject history | Inject prior risk reads for the same subject |
| Outputs are unrankable | Free-text risk levels | Convert to enum |
| Parse errors drop subjects from the view | No defensive normalization in calling code | Coerce out-of-enum values to lowest risk, log the anomaly |

---

## Reference implementations

- **Followloop Agent 4** (B2B SaaS implementation work) — reads meeting transcripts for customer-health signals, feeds an Escalation Radar that ranks all active customers by risk and recency. Published metrics: ~70% precision, 100% recall over 38 meetings. See [/case-studies/followloop/prompts/agent-4-risk-classifier.md](../../case-studies/followloop/prompts/agent-4-risk-classifier.md).

If you build another deployment using this pattern, link it here.
