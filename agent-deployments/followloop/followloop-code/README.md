# Customer Operations Agent

Turns meeting transcripts into Gmail drafts, automatically. Polls Avoma for new transcriptions, extracts action items, flags escalation risk, generates a follow-up email in the PM's writing style, and pings them on Slack to review and send.

## Stack

- **Backend** — Python / Flask
- **Frontend** — Next.js 14
- **Database** — Supabase (Postgres)
- **AI** — Anthropic Claude API
- **Auth** — Google OAuth 2.0 (per-user)
- **Integrations** — Gmail API, Slack Web API, Avoma API

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project
- Google Cloud project with Gmail API enabled and OAuth credentials
- Anthropic API key
- Slack app with `chat:write` and `users:read` scopes
- Avoma API key

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd summary-agent

python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && npm install
```

### 2. Environment variables

**Backend** — create `.env` in the project root:

```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
AVOMA_API_KEY=
FLASK_SECRET_KEY=
```

**Frontend** — copy and fill in `frontend/.env.local.example` → `frontend/.env.local`

### 3. Database

Run `backend/db/schema.sql` in your Supabase SQL editor to create the tables.

### 4. Run locally

```bash
# Backend (port 8080)
cd backend && ../.venv/bin/python app.py

# Frontend (port 3000)
cd frontend && npm run dev
```

## How it works

1. Avoma is polled every 5 minutes for new transcriptions
2. Each new meeting runs through a 4-step Claude pipeline: extract context → generate email → analyze escalation → generate internal Slack note
3. A Gmail draft is created in the PM's inbox and they are pinged on Slack to review and send
4. When the PM sends the email, edits are detected and a lesson is extracted to improve future drafts

## Deploy

- **Backend** — Railway (`Procfile` included, set env vars in Railway dashboard)
- **Frontend** — Vercel (connect repo, set env vars in Vercel dashboard)
