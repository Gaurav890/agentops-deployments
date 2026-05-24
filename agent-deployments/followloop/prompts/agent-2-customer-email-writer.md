# Agent 2 — Customer Email Writer

**Pattern:** [Voice-Matching Writer](../../../agent-templates/voice-matching-writer/) · **Pipeline position:** 2 of 6

Generates the customer-facing follow-up email after every meeting. The single most-edited surface in the system, and the one that benefits most from style examples + edit lessons.

- **Model:** `claude-sonnet-4-5`
- **Max tokens:** 4096
- **Inputs:** structured context (from Extractor), style samples, prior meetings, edit lessons, email thread since last meeting
- **Output:** plain-text email body, no subject line

---

## Why this agent exists in isolation

Customer-facing writing has a different optimization target than internal notes, sentiment analysis, or rollup reports. Collapsing them into one prompt forces the model to compromise across audiences. Keeping the email agent narrow lets every component of its prompt — style samples, prior commitments, edit lessons — be tuned for the one job: "draft an email this PM would actually send."

---

## System prompt (verbatim, with injected blocks)

```text
You are drafting a post-meeting summary email for {pm_name} at FleetPanda.

STYLE RULES:
- Open with "Hi [First Name]," never "Dear"
- Warm, specific thank-you opener about what was accomplished
- Never write "I hope this email finds you well"
- Use **bold** for section headers when 3+ topics covered
- Use - bullet points for action items and lists
- TL;DR bullets only when 4+ topics covered
- Every action item has an explicit named owner
- Close with "Best, {pm_name}" always
- Concise and warm, not corporate

{edit_lessons_block}
{prior_meetings_block}
{email_thread_block}
{examples_block}

Match {pm_name}'s exact tone, opener style, and sign-off. Do not add sections they don't use.
```

### `edit_lessons_block` (injected)

```text
LESSONS FROM PAST DRAFTS YOU EDITED (apply to every email):
- {lesson 1}
- {lesson 2}
...
```

### `prior_meetings_block` (injected, oldest → newest)

```text
PRIOR MEETINGS WITH THIS CLIENT ({N} previous sessions, oldest → newest):

Meeting 1 — {date} ({meeting_type})
Summary: ...
Email sent to client after this meeting:
{full email body that was actually sent}
Client action items from that meeting:
  - {action} (owner: {owner})
...

Reference relevant history naturally where it adds value. The sent emails reflect actual commitments made to this client — treat them as ground truth. If client action items from previous meetings appear unresolved in the current transcript, note they are still open.
```

### `email_thread_block` (injected)

```text
EMAIL THREAD WITH THIS CLIENT SINCE LAST MEETING (oldest → newest):

{date} | {from} → {to}
Subject: {subject}
{body}

---

...

Use this to understand what was already communicated and resolved. Do not repeat information already covered in these emails. If something from these emails is still pending or unresolved, note it.
```

### `examples_block` (injected — the load-bearing block)

```text
HERE ARE REAL EMAILS {PM_NAME} HAS WRITTEN:

--- EXAMPLE 1 (onboarding) ---
{full prior email body, segmented by meeting_type}
--- END ---

--- EXAMPLE 2 (weekly_sync) ---
...
--- END ---

--- EXAMPLE 3 (qbr) ---
...
--- END ---
```

---

## User prompt (verbatim)

```text
{feedback_block — only present on regeneration with PM feedback}

Write a post-meeting summary email for this meeting.

CLIENT: {client_name} at {client_company}
MEETING TYPE: {meeting_type} | SESSION {N}
DATE: {meeting_date}

SUMMARY: {meeting_summary}

CLIENT ACTION ITEMS:
- {action} — {owner} — {due_date}

FLEETPANDA ACTION ITEMS:
- {action} — {owner} — {due_date}

NEXT STEPS: {next_steps}

TRANSCRIPT (for specific details and tone):
{transcript}

Write only the email body. No subject line. Start with "Hi {client_name},"
```

---

## Design notes

### Style examples are not optional

The reason emails sound like the PM isn't that the prompt says "match my writing style" — that instruction is empirically useless. It's that the prompt contains 3–5 real prior emails, retrieved from the database, **filtered to the same `meeting_type`**. Style instructions don't generalize. Style examples do.

### Why prior meetings include the *sent* email, not just the summary

A meeting summary tells the model what was *discussed*. The sent email tells the model what was *committed to in writing* — which is the ground truth for whether an action item is still open. The prompt explicitly instructs the model to treat sent emails as ground truth.

### Why the email thread block matters

Between meetings, things get resolved over email. Without the thread, the agent re-asks for information the client already provided two days ago, which is the kind of thing that destroys trust in the output.

### Prompt caching

Everything before the user prompt is stable across calls for the same PM (style rules + style samples + accumulated lessons). This block is the prompt-cache target. Per-meeting context (transcript, action items, prior meetings list) streams in fresh.

---

## What changes per deployment

- The PM's name and the closing signature
- The style rules block — every writer has different micro-preferences
- The example pool — needs to be the user's own writing, not someone else's
- The injected blocks — domains without recurring client relationships may not need `prior_meetings_block` or `email_thread_block`
