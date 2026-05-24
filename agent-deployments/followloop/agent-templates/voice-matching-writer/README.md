# Voice-Matching Writer

> **The pattern:** generate written output (email, message, summary, post, doc) in a *specific person's voice* by anchoring the prompt on real examples that person has produced — not on adjectives describing their style.

The hardest agent class to ship well, and the one where most LLM tools fall flat. Voice-matching is the difference between output a user can press send on and output they always have to rewrite.

---

## What problem this solves

The naive approach — instructing the model with adjectives ("warm but professional", "concise but not curt", "match my writing style") — produces generic LLM output. Style-instructions don't generalize: a million different writers fit any given description.

The pattern that works is **few-shot anchoring on real artifacts**: show the model 3–5 things the user actually wrote, segmented by the right context, and the model imitates concrete patterns rather than guessing at adjectives.

---

## Where this pattern shows up

| Domain | What's being generated | Examples to anchor on |
| --- | --- | --- |
| Customer-facing email | Follow-up after a meeting | Prior emails the user sent, segmented by meeting type |
| Internal comms | Slack updates, status notes | Prior updates the user posted in the same channel |
| Sales outreach | Cold/warm outreach drafts | Prior successful outreach this rep wrote |
| Code generation | PR descriptions, commit messages | Prior PRs/commits by the same author |
| Documentation | API doc pages, runbook entries | Prior docs by the same author or team |
| Marketing | Social posts, newsletter copy | Prior posts by the same brand voice |

---

## Input / output contract

**Inputs (a five-block prompt):**

| Block | Why it's needed |
| --- | --- |
| **Structured context** (from an upstream extraction agent) | Action items, decisions, summary in typed form — not raw source artifact |
| **Style examples** — 3–5 prior artifacts the user wrote, filtered to the same subtype | The single biggest quality lever |
| **Prior interaction history** | What was already committed in writing to this counterparty |
| **Accumulated style rules** (from a feedback-loop learner) | Imperative-form rules from past corrections |
| **Adjacent channel context** (e.g. email thread between meetings) | Prevents the agent from re-asking for things already resolved elsewhere |

**Output:** the artifact itself, no metadata, no commentary — just the email/message/post.

---

## Style examples > style instructions

The single most important rule in this pattern. Three sub-rules:

### Quantity: 3–5 examples

- Fewer than 3 → the model picks up idiosyncrasies of one example
- More than ~7 → the signal dilutes and tokens get expensive

### Recency: prefer recent

Voice drifts. Examples from two years ago calibrate the model to a person the user no longer is.

### Subtype matching: filter by context

Don't show onboarding emails to the model when generating a quarterly review email. Use a categorical field from the upstream extraction agent to filter the example pool to the same subtype.

---

## Prompt-cache strategy

Voice-matching writers are the agent class that benefits most from prompt caching, because:

- The system prompt is **long** (style rules + 3–5 examples + accumulated rules + prior history can easily exceed 20K tokens)
- The system prompt is **stable** across calls for the same user
- Per-call context (the new structured input) is small relative to the cached portion

```
[CACHED PORTION]                    [NOT CACHED]
─────────────────────────────────   ─────────────────────────────────
- style boilerplate                 - this call's structured context
- accumulated style rules           - this call's source artifact (in user msg)
- pinned style examples             - adjacent channel context (volatile)
- (optional) prior history block
```

Two practical rules:

- **Stable content first.** Putting volatile content above stable content invalidates the cache on every call.
- **Mark the boundary deliberately.** Most APIs let you flag the cache checkpoint. Place it where content actually transitions from stable to volatile.

For an agent firing more than a few times within the cache TTL, prompt caching pays for itself within a couple of days.

---

## Style-rule injection (the feedback loop)

A separate **feedback-loop learner** agent watches what the user edits before sending and emits imperative-form rules:

> "Always include the next-meeting date when one was scheduled."
>
> "Never use the phrase 'I hope this email finds you well'."
>
> "When the customer mentions a blocker, summarize their understanding of the resolution rather than the technical fix."

These get appended verbatim into a `STYLE RULES YOU'VE LEARNED FROM PAST EDITS` block in the system prompt.

Two important properties of well-formed rules:

- **Imperative form, starting with a verb.** A description ("the email was too formal") is not a rule — it can't be applied. Enforce verb-shape upstream in the learner.
- **Inject all rules, not just recent ones.** The accumulated rule set *is* the user's voice profile. Truncating to "last 10" loses the foundational ones. Deduplicate, don't truncate.

See [/agent-templates/feedback-loop-learner](../feedback-loop-learner/) for the upstream pattern.

---

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Generic openers, robotic register | Style instructions instead of examples | Add 3–5 real prior artifacts |
| Drifts to model's default voice | Examples too generic / too few / not subtype-filtered | Tighten the example pool |
| Repeats info already covered elsewhere | Missing adjacent-channel context block | Inject the email thread / chat history |
| Re-makes commitments already made | Missing prior-history block | Inject prior artifacts as ground truth |
| Rules don't seem to apply | Rules are descriptive, not imperative | Re-prompt the learner with verb-shaped output requirement |
| Output drifts month-over-month | Style rules being truncated | Switch to dedup, not truncation |
| Costs climb fast | No prompt caching on the stable portion | Mark cache checkpoint, reorder so stable content is first |

---

## Reference implementations

- **Followloop Agent 2** (B2B SaaS implementation work) — generates customer-facing follow-up emails after meetings, anchored on the PM's prior emails segmented by meeting type, with five injected blocks (style rules, learned rules, prior meetings, email thread since last meeting, style examples). See [/case-studies/followloop/prompts/agent-2-customer-email-writer.md](../../case-studies/followloop/prompts/agent-2-customer-email-writer.md).

If you build another deployment using this pattern, link it here.
