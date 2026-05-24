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

Each deployment in this repo carries its own set of methodology artifacts — the same five-stage process is applied, but every deployment documents how it played out in that specific workflow. For Followloop those artifacts are:

- **[Methodology](./agent-deployments/followloop/methodology.md)** — the five-stage process (Audit → Identify → Build → Deploy → Measure) as it was applied to this workflow
- **[System-design playbook](./agent-deployments/followloop/system-design-playbook.md)** — the multi-agent design decisions made during Build, framed so the patterns transfer
- **[Pre-build audit](./agent-deployments/followloop/pre-build-audit.md)** — the 10-question Stage-1 audit that scoped v1
- **Architecture, evaluation, portable/situated/untransferable** — covered inside the deployment's [README](./agent-deployments/followloop/README.md)

The portable layer is what makes a deployment a *case study* rather than a *demo*.
---

## About

Gaurav Chaulagain — AI Solutions & Enterprise Deployment Strategist, San Francisco.

- Forward Deployed PM, TPM - B2B SaaS
- Winner, "Best Use of Claude" — Cal Hacks 12.0 (3,300+ participants)
- MS Computer Science (ML, Systems), San Francisco Bay University
- Anthropic MCP credential, Building with the Claude API

[LinkedIn](https://linkedin.com/in/gaurav-chaulagain) · [Medium](https://medium.com/@gauravchaulagain)