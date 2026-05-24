# Frontend Pages

Next.js 14 App Router. Deployed on Vercel.

All API calls to Flask backend go through `lib/api.ts`. Never call Flask directly from components.

---

## Routes

| Route | File | Purpose |
|---|---|---|
| `/` | `app/page.tsx` | Landing page with "Sign in with Google" button |
| `/auth/callback` | `app/auth/callback/route.ts` | Google OAuth callback, sets session cookie, redirects |
| `/dashboard` | `app/dashboard/page.tsx` | Redirect to onboarding if incomplete, else history |
| `/dashboard/onboarding` | `app/dashboard/onboarding/page.tsx` | 3-step setup flow |
| `/dashboard/training` | `app/dashboard/training/page.tsx` | Style sample management |
| `/dashboard/history` | `app/dashboard/history/page.tsx` | Draft history, stats, diffs |

---

## Page: `/dashboard/onboarding`

**Purpose:** Guide PM through 3 required setup steps. Show progress. Block step 3 until step 2 complete.

**Step 1 — Sign in with Google**
- Auto-marked done if they reached this page (they signed in to get here)
- Shows their email address as confirmation

**Step 2 — Grant Gmail + Calendar access**
- Button: "Connect Google account" → redirects to Google OAuth consent
- Scopes to request: `gmail.compose`, `calendar.readonly`
- After grant: show green checkmark, unlock step 3
- Display permission explanation: "Draft only — we cannot read your inbox"

**Step 3 — Add Slack user ID**
- Text input for Slack member ID (format: U0XXXXXXX)
- Where to find it: "In Slack → click your name → Profile → More → Copy member ID"
- Save button → POST to `/api/onboarding/slack`

**Completion:** When all 3 steps done → button "Go to style training" → redirect to `/dashboard/training`. Sets `onboarding_complete = true` only after minimum 3 style samples added (enforced on training page).

---

## Page: `/dashboard/training`

**Purpose:** PM uploads past emails so Claude learns their style.

**Left panel — sample list:**
- Show all existing samples as cards: meeting type badge + first 80 chars of email
- Delete button on each card
- Sample count: "6 samples added (target: 5–10)"
- Progress bar toward 10

**Right panel — add new sample:**
- `<textarea>` — paste raw email text
- Meeting type selector: onboarding / weekly sync / QBR / kickoff / escalation / other
- Optional client name label
- "Save sample" button → POST to `/api/samples`

**Bottom — style preview:**
- Button: "Preview how my emails will look"
- Calls `POST /api/style-preview` with pm_id
- Shows Claude's output in a read-only text block
- Label: "Based on your samples, drafts will look like this"
- Re-runs every time a sample is added/deleted

**Completion gate:**
- If sample count ≥ 3 AND Slack ID set: show "Setup complete — you're live" banner
- Sets `onboarding_complete = true`

---

## Page: `/dashboard/history`

**Purpose:** PM sees all agent-generated drafts, their status, and can review transcripts.

**Top stats row (4 cards):**
- Drafts this week
- Sent without edits (count + %)
- Time saved estimate (drafts × 17 min)
- Total drafts all time

**Draft list:**
Each row shows:
- Client name + meeting type
- Date + time
- Status badge: "Sent as-is" (green) / "Sent with edits" (amber) / "In Gmail" (gray) / "Not sent" (red)
- Two buttons: "Transcript" (expand inline) / "Draft" (expand inline)
- If `was_edited = true`: third button "View diff" (side-by-side comparison)

**Filters:**
- Date range
- Status
- Client name search

**No pagination needed for MVP** — load last 50 drafts.

---

## Auth pattern

Session stored in httpOnly cookie set at `/auth/callback`.

All dashboard pages:
1. Check cookie server-side in layout
2. If no cookie → redirect to `/`
3. Pass `pm_id` from session to all API calls

Do not store pm_id in localStorage or client state.

---

## API calls from frontend (`lib/api.ts`)

```
GET  /api/samples?pm_id=          → list PM's style samples
POST /api/samples                  → add sample { pm_id, meeting_type, email_body }
DEL  /api/samples/:id              → delete sample
POST /api/style-preview            → { pm_id } → { draft: string }
POST /api/onboarding/slack         → { pm_id, slack_user_id }
GET  /api/history?pm_id=           → list draft history
GET  /api/history/:id/transcript   → full transcript for one draft
```
