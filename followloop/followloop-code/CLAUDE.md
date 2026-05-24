# FleetPanda Meeting Summary Agent

## What this is
An autonomous agent that converts Avoma meeting transcripts into Gmail drafts in each PM's inbox, then pings them on Slack to review and send. Zero manual writing.

## Stack
- Backend: Python Flask on Railway
- Frontend: Next.js 14 on Vercel  
- Database: Supabase (Postgres)
- Auth: Google OAuth 2.0 (per-PM, not shared service account)
- AI: Anthropic Claude API (`claude-sonnet-4-5`)
- Email: Gmail API (compose scope only)
- Notifications: Slack Web API

## Repo structure
```
backend/      Flask app, webhook handler, agent logic, integrations
frontend/     Next.js app, PM dashboard, onboarding, style training
docs/         Architecture, schema, integration specs (read before coding)
tasks/        One file per buildable unit — work through these in order
sessions/     Auto-updated after each session — read latest before starting
```

## How to use this project
1. Read the latest file in `sessions/` to see where we left off
2. Read the current task file in `tasks/`
3. Reference `docs/` files for specs — do not invent structure
4. When session ends, run: update CLAUDE.md status + create a new session log in sessions/

---

## Current status
> **STATUS: LIVE — Avoma polling, Gmail drafts, Slack notifications, dashboard all working**
> Completed: Tasks 01–08 + runtime fixes + enhancements (history, escalation, tasks, weekly reports, sign-out)
> Last session: 2026-04-25 — weekly report email context (14-day meetings + Gmail auto-pull), gmail.readonly scope fix, sign-out button, report client_company OR fix
> Next session: Verify Sommers Oil report fix; confirm Gmail auto-pull in reports; consider Railway deploy
> Run backend: `cd backend && /path/to/.venv/bin/python app.py` (port 8080)
> Run frontend: `cd frontend && npm run dev` (port 3000)

---

## Key decisions (do not re-litigate)
- Per-PM OAuth tokens, not a shared service account
- Gmail scopes: `gmail.compose` (drafts) + `gmail.readonly` (read threads for report context) — both approved in Google Cloud Console
- Style samples stored as raw email text, Claude extracts style via few-shot
- Avoma integration: API polling every 5 min (not webhook) — no public endpoint needed
- Refresh tokens encrypted with Fernet before DB storage
- Model: `claude-sonnet-4-5` (do not change without updating this file)
- Gmail drafts sent as HTML (markdown → HTML via `markdown` lib), not plain text
- `pm_id` cookie is non-httpOnly (UUID only, not sensitive)
- Browser API calls go through Next.js rewrites (`next.config.mjs`) — no CORS needed
- Flask runs on port 8080 (set via `PORT` env var); venv is at project root `.venv/`
- Supabase `sb_secret_` key format requires supabase>=2.10 + websockets>=13 in venv

## What NOT to do
- Do not write code not in the active task file
- Do not add dependencies not listed in `docs/architecture.md`
- Do not store OAuth tokens unencrypted
- Do not read PM inbox — compose scope only
