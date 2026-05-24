# Pre-Build Audit

A structured 10-question worksheet you complete **before writing a single line of code** — to make sure the agent you're about to build is the one most worth building.

---

## What this is

A scope-discipline tool. It walks you through the operational surface of one team, identifies their recurring work, and uses a 6-axis leverage rubric to pick **one** workflow as the target for v1.

It is the practical artifact for the **Audit** stage of [the AgentOps methodology](../methodology/) — the stage where you map the work *before* you start building.

## When to use it

Use it **once per deployment**, before any prompt engineering or coding. Specifically:

- You're considering building an AI agent for your team or yourself
- You have several candidate use cases and need to pick one
- You suspect you're about to over-scope (build a "platform" instead of a tool)
- You need a defensible justification for *why this workflow and not another*

Don't use it for: post-deployment retros, ongoing roadmap planning, or scoping a v2 (those need different questions).

## What you get out of it

By the end of one focused hour, you'll have:

1. A map of your team's recurring meetings, artifacts, channels, and where institutional knowledge lives
2. **3 candidate workflows** with measured baselines (frequency, time-per-instance, weekly cost)
3. A **score (0–30)** for each candidate against the leverage rubric
4. **One chosen workflow** with a 3-sentence justification
5. A **falsifiable success criterion** for v1 — the number a skeptic could check after 4 weeks

That decision artifact feeds straight into the Build stage. Without it, you're guessing.

---

## How to use this document

1. Pick one team (yourself, your function, your direct reports) — not "the company."
2. Walk through the 10 questions in order. Write the answers down. Be specific — owners, time, frequency, artifact names.
3. Score each candidate workflow against the **leverage rubric** in question 8.
4. Pick **one** workflow with the highest score for v1. Defer the rest.

The single most common failure mode of an AgentOps initiative is starting with too broad a scope. The audit's job is to make scope discipline mechanical.

---

## Part 1 — Map the operational surface

### 1. What recurring meetings does this team run, and how often?

List every meeting that happens at a regular cadence. For each:

- Name / type
- Frequency (per week)
- Average duration
- Who runs it, who attends
- What artifact comes out (notes? email? ticket? nothing?)

> **Why this question:** recurring meetings are the densest source of structured automation opportunities. Anything that produces a per-meeting artifact is a candidate.

### 2. What artifacts does the team produce per week?

For each artifact, capture:

- Name (e.g. "weekly status report", "incident postmortem", "deal review note")
- Owner
- Cadence
- Approximate time-to-produce (be honest — time yourself if you don't know)
- Where it lives (email? Notion? Salesforce? a Slack channel?)

> **Why this question:** artifacts are the surface where AI output lands. If there's no recurring artifact, there's nowhere obvious for the agent's output to go.

### 3. What channels carry the team's work?

List the tools the team uses for: communication, documentation, tasks, customer-facing output, status reporting. Note which are read-only vs. write-capable from automation.

> **Why this question:** an agent that produces output the team can't easily consume is a science project. Channel constraints often dictate architecture.

### 4. Where does institutional knowledge live?

For each of the following, where is it stored (or "in someone's head")?

- Past customer conversations
- Past decisions and why they were made
- Style examples (writing, code, designs)
- Team-specific terminology / naming
- Customer-specific context (relationships, history, tone calibration)

> **Why this question:** the parts of a workflow that *feel* automatable but produce bad output usually fail because the institutional knowledge they need isn't accessible. If the answer is "in someone's head," that's a constraint to design around — or a reason to deprioritize.

---

## Part 2 — Cost the work

### 5. Pick three candidate workflows. For each, time the work.

For each candidate, fill in:

| Field | Example |
| --- | --- |
| Workflow name | Post-meeting follow-up email |
| Frequency | ~10 per week |
| Time per instance | 25 minutes |
| Total weekly cost | 4.2 hours |
| Inputs | Meeting transcript, prior context, style |
| Outputs | One email, sent to the customer |
| Edit-tolerant? | Yes — PM reviews before sending |
| Trigger | Meeting ends → transcript ready in Avoma |

If you don't know the per-instance time, **time yourself for one week before continuing**. Estimates are systematically wrong by 2x in either direction.

### 6. What's the baseline, in measurable units?

For each candidate, name the **one number** you'd improve. Pick something a stranger could verify.

- "Time spent writing follow-up emails per week, in minutes"
- "Number of escalations that surfaced from above with no warning"
- "Time-to-first-status-report after a quarter ends"

> **Why this question:** without a baseline number, you can't claim improvement after deployment. "Felt faster" doesn't survive contact with a skeptic.

### 7. What's the failure cost?

For each candidate:

- What's the cost of a wrong output that gets shipped? (e.g. "a customer gets a draft with a wrong action owner")
- What's the cost of a wrong output that gets caught? (usually: the user's review time)
- What's the cost of the system not running at all? (the user falls back to manual, no harm done)

