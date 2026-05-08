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
| [Followloop](./case-studies/followloop/) | B2B SaaS implementation work — autonomous meeting follow-up, escalation analysis, weekly reports | Live ✅ |

---

## Methodology

Each deployment is documented as a case study with:

- **Architecture** — what was built, why each component exists, what fails if you collapse them
- **Evaluation** — real metrics from production, with the methodology behind every number
- **What's portable, situated, untransferable** — distinguishing the parts that generalize from the parts that depend on the specific workflow

The portable layer is what makes a deployment a *case study* rather than a *demo*.
---

## About

Gaurav Chaulagain — AI Solutions & Enterprise Deployment Strategist, San Francisco.

- Forward Deployed PM, TPM - B2B SaaS
- Winner, "Best Use of Claude" — Cal Hacks 12.0 (3,300+ participants)
- MS Computer Science (ML, Systems), San Francisco Bay University
- Anthropic MCP credential, Building with the Claude API

[LinkedIn](https://linkedin.com/in/gaurav-chaulagain) · [Medium](https://medium.com/@gauravchaulagain)