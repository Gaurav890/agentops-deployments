# Task 02 — Google OAuth flow

## Goal
PM clicks "Sign in with Google" → grants Gmail + Calendar scopes → tokens stored encrypted in Supabase → session cookie set → redirected to dashboard.

## Done when
- [ ] PM can complete full OAuth flow in browser
- [ ] Refresh token stored encrypted in `oauth_tokens` table
- [ ] `pms` record created on first login
- [ ] Session cookie set, persists across page refreshes
- [ ] `/dashboard` redirects to `/` if no valid session

## Reference
- `docs/integrations.md` → Google OAuth section
- `docs/database.md` → `pms` and `oauth_tokens` tables
- `docs/architecture.md` → data flow: PM onboarding

## Steps

### 1. Google Cloud Console setup (manual — do first)
1. Create project
2. Enable: Gmail API, Google Calendar API, Google People API
3. OAuth consent screen → External → add scopes:
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `openid`, `email`, `profile`
4. Add test users (each PM's email)
5. Create OAuth 2.0 Web credentials
6. Authorized redirect URI: `http://localhost:3000/auth/callback` (dev) + production URL
7. Copy client ID and secret to `.env`

### 2. Backend: token exchange endpoint
`POST /auth/google/exchange` — receives auth code from frontend, exchanges for tokens, stores in DB, returns session token.

Logic:
- Exchange code with Google
- Upsert `pms` record (create if new, update google_sub if exists)
- Encrypt refresh token with Fernet
- Upsert `oauth_tokens` record
- Generate a session token (UUID or JWT) → store in a `sessions` table or signed cookie
- Return `{ pm_id, session_token }`

### 3. Frontend: OAuth initiation
`app/api/auth/google/route.ts` — builds Google OAuth URL with correct scopes and redirects.

URL parameters:
- `client_id`: from env
- `redirect_uri`: `/auth/callback`
- `scope`: gmail.compose + calendar.readonly + openid + email + profile
- `access_type`: offline (to get refresh token)
- `prompt`: consent (force refresh token on every grant)
- `response_type`: code

### 4. Frontend: OAuth callback
`app/auth/callback/route.ts`:
- Get `code` from query params
- POST to Flask `/auth/google/exchange`
- Set httpOnly session cookie with returned session token
- Redirect to `/dashboard/onboarding`

### 5. Frontend: auth middleware
`middleware.ts` at root:
- Check session cookie on all `/dashboard/*` routes
- If missing → redirect to `/`

## Out of scope
- Onboarding steps 2 and 3 (Slack ID, style samples) — those are Task 05
- Token refresh logic — that's in `auth/google_oauth.py`, implement in Task 03

## Test
1. Start both `flask run` and `npm run dev`
2. Click "Sign in with Google" on landing page
3. Complete Google consent screen
4. Verify redirect to `/dashboard/onboarding`
5. Check Supabase: `pms` table has new row, `oauth_tokens` has encrypted refresh token
6. Verify refresh token is NOT plaintext (should be a Fernet-encoded string starting with `gAAAAA`)
