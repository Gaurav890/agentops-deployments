# System Design Playbook

Cross-cutting design decisions that apply to **any** multi-agent LLM deployment, regardless of domain. This is the file you consult during the **Build** stage of [the methodology](../methodology/) when you hit one of the recurring "should I do X or Y?" forks.

It is not a tutorial. It is not specific to one product. Each section covers one decision, the rule of thumb, and the failure mode the rule prevents.

---

## What's in here vs. what's elsewhere

| If you're asking… | Look here |
| --- | --- |
| *"How do I find what to build?"* | [/methodology/](../methodology/) and [/audit-tool/](../audit-tool/) |
| *"What's a proven agent pattern for problem X?"* | [/agent-deployments/followloop/agent-templates/](../agent-deployments/followloop/agent-templates/) |
| *"How do I structure the **system** these agents live in?"* | **This file** |
| *"What does a real deployment look like?"* | [/agent-deployments/followloop/](../agent-deployments/followloop/) |

The agent-templates answer "what shape should each agent have." This file answers "how do those agents fit together, and how do you keep the system maintainable, debuggable, and cheap?"

---

## Decision 1 — One agent or several?

Default instinct: start with one. It's the right shape for a prototype. It's the wrong shape for anything that ships at quality.

### Split into multiple agents when any of these is true:

- **The output of one stage is the input of two or more downstream stages** (fan-out). Once you have fan-out, an extractor stage at the front pays for itself.
- **Two responsibilities have opposite optimization targets.** Summarization vs. sentiment analysis is the canonical example — one neutralizes emotional content, the other amplifies it.
- **Two responsibilities run on different cadences.** Per-event and per-period (per-meeting vs. per-week, per-ticket vs. per-day) need different prompts and different rollup logic.
- **You can't tell which stage is failing when the output is wrong.** If a single combined prompt produces a bad output and you can't localize the bug, that's the signal to split.
- **Your prompt has gotten long enough that instruction-following is degrading.** Models follow short prompts more reliably than long ones. When you're stacking instructions to fix one job and watching another regress, split.

### Stay with one agent when:

- You have a single artifact, a single output, and no fan-out
- The domain is small enough that the prompt fits in 1–2K tokens
- You're prototyping and don't yet know what the right split is

**Don't pre-split.** Prototypes that already have six agents on day one usually have the wrong six. Let the structure emerge from where one-prompt quality plateaus.

---

## Decision 2 — Where does each responsibility belong?

Once you've decided to split, the next question is where the boundaries go. The rule:

> **One agent, one job. The output of each is a typed input for the next. When something goes wrong, you can name the agent that failed.**

The "name the agent" clause is the operational version of the rule. If your error logs say "the system was wrong" instead of "the extractor mislabeled `category`," your separation of concerns is wrong.

| Decision | Single-agent default | Multi-agent default |
| --- | --- | --- |
| Output shape between stages | Free-form prose | Structured JSON |
| Logging | Single input/output pair | Per-agent input/output rows |
| Eval | "Was the output good?" | "Did each agent do its job?" |
| Iteration | Tweak the single prompt | Tweak the failing agent in isolation |

If two responsibilities keep wanting to share information that the JSON schema doesn't capture cleanly, that's a signal the split is wrong — not a signal to pass blobs of prose between stages.

---

## Decision 3 — Should I use prompt caching, and how?

Anthropic's prompt caching (and equivalent features in other vendors' APIs) makes long, stable system prompts economical. But cache layout is something you have to design.

### Use prompt caching when:

- Your system prompt is **>2K tokens** (cache breakeven is around 50–100 reuses for short prompts; larger prompts amortize faster)
- Your system prompt is **stable across calls** for the same user/customer/tenant
- You're calling the agent **at least a few times per cache TTL** (5 minutes for Anthropic at time of writing)
- You can cleanly separate stable from volatile content in the prompt

### Don't use it when:

