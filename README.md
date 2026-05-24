# AgentOps

I design and deploy AI agents into real enterprise workflows. This repo documents what I build, what I learn, and what actually works in production.

---

## The thesis

Most AI projects fail not because the model was wrong. They fail because nobody understood the workflow they were replacing.

AgentOps is my methodology for going into a real organization, mapping the operational surface, identifying the highest-leverage AI automation opportunity, and shipping a working agent — measurably fast. The focus isn't model capability. It's the gap between model capability and real-world deployment.

This is not a demo repo. Every deployment here is running in a real environment, against real workflows, with real users.

---

## Deployments

| System | Domain | Status |
| --- | --- | --- |
| [Followloop](./agent-deployments/followloop/) | B2B SaaS implementation work — autonomous meeting follow-up, escalation analysis, weekly reports | Live ✅ |

---

## Methodology

AgentOps is a five-stage process — **Audit → Identify → Build → Deploy → Measure** — for going from a real organizational workflow to a deployed AI agent that measurably saves time. Each stage is named for what blocks most projects there: not knowing what to automate, scoping too broad, collapsing two agents into one, shipping without a trigger, declaring success without a baseline.

Every deployment in this repo carries its own *worked* version of the methodology — the same five stages, documented as they played out in that specific workflow. Each case study includes:

- A **methodology writeup** — how the five stages were applied
- A **system-design playbook** — the multi-agent design decisions made during Build
- A **pre-build audit** — the Stage-1 audit that scoped v1
- Architecture, evaluation, and the **portable / situated / untransferable** breakdown

The portable layer — what's reusable across deployments — is what makes each one a *case study* rather than a *demo*. See [Followloop](./agent-deployments/followloop/) for a full worked example.

---

## About

Gaurav Chaulagain — AI Solutions & Enterprise Deployment Strategist, San Francisco.

- Forward Deployed PM, TPM - B2B SaaS
- Winner, "Best Use of Claude" — Cal Hacks 12.0 (3,300+ participants)
- MS Computer Science (ML, Systems), San Francisco Bay University
- Anthropic MCP credential, Building with the Claude API

[LinkedIn](https://linkedin.com/in/gaurav-chaulagain) · [Medium](https://medium.com/@gauravchaulagain)