> **Why this question:** the gap between "wrong-shipped" cost and "wrong-caught" cost determines whether you can use an edit-tolerant deployment or whether you need a pre-send gate. Edit-tolerant workflows are dramatically cheaper to ship. Strongly prefer them for v1.

---

## Part 3 — Pick the target

### 8. Score each candidate against the leverage rubric

Score 1–5 on each axis. Don't skip axes, even when it's obvious.

| Axis | 1 (avoid) | 5 (ideal) |
| --- | --- | --- |
| **Frequency** | Once a quarter | Multiple times per day |
| **Boundary clarity** | Inputs and outputs are vague | Single artifact in, single artifact out |
| **Edit tolerance** | Must be perfect first try | User reviews and edits before sending |
| **Time recovered per instance** | <5 min | >20 min |
| **Channel availability** | Tooling is read-only or non-existent | Existing API for both input and output |
| **Institutional knowledge accessibility** | Lives only in someone's head | Available as documents/logs/prior artifacts |

Total possible: 30. Anything below 18 is not a v1 candidate. Anything 22+ is a strong candidate.

### 9. Pick one. Justify the choice.

Write a 3-sentence justification:

- Which workflow you picked
- Why you picked it over the runner-up
- What you're explicitly choosing not to do, and when you'll revisit

If you can't justify it in 3 sentences, the audit isn't done.

### 10. Define the v1 success criterion in one line.

Examples:

- "Cut my weekly post-meeting follow-up time from 4 hours to <30 minutes within 4 weeks of deployment, measured against the same baseline window."
- "Surface every escalation-worthy customer ≥1 day before it reaches my manager, measured over 8 weeks of deployment."
- "Cut weekly status report turnaround from 3 hours to <30 minutes, with the customer accepting the report as-is on at least 80% of weeks."

The criterion must:

- Reference the baseline you defined in question 6
- Have a defined measurement window
- Be falsifiable (a skeptic could check it)

---

## Decision artifact

After completing the audit, you should have:

- A map of your team's operational surface
- 3 ranked candidate workflows with scores
- One chosen workflow with a justification
- A measurable v1 success criterion

That's the input to the **Identify** stage of the AgentOps methodology. From here, go to [/agent-deployments/followloop/agent-templates/](../agent-deployments/followloop/agent-templates/) and pick the patterns that match your chosen workflow.

---

## Anti-patterns this audit prevents

- **Starting with the model's capabilities.** "GPT-N can do X, what should we use it for?" is the wrong question. Start with the workflow.
- **Choosing the most visible workflow instead of the most leveraged one.** The most-visible one usually involves senior people, who are the slowest to adopt new tools. Pick a workflow you (or one trusted user) own end-to-end.
- **Building a platform before a use case.** A platform that supports many workflows is worth ~0 until *one* workflow is in daily use. Single-tenant first, multi-tenant later.
- **Skipping the baseline measurement.** You will not be able to prove value at the end if you didn't measure the start.