- The prompt changes per call (e.g. transcript embedded in system prompt)
- Call volume is low enough that cache hits are rare (the cache write costs ~25% more than a normal write — you need reuse to break even)
- The "stable" portion is actually drifting (e.g. you're constantly adding lessons or examples that invalidate the cache)

### Cache layout discipline

The cache works in **prefix-matching** mode. The cached portion must be a literal prefix of the prompt. Two practical implications:

```
[CACHED PORTION]                   [NOT CACHED]
─────────────────────────────────  ─────────────────────────────────
- system prompt boilerplate        - this call's specific context
- pinned style examples            - this call's source artifact
- accumulated rules / lessons      - per-call user prompt
- (optional) prior history block   - any volatile metadata
```

- **Stable content goes first.** If you put the per-call artifact above the style examples, the cache invalidates on every call.
- **Order matters more than content.** Two calls with identical content but different field ordering are two different cache entries.
- **Cache breaks at the `cache_control` checkpoint.** Most APIs let you mark up to a few cacheable segments — use them where the content actually transitions from stable to volatile.

### Common mistake: caching everything

Marking the entire prompt cacheable when half of it changes per call is *worse than not caching*. You pay the write premium and never get a hit. Design the prompt around the cache boundary, not the other way around.

---

## Decision 4 — What do I log, and at what granularity?

Every multi-agent pipeline should log, **for each agent invocation**:

| Field | Why |
| --- | --- |
| `agent_name` | Which stage |
| `invocation_id` | Correlate stages of the same pipeline run |
| `input` (full) | Reproduce the call |
| `output` (full, raw) | Inspect what the model returned, including parse failures |
| `parsed_output` | The post-processing result the next stage actually consumed |
| `model`, `temperature`, `max_tokens` | Reproduce with the same config |
| `latency_ms` | Spot regressions |
| `cache_metrics` (read tokens, write tokens, hit %) | Validate caching is working |
| `created_at` | Time-ordered debugging |

This is more verbose than a typical request log. That's the point. When an output is wrong six weeks from now, you'll need to:

1. Find the pipeline run that produced it
2. Walk back through every agent's input and output
3. Localize which agent was wrong
4. Reproduce the bad output for prompt iteration

Without per-agent logs, step 3 is guesswork.

### What not to do

- **Don't only log the final user-facing output.** By the time it reaches the user, the bug is laundered through several stages and you can't tell which one introduced it.
- **Don't only log inputs.** Sometimes the model returns something that fails to parse — you need the raw output to diagnose.
- **Don't sample.** At pipeline scale, "1% of agent calls logged" is fine for metrics but useless for debugging the specific bad output the user complained about.

---

## Decision 5 — When do I introduce async?

Synchronous pipelines are simpler. Async (background loops, queue-driven workers) is harder to reason about. Reach for async when:

- A stage needs to **observe user behavior over time** (an edit-detection loop, a daily-rollup worker). It can't be inline because the user hasn't acted yet.
- A stage runs on a **different cadence** from the trigger (weekly reports off per-meeting events).
- A stage is **expensive enough** that blocking the user is unacceptable, and stale-by-a-minute is acceptable.

Stay synchronous when:

- The user is waiting on the output
- The cost of staleness is high
- You haven't built the operational tooling (queues, retries, dead-letter handling) needed to run async safely

The async stages most teams underestimate are queue management, idempotency, and TTLs. A `pending` queue with no TTL grows forever. A retry with no idempotency double-applies side effects. Build the tooling before you build the second async worker.

---

## Decision 6 — How do I evaluate this thing?

The universal failure mode: shipping with no eval, then having no way to tell whether the next prompt change made it better or worse.

### Three layers of eval

| Layer | What it measures | When to build it |
| --- | --- | --- |
| **Per-agent correctness** | Does each agent produce a valid output for its contract? (schema conformance, enum coverage) | Day one |
| **Per-pipeline outcome** | Is the user shipping the output as-is, or with edits? | Week one |
| **Outcome-level metric** | Is the user actually getting time/value back from the deployment? | Whenever you have a real baseline |

Most teams skip layer 2. Don't — it's the most useful one. Edit rate (how often the user changes the output before shipping) is a per-pipeline quality signal that comes for free if you instrument the channel. It's also the primary signal a [Feedback Loop Learner](../agent-deployments/followloop/agent-templates/feedback-loop-learner/) consumes.

### Build the boring instrumentation first

When you start, the temptation is to build a dashboard because it's visible — to the user, to stakeholders, to yourself. The thing you actually need in week two is per-agent input/output logs, prompt versioning, and trace correlation across stages.

Build the boring instrumentation first. The dashboard sits on top of it.

---

## Decision 7 — Operational visibility before user-facing visibility

Closely related to logging, but worth its own mention:

A multi-agent system has two kinds of UI surface — what the user sees (drafts, dashboards, notifications) and what the operator sees (logs, traces, prompt revisions, cache metrics). The user-facing surface is the visible one. The operator-facing surface is the load-bearing one.

Build the operator surface first. You will be debugging this system long before any external user gives you usable feedback.

---

## Where these decisions came from

Every decision in this file is grounded in production deployments — usually multiple. Specific incidents and tradeoffs are documented in the relevant case study's "What I got wrong" section. The decisions live here because they're **not** specific to any one workflow.

If you make one of these decisions differently in your own deployment and learn something the playbook doesn't capture yet, that's a candidate for a new section here — back it with the case study that justifies it.
