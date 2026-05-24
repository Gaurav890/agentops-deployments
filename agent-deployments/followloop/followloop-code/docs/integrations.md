# Integrations

## Avoma (API polling)

We poll the Avoma REST API every 5 minutes instead of receiving webhooks.
This removes the need for a publicly accessible endpoint during development.

**API reference:** https://dev.avoma.com  
**Base URL:** `https://api.avoma.com/v1/`  
**Auth:** `Authorization: Bearer {AVOMA_API_KEY}`  
**Rate limit:** 60 requests/minute  

**Setup:** Avoma app → Settings → Organization → Developer → Create API key → copy to `AVOMA_API_KEY` in `.env`. Requires admin privileges.

---

### Endpoints used

#### List transcriptions
```
GET /v1/transcriptions/
  ?from_date=<ISO 8601>
  &to_date=<ISO 8601>
  &page_size=50
```
Response:
```json
{
  "results": [
    {
      "uuid": "txn-uuid",
      "meeting_uuid": "meeting-uuid",
      "speakers": [
        {"name": "Sarah Chen", "email": "sarah@fleetpanda.com", "duration": 120},
        {"name": "Raj Patel",  "email": "raj@acmecorp.com",     "duration": 95}
      ],
      "transcript": [
        {"speaker": "Sarah Chen", "text": "Hi Raj...", "start_time": 0.0, "end_time": 4.2},
        {"speaker": "Raj Patel",  "text": "Hey Sarah!", "start_time": 4.5, "end_time": 7.1}
      ]
    }
  ]
}
```

#### Get meeting details
```
GET /v1/meetings/{meeting_uuid}/
```
Response fields used: `subject` (or `title`), `start_time` (or `startTime`).

---

### How the poller works (`jobs/avoma_poller.py`)

1. Runs every 5 minutes in a background thread (started at app boot)
2. Fetches transcriptions completed in the last poll window
3. Deduplicates against `draft_history.avoma_meeting_id` — skips already-processed meetings
4. Identifies the FleetPanda host from `speakers[].email` (first `@fleetpanda.com` email)
5. Converts transcript array to plain text (`"Speaker: text\n\n..."`)
6. Runs through the full agent pipeline (extract → generate → Gmail draft → Slack DM)
7. Stores `last_poll` timestamp in `backend/jobs/.avoma_last_poll` (persists across restarts)

---

## Gmail API (outbound)

**Purpose:** Create email drafts in the PM's personal inbox.

**Scope:** `https://www.googleapis.com/auth/gmail.compose` — creates drafts only. Cannot read inbox. This scope does NOT require Google verification for internal/test users.

**What we do:**
- `users.drafts.create` — create a new draft pre-addressed to client
- `users.messages.list` (SENT label) — background job to detect if PM edited before sending

**One credentials object per PM.** Never share credentials between PMs.

**Setup:** Google Cloud Console → Enable Gmail API → OAuth consent screen → add scope → create OAuth 2.0 Web credentials → add redirect URI.

---

## Google Calendar API (outbound)

**Purpose:** Pull attendee email addresses from calendar events to pre-address drafts accurately.

**Scope:** `https://www.googleapis.com/auth/calendar.readonly`

**What we do:**
- `events.list` — find the calendar event matching the Avoma meeting time
- Extract `attendees[].email` — used to identify client email when transcript parsing is ambiguous

**This is a fallback.** Primary client detection is from transcript + Avoma attendee list. Calendar is only queried when that fails.

---

## Google OAuth 2.0 (auth)

**Flow:** Authorization Code Flow with refresh tokens.

**Scopes requested in one consent screen:**
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/calendar.readonly`
- `openid`, `email`, `profile`

**Token storage:**
- Access token: stored plaintext (short-lived, ~1hr)
- Refresh token: **must be Fernet-encrypted** before writing to DB
- On expiry: call Google token endpoint with refresh token, update access token in DB

**Redirect URI:** `https://yourapp.com/auth/callback` — must match exactly in Google Console.

---

## Slack API (outbound)

**Purpose:** DM the PM when their Gmail draft is ready.

**Method:** `chat.postMessage` with block kit (message + button linking to Gmail drafts).

**Finding PM's Slack ID:** During onboarding, call `users.lookupByEmail` with their work email. Store `slack_user_id` in `pms` table. This is what you pass as `channel` in `chat.postMessage`.

**Bot token scopes needed:**
- `chat:write` — send messages
- `users:read.email` — look up user by email

**Setup:** api.slack.com → Create app → Bot Token Scopes → Install to workspace → copy Bot User OAuth Token.

---

## Anthropic Claude API (outbound)

**Model:** `claude-sonnet-4-5` (do not change — update `CLAUDE.md` if you do)

**Two calls per meeting:**
1. `extractor.py` — parse transcript → structured JSON (context extraction)
2. `generator.py` — generate email with style samples as few-shot examples

**Approximate tokens per meeting:**
- Extraction: ~2,000 in / ~400 out
- Generation: ~3,000 in / ~600 out
- Total: ~6,000 tokens → ~$0.006 per email at Sonnet pricing

**Context window management:**
- Truncate transcript to 5,000 chars in generation prompt if longer
- Style samples: use 2-3 max, prioritize same meeting_type as current meeting

**Response format for extractor:**
Claude must return valid JSON only. Prompt must say "Return ONLY valid JSON, no markdown, no preamble." Strip any accidental code fences before `json.loads()`.
