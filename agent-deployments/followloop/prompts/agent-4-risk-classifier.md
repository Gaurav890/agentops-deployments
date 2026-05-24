# Agent 4 — Risk Classifier

**Pattern:** [Risk Classifier](../../../agent-templates/risk-classifier/) · **Pipeline position:** 4 of 6

Reads the same transcript as Agent 1 and Agent 2, but with a fundamentally different question: *how is this customer feeling, and should anyone be worried?*

- **Model:** `claude-sonnet-4-5`
- **Max tokens:** 1024
- **Output:** structured JSON (`risk_level`, `signals`, `sentiment_summary`)

---

## Why this agent exists in isolation

Sentiment analysis has the *opposite* optimization target from summarization.

- The summarizer wants to **neutralize** emotional content into action items ("client mentioned frustration with deploy timeline" → "follow up on deploy timeline").
- The escalation analyzer wants to **preserve and amplify** emotional signal — the verbatim quote, the urgency word, the unresolved-from-last-time pattern.

Same transcript, opposite jobs. Trying to do both in one prompt produces a model that does neither well — emails turn passive-aggressive when sentiment leaks in, and risk reads turn anodyne when the summarizer instinct dominates.

---

## Prompt (verbatim)

```text
You are analyzing a meeting transcript to assess customer health and escalation risk.

Client: {client_company or client_name}
Meeting type: {meeting_type}

Transcript:
{transcript}

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
{
  "risk_level": "high|medium|low|healthy",
  "signals": ["specific quote or observation that drove the assessment", "..."],
  "sentiment_summary": "1-2 sentences describing customer mood and key dynamics"
}

If the transcript is too short or unclear to assess, return risk_level "low" with an appropriate summary.
```

---

## Design notes

### Enumerated, not free-text, risk levels

Free-text risk levels ("kind of concerning?", "moderately worried") are unrankable. The enum is what makes the downstream Escalation Radar view possible — every customer in the portfolio gets sorted by `risk_level` and recency.

### `signals` is required to be quote-shaped

The most common failure mode for sentiment models is **confident hallucination of mood**. Forcing `signals` to be specific quotes or observations grounds the assessment in the transcript and gives a reviewer a 5-second way to validate the call.

### Defensive normalization

If the model returns a `risk_level` outside the enum, the calling code coerces it to `"low"` rather than retrying. False low is recoverable on the next meeting; a parse failure that drops the entire row is not.

### `signals` and `sentiment_summary` are what flow into the weekly report

The Escalation Analyzer's output isn't just a per-meeting flag — it accumulates across meetings and surfaces in the rolled-up status report. Without a separate sentiment agent, the weekly report has no honest read of customer health.

---

## Recall > precision

The 70% precision and 100% recall numbers reported in the case study are deliberate. False positives cost a 2-minute review by the PM. False negatives mean an escalation arrived from above with no warning. The prompt is tuned (by listing trigger phrases explicitly) to bias toward catching, not classifying.

---

## What changes per deployment

- The trigger-phrase list (your customers complain in different vocabulary)
- The risk-level taxonomy (some teams want a 3-level scale, some want 5)
- The "Look for:" bullets generally — domain-specific signals belong here
