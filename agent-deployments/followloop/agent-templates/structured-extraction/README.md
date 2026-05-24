# Structured Extraction

> **The pattern:** turn unstructured input (a document, transcript, ticket, email, log) into a typed JSON object that downstream agents and tools can consume reliably. The agent **never writes prose** — its only job is to parse.

This is the most generally-applicable pattern in agent design. If your pipeline has more than one downstream stage, you almost certainly want a structured-extraction agent at the front.

---

## What problem this solves

Real-world inputs are messy: meeting transcripts, support tickets, customer emails, sensor logs, PDFs, chat threads. Downstream automation needs typed fields: an enum for category, a list of action items with owners, a date, a sentiment score.

Asking one agent to do both the parsing *and* generate a final output (an email, a summary, a decision) collapses two jobs that have different optimization targets:

- **Parsing** wants exactness, schema conformance, no embellishment
- **Generation** wants narrative flow, voice, register matching

When one prompt does both, errors in parsing get laundered into plausible-sounding prose, and the user can't tell which stage went wrong.

A structured-extraction agent splits parsing into its own stage, with its own contract.

---

## Where this pattern shows up

| Domain | Input | Structured output |
| --- | --- | --- |
| Customer success | Meeting transcript | `meeting_type`, `client_action_items[]`, `internal_action_items[]`, `next_steps` |
| Support ops | Inbound ticket | `severity`, `category`, `affected_features[]`, `customer_intent` |
| Sales | Discovery call transcript | `pain_points[]`, `competitors_mentioned[]`, `budget_signal`, `next_step` |
| Content moderation | User-generated post | `policy_categories[]`, `confidence`, `excerpt_quotes[]` |
| Code review | PR diff + description | `risk_level`, `affected_subsystems[]`, `breaking_change`, `migration_required` |
| Healthcare ops | Patient intake form | `chief_complaint`, `severity_indicators[]`, `triage_category` |

The shape generalizes; only the field names change.

---

## When to use this pattern

Use a structured-extraction agent when **any of these are true**:

- Two or more downstream agents/tools consume the same source artifact
- Downstream logic branches on a categorical field
- The source artifact is long enough that re-parsing it for every downstream call is expensive
- You need typed fields a database, scheduler, dashboard, or API can ingest directly

Do **not** add this stage when:

- The pipeline is one-shot ("artifact in → final output out") with no downstream consumers
- The output is naturally prose for a human reader and won't be programmatically consumed

Adding a stage just to add a stage is overhead.

---

## Input / output contract

**Input:** the raw artifact + minimal metadata to disambiguate parsing (author, source, timestamp).

**Output:** a single JSON object conforming to a fixed schema. Categorical fields use **enums**, never free text.

```json
{
  "subject_id": "primary subject of the artifact",
  "artifact_type": "<enum value from a fixed set>",
  "summary": "1-3 sentence neutral description",
  "items_for_them": [
    {"action": "...", "owner": "...", "due_date": "ISO date or null"}
  ],
  "items_for_us": [
    {"action": "...", "owner": "...", "due_date": "ISO date or null"}
  ],
  "open_questions": ["..."],
  "next_step": "string"
}
```

Keep nullable fields explicit (`"due_date": null`, not omitted). Downstream code stops branching on missing keys.

---

## Why this stage must be isolated

Three reasons, all learned from production deployments.

### 1. Errors compound silently downstream

A parsing mistake in a combined parse-and-generate prompt produces beautiful output built on a wrong foundation. The user can't tell whether the failure was "wrong owner extracted" or "wrong tone generated." A separate extraction stage with a strict schema makes parsing failures **loud** (JSON parse error, schema violation) instead of **silent** (wrong content embedded in plausible output).

### 2. Different jobs corrupt each other when combined

Tightening the action-item format makes the prose stilted. Adding "match my voice" makes structured fields drift. The combined prompt grows long enough that instruction-following degrades on both ends. Splitting fixes both.

### 3. Caching economics

A short, stable extraction prompt and a long, stable generation prompt are both prompt-cache candidates — but only as separate calls. A combined prompt that includes the per-call artifact in the cached portion invalidates the cache on every call.

---

## Implementation guidance

- **Use structured outputs / tool use.** `response_format=json_schema` (or your model's tool-use equivalent) is more reliable than "return ONLY JSON." Use both: schema as a hard constraint, prompt instruction as a soft one.
- **Defensive markdown stripping.** Even with structured output enforced, strip ```` ```json ... ``` ```` fences before parsing. Cheap belt-and-braces.
- **Categorical fields → enums with an `"other"` escape hatch.** Forcing the model to pick from a fixed set without an out produces confidently wrong classifications.
- **No downstream concerns in the prompt.** The extractor doesn't need to know that a downstream agent exists. Keep its job narrow.
- **Log every input and output.** When something goes wrong six weeks from now, you will need this.

---

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Schema violations on edge cases | Free-text categorical field, no enum | Convert to enum + `"other"` |
| Confident misclassifications | Enum has no escape hatch | Add `"other"` and a low-confidence fallback in code |
| Drift toward prose | Prompt allows narrative output | Tighten with structured-output enforcement, not just instructions |
| Combinatorial JSON shapes | Optional fields silently omitted | Require all fields, mark missing as `null` explicitly |

---

## Reference implementations

- **Followloop Agent 1** (B2B SaaS implementation work) — parses meeting transcripts into a fixed schema that fans out to four downstream agents. See [/case-studies/followloop/prompts/agent-1-structured-extractor.md](../../case-studies/followloop/prompts/agent-1-structured-extractor.md).

If you build another deployment using this pattern, link it here.
