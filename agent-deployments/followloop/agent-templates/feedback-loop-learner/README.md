# Feedback Loop Learner

> **The pattern:** watch what a user changes about the agent's output before they ship it, diff the agent's draft against the shipped version, and extract a generalizable rule from the diff. The pattern that turns a static LLM tool into a system that *learns from real usage* — without ever asking the user "rate this output."

The differentiated capability behind any agent that gets better the longer it runs.

---

## What problem this solves

Most LLM-powered tools are static after deployment. The user fixes the same kind of error every week, the system never learns, and the user's friction tax never goes down.

The naive "fix" — explicit feedback UI ("rate this output 1–5", "mark this draft as good/bad") — fails for a different reason: it adds friction. Users who are busy stop rating. Within a week, the feedback signal is gone.

The pattern that works leverages the signal the user is **already producing**: their natural edit-before-shipping behavior. If you can detect what they sent, you can diff it against what you generated, and extract a rule. No friction added.

The improvement is asymmetric to user effort: the user edits once, the rule applies to every subsequent draft forever.

---

## Where this pattern shows up

| Domain | Agent draft | "Shipped" version | Detection mechanism |
| --- | --- | --- | --- |
| Email follow-up | Generated email draft | Email actually sent | Match against Sent folder by subject + window |
| Code generation | Generated PR description | Final PR description on merge | GitHub API on PR merge |
| Doc generation | Generated runbook entry | Saved version after edits | Doc-store webhook / version diff |
| Internal updates | Generated Slack post | Posted message | Slack API search in target channel |
| Support replies | Suggested macro reply | Agent-sent reply | Helpdesk integration (Zendesk, Intercom) |
| Content moderation | Suggested action | Reviewer's final action | Audit log diff |

The mechanism varies; the pattern is the same — find the user's natural shipping channel, match by subject/timing, diff, learn.

---

## Mechanism (background loop, not synchronous)

```
┌──────────────────────────────────────────────────────────────┐
│  Generation pipeline produces a draft → marked `pending`     │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │ User edits + ships   │
                │ (or ships as-is)     │
                └──────────┬───────────┘
                           │
                           ▼
   ┌─────────────────────────────────────────────────┐
   │ Cron loop (typical: every 30 min):              │
   │ 1. Find `pending` drafts older than ~20 min     │
   │ 2. Match against the channel where user shipped │
   │ 3. Diff agent_draft vs. shipped_text            │
   │ 4. If was_edited & diff non-empty:              │
   │    → invoke this learner, get back a rule       │
   │ 5. Persist rule, deduplicate                    │
   │ 6. Future generations include the rule          │
   └─────────────────────────────────────────────────┘
```

Three operational rules learned the hard way:

- **Lag the check (15–30 min).** Users often draft, leave for a meeting, edit, and ship. Checking too eagerly produces false `was_edited=False` rows.
- **TTL the `pending` queue (24–48h).** Users sometimes don't ship at all. Without a TTL the queue grows unbounded.
- **Match conservatively.** Tighter timing windows miss real ships; looser ones cross-match the wrong drafts. Tune to your channel's noise.

---

## Diff → rule schema

```json
{
  "issue_type": "missing_info | wrong_tone | poor_organization | incorrect_detail | too_long | too_short | other",
  "severity": "minor | moderate | significant",
  "description": "one sentence: what was wrong with the draft",
  "rule": "one actionable instruction starting with a verb"
}
```

### The verb requirement is the load-bearing constraint

Without it, the model returns rules like:

> "the email was a bit too formal"

That's a description of the past, not a rule for the future. It can't be appended to a system prompt because it doesn't tell the next draft what to do differently.

With the verb requirement enforced, you get:

> "Open with the recipient's first name and reference a specific topic from the source artifact, never a generic 'Hi [Name], thanks for the meeting!' opener."

That **is** a rule. It can be appended verbatim to the generator's system prompt and applied immediately.

### Severity is for prioritization, not filtering

Collect `severity`, but inject all rules into the generator regardless. Severity is useful for the user-facing review surface ("show me this week's significant rules") and for future deduplication priority — not for runtime filtering, where any rule is better than the absence of one.

---

## Deduplication approach

Rules accumulate quickly. After ~50 drafts the same correction surfaces multiple times in different language.

### Easy: string-equality dedup with normalization

Lowercase, strip punctuation, dedupe on equality. Works because models tend to produce stable phrasings for the same correction. Good enough until you hit ~100+ rules.

### Robust: embedding-based semantic dedup

Embed each new rule, compare against the existing pool, drop if cosine similarity > threshold. More expensive, more reliable at scale. Switch when the easy approach starts admitting near-duplicates.

### Don't truncate by recency

The earliest rules tend to be the most foundational ("never use 'I hope this email finds you well'"). Truncate them and the agent regresses to the model's default voice.

---

## Why a learner loop, not a fine-tune

You could imagine training the generator on (draft, shipped) pairs and skipping the rule layer. Don't, for three reasons:

| Property | Rule loop | Fine-tune |
| --- | --- | --- |
| **Latency to improvement** | Next draft | After a training run |
| **Interpretability** | Human-readable rule | Black-box weight update |
| **Reversibility** | Delete one row | Re-train |

The cheapest, most legible feedback mechanism wins.

---

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Same correction surfaces repeatedly | Dedup too strict / not running | Lower the similarity threshold or add normalization |
| Rules feel descriptive, not actionable | Verb-form not enforced in prompt | Tighten the prompt; reject outputs without an imperative verb |
| Fewer rules captured than expected | Edit-detection match is missing real ships | Investigate the matching window and channel-specific quirks (signature drift, reply chains) |
| Rule injection blows up the system prompt | Too many rules, no dedup | Switch to embedding-based dedup |
| Generator ignores rules over time | Model's instruction-following degrades on long prompts | Move rules higher in the prompt; group by category |

---

## Reference implementations

- **Followloop Agent 5** (B2B SaaS implementation work) — runs every 30 minutes, matches generated email drafts against the user's Sent folder, extracts imperative-form lessons from each diff, injects them into the email generator's system prompt for all future drafts. See [/case-studies/followloop/prompts/agent-5-feedback-loop-learner.md](../../case-studies/followloop/prompts/agent-5-feedback-loop-learner.md).

If you build another deployment using this pattern, link it here.
