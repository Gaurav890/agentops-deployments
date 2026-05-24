# Architecture

## System overview

```
Avoma (meeting ends)
  → webhook POST to Flask backend
  → background thread: extract context → build prompt → call Claude
  → Gmail API: create draft in PM's inbox
  → Slack API: DM the PM
  → PM opens Gmail → reviews → sends
```

## Backend structure
```
backend/
  app.py                  Entry point, routes, webhook signature verification
  webhook/
    avoma.py              Receives payload, spawns background thread
  agent/
    extractor.py          Pulls client name, meeting type, action items from transcript
    prompt_builder.py     Assembles system prompt with style samples + user prompt
    generator.py          Calls Claude API, returns email string
  integrations/
    gmail.py              Creates draft via Gmail API
    calendar.py           Reads attendee emails from Google Calendar
    slack.py              Sends DM notification
  auth/
    google_oauth.py       Token refresh logic, Fernet encryption/decryption
  db/
    models.py             All Supabase queries (no raw SQL in other files)
    schema.sql            Source of truth for DB structure
```

## Frontend structure
```
frontend/
  app/
    page.tsx                      Landing + login
    auth/callback/route.ts        Google OAuth callback handler
    dashboard/
      onboarding/page.tsx         3-step setup flow
      training/page.tsx           Style sample management + live preview
      history/page.tsx            Draft log, diffs, stats
  components/                     Reusable UI pieces
  lib/
    supabase.ts                   Supabase client
    api.ts                        All calls to Flask backend
```

## Data flow: transcript → draft

1. Avoma fires webhook with transcript JSON
2. Flask verifies HMAC signature, returns 200 immediately
3. Background thread starts:
   a. Look up PM by `host_email` in `pms` table
   b. If PM not found or onboarding incomplete → log and exit
   c. `extractor.py` calls Claude to parse transcript → structured context JSON
   d. `prompt_builder.py` fetches 2-3 style samples for that PM + meeting type
   e. `generator.py` calls Claude with system prompt (style) + user prompt (context)
   f. `gmail.py` creates draft in PM's Gmail inbox
   g. `models.py` saves record to `draft_history`
   h. `slack.py` DMs the PM

## Data flow: PM onboarding

1. PM visits app → clicks "Sign in with Google"
2. Frontend redirects to Google OAuth consent screen
3. PM grants `gmail.compose` + `calendar.readonly` scopes
4. Google redirects to `/auth/callback` with auth code
5. Backend exchanges code for access + refresh tokens
6. Refresh token encrypted with Fernet → stored in `oauth_tokens`
7. PM completes onboarding: adds Slack user ID, uploads style samples
8. `pms.onboarding_complete` set to TRUE → agent will now process their meetings

## Dependencies (approved list)
```
# Backend
flask==3.0.0
anthropic==0.40.0
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-api-python-client==2.118.0
supabase==2.3.0
slack-sdk==3.27.1
cryptography==42.0.2
python-dotenv==1.0.0
gunicorn==21.2.0

# Frontend
next@14
react@18
typescript
@supabase/supabase-js
```
Do not add dependencies without updating this file.

## Environment variables
See `.env.example` in repo root. Required before any backend task will run:
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`
- `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET`
- `AVOMA_WEBHOOK_SECRET`
- `TOKEN_ENCRYPTION_KEY` (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `FLASK_SECRET_KEY`
