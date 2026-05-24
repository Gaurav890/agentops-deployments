# The AgentOps Methodology

A repeatable process for going from a real organizational workflow to a deployed AI agent that measurably saves time. This is the playbook behind every case study in this repo.

---

## The thesis

Most AI projects fail not because the model was wrong, but because nobody mapped the workflow they were replacing. AgentOps inverts the usual order: instead of starting with a model capability and looking for a use case, you start with the operational surface of a real team and find the highest-leverage automation it can absorb. The agent comes last. What comes first is *understanding the work*.

---

## The five stages

### 1. Audit

Map the operational surface before writing a line of code. Catalog the recurring meetings, the per-meeting overhead, the documents produced, the channels where decisions land, the tools already in the loop. Time the work. The goal is to find the **highest-leverage hour** — the recurring task that costs the most time and has the cleanest input/output boundary.

Heuristics that help:
- Anything that happens **on every meeting / ticket / customer / week** is a candidate
- Anything where the input is a single document and the output is a single document is a strong candidate
- Anything that requires institutional voice (writing style, escalation judgment) is hard but high-value when it works

The audit tool in [/audit-tool](../audit-tool/) is a 10-question structured version of this stage.

### 2. Identify

Pick **one** workflow. Resist the urge to ship a platform. The first deployment should be narrow enough that a single person can use it daily within two weeks.

Three filters:
- **Frequency** — does it happen at least 5x/week?
- **Boundary clarity** — is the input/output well-defined?
- **Edit-tolerance** — can the user review-and-correct, or does it have to be perfect first try?

Edit-tolerant workflows are dramatically easier to ship than fire-and-forget ones. Start there.

### 3. Build

The build phase has two non-obvious rules:

**One agent, one job.** If you can describe the agent's purpose with the word "and" ("parse the transcript *and* write the email"), it's two agents. The Followloop case study spells out the cost of collapsing this — every fix to one job broke another.

**Style examples > style instructions.** "Match my writing style" is a useless instruction to any model. Five real artifacts the user produced are useful. Build the prompt around examples, not adjectives.

Other build defaults:
- Structured outputs (JSON schemas, tool use) wherever the next stage consumes the output
- Prompt caching on stable system-prompt context from day one
- Per-agent input/output logs from day one (you will need them in week two)

### 4. Deploy

Deployment is where most projects quietly die. Two failure modes:

- **Manual review friction**: any flow that requires the user to "rate the output" or "approve before send" decays the moment they're busy. Prefer **edit-detect** patterns where the system watches the user's natural workflow and infers feedback from it.
- **Trigger drift**: if the agent runs only when manually invoked, usage drops to zero. Wire it to events that already happen (webhook, cron, inbox arrival).

Ship the narrowest possible v1 to one user (often: yourself). Daily use is the only honest test.

### 5. Measure

Numbers without methodology aren't real metrics. For every published number, document:

- **What was measured** (e.g. "edit rate per draft," not "quality")
- **The date range and sample size**
- **The baseline** (what was the cost before deployment?)
- **What you haven't measured yet** (the honest gaps)

The metrics that matter for an agent deployment:
- **Edit rate / verbatim-send rate** — fraction of outputs shipped without changes
- **Time recovered** — measured baseline minus measured post-deployment cost
- **Latency** — time from trigger to usable output
- **Recall on critical signals** — for risk/escalation agents, missed-flag rate is more important than precision

---

## Portable vs. situated vs. untransferable

Every deployment has three layers. Naming them is what makes a deployment a *case study* rather than a *demo*.

| Layer | What it is | Example (Followloop) |
| --- | --- | --- |
| **Portable** | Architecture and patterns that generalize across domains | Extractor-first pipeline; style examples > instructions; async edit-lesson loop; sentiment as a separate agent from summarization |
| **Situated** | Choices specific to this workflow but replaceable in another | Avoma/Gmail/Slack as channels; the meeting taxonomy (onboarding, weekly sync, QBR); the 14-day rollup window |
| **Untransferable** | Institutional knowledge baked in over time | The user's writing voice; the customer relationships that calibrate sentiment reads; what makes a "high-risk" flag actionable |

The portable layer is the architecture. The situated layer is the prompts. The untransferable layer is the lessons accumulated over time. When you read a case study, separate them in your head — the portable layer is what you can take to your own deployment.


If you're building a deployment of your own: read the audit tool, read one case study end-to-end, then pick the relevant agent templates. Don't read the templates first — context-free patterns are how people end up with platforms that nobody uses.
