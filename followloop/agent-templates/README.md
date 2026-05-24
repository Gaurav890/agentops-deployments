# Agent Templates

Generic agent patterns extracted from real production deployments. Each template documents an architectural pattern that recurs across domains — what problem it solves, when to use it, the input/output contract, and the failure modes that surface in practice.

These are **patterns, not code**. The prompts and JSON schemas vary by domain; the shape and the design rules don't.

---

## The four patterns

| # | Pattern | One-line description | When you need it |
| --- | --- | --- | --- |
| 1 | [Structured Extraction](./structured-extraction/) | Turn unstructured input into typed JSON. Never writes prose. | You have one source artifact feeding two or more downstream agents/tools |
| 2 | [Voice-Matching Writer](./voice-matching-writer/) | Generate written output in a specific user's voice using few-shot anchoring on real artifacts they've produced. | You need outputs that someone is willing to ship as-is, in their own voice |
| 3 | [Risk Classifier](./risk-classifier/) | Read a source artifact and emit a structured risk/sentiment assessment with quote-grounded signals. | You need to surface signal across a portfolio (rank subjects by risk and recency) |
| 4 | [Feedback Loop Learner](./feedback-loop-learner/) | Watch what the user changes before shipping, diff against the agent's draft, extract a generalizable rule. | You want the system to improve from real usage without a "rate this output" UI |

---

## How they compose

A typical multi-agent pipeline that uses three or four of these looks like:

```
                        ┌────────────────────────┐
                        │  Source artifact       │
                        │  (transcript, ticket,  │
                        │   email, log, …)       │
                        └────────────┬───────────┘
                                     │
                                     ▼
                       ┌─────────────────────────┐
                       │  STRUCTURED EXTRACTION  │ ← always at the front
                       │  → typed JSON context   │   when there's fan-out
                       └────┬─────────┬──────────┘
                            │         │
              ┌─────────────┘         └────────────────┐
              ▼                                        ▼
   ┌──────────────────────┐               ┌──────────────────────┐
   │ VOICE-MATCHING       │               │ RISK CLASSIFIER      │
   │ WRITER               │               │ → structured risk    │
   │ → user-shippable     │               │   per artifact       │
   │   output             │               │ → portfolio view     │
   └──────────┬───────────┘               └──────────────────────┘
              │
              │  draft
              ▼
   ┌──────────────────────┐
   │ User edits + ships   │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │ FEEDBACK LOOP LEARNER (background, async)│
   │ diff(draft, shipped) → imperative rule   │
   └──────────┬───────────────────────────────┘
              │
              └──── rules injected back into voice-matching writer
```

Three composition rules:

1. **Structured Extraction goes first** when there's fan-out. It's the load-bearing stage that makes parallelism cheap.
2. **The Risk Classifier is a sibling, not a child, of the writer.** Same input artifact, different optimization target, different output shape. Don't try to derive risk from the writer's output.
3. **The Feedback Loop Learner is async and out-of-band.** It runs on a cron, not inline. Adding synchronous feedback ("approve before send") destroys the friction-free property that makes this pattern work.

---

## Decision guide

**Should this be one agent or multiple?**

Start with one. Split when:

- You see fan-out (one input, multiple consumers) — add a Structured Extraction stage at the front
- Two responsibilities have **opposite optimization targets** (e.g. summarize-and-neutralize vs. preserve-and-amplify) — split into a generator and a Risk Classifier
- Two responsibilities have **different cadences** (per-artifact vs. weekly rollup) — different agent, different prompt
- You can't tell which stage is failing when the output is wrong — split until you can localize the bug

The full decision guide lives in [/architecture/](../architecture/).

**Which template applies to my use case?**

Walk down this list:

1. Do you have one input feeding two or more downstream consumers? → start with **Structured Extraction**.
2. Are you generating something a real human ships in their own voice? → use **Voice-Matching Writer**.
3. Are you trying to detect problems / risk / sentiment across a portfolio? → use **Risk Classifier**.
4. Does your agent ship the same kind of mistake repeatedly? → add a **Feedback Loop Learner** to absorb corrections.

You can use any subset. Most production deployments use 2–4 of them.

---

## What's NOT in this folder

- **Implementation code.** These are pattern documents. The prompts and integration code live in case studies (e.g. [Followloop](../case-studies/followloop/)).
- **Domain-specific prompts.** The `voice-matching-writer` template documents the pattern abstractly. The actual prompt for "follow-up emails for a B2B implementation PM" is a Followloop artifact, not a template.
- **Patterns that aren't proven yet.** Every template here is grounded in at least one production deployment. Speculative patterns belong in `/architecture/` until they have a case study to back them up.

---

## Contributing a new template

A pattern earns a template when:

- It has been deployed in production for at least one real workflow
- The deployment has a written case study in `/case-studies/`
- The pattern has a clear input/output contract and at least 2–3 concrete failure modes documented from experience

Patterns that exist only in theory don't go here. They go in `/architecture/`.
