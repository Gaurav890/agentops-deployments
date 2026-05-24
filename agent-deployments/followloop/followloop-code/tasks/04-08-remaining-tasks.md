# Task 04 — Onboarding UI

## Goal
PM self-serve setup: sign in → grant Google access → add Slack ID. Three-step flow.

## Done when
- [ ] All 3 steps render correctly with right state (done/active/locked)
- [ ] Step 2 button triggers Google OAuth for Gmail + Calendar scopes
- [ ] Slack user ID saves to `pms.slack_user_id`
- [ ] Completing all steps redirects to training page

## Reference
`docs/frontend.md` → Onboarding page section

## Notes
- Step 1 is auto-complete (they signed in to get here)
- Step 2 re-uses the OAuth flow from Task 02 but requesting the additional API scopes
- Step 3 is a simple text input save
- Do not set `onboarding_complete = true` here — that happens after style samples added (Task 05)

---

# Task 05 — Style Training UI

## Goal
PM adds past emails as style samples. Agent uses them as few-shot examples. Live preview shows how Claude will write.

## Done when
- [ ] PM can add, view, and delete style samples
- [ ] Sample count shows progress toward 10
- [ ] "Preview" button calls `/api/style-preview` and shows Claude output
- [ ] When sample count ≥ 3, `onboarding_complete` set to TRUE
- [ ] "Setup complete — you're live" banner appears

## Reference
`docs/frontend.md` → Training page section
`docs/prompt-design.md` → Style preview section

## Notes
- Preview uses hardcoded sample transcript in `generator.py`
- Re-run preview automatically when a sample is added or deleted
- Sample cards should show: meeting type badge + first 80 chars of email body

---

# Task 06 — Draft History UI

## Goal
PM sees all agent drafts, their status, and can review transcripts and diffs.

## Done when
- [ ] Draft list shows all drafts for PM, newest first
- [ ] Status badges correct: Sent as-is / Sent with edits / In Gmail / Not sent
- [ ] "Transcript" expands inline
- [ ] "Draft" expands inline
- [ ] "View diff" shows for edited drafts
- [ ] Top stats: drafts this week, % sent without edits, time saved

## Reference
`docs/frontend.md` → History page section

## Notes
- Load last 50 drafts, no pagination for MVP
- Time saved estimate: count of sent drafts × 17 minutes
- Diff view: simple line-by-line comparison, no need for a library — just highlight removed lines red, added lines green

---

# Task 07 — Edit detection + feedback loop

## Goal
Detect when a PM edited the agent draft before sending. Store the diff. Surface it in history UI.

## Done when
- [ ] Background job runs ~30 min after each draft creation
- [ ] Compares agent_draft to what was actually sent
- [ ] `was_edited` and `edit_diff` populated in `draft_history`
- [ ] History UI shows "Sent with edits" badge for edited drafts

## How edit detection works
1. After draft is created, store `gmail_draft_id` in `draft_history`
2. Background job (run via APScheduler or a simple cron): for each draft with `status = pending` older than 20 min:
   - Query Gmail SENT folder for messages in last 2 hours
   - Match by approximate timing + subject line prefix (`[client_name] — Meeting Summary`)
   - If found: compare body to `agent_draft`, compute diff, update record
   - If not found after 48hrs: set `status = discarded`

## Notes
- This is best-effort — Gmail API doesn't have a direct "was this draft sent" endpoint
- Matching by subject prefix + timing window is reliable enough for MVP
- `edit_diff` format: `{"removed": ["line1", "line2"], "added": ["line1", "line2"]}` — simple enough to render in UI

---

# Task 08 — Production hardening

## Goal
Ready for full 10-PM team rollout.

## Done when
- [ ] Error alerting: Slack message to #eng-alerts on any pipeline failure
- [ ] Token refresh works reliably (test with expired token)
- [ ] Rate limiting on webhook endpoint (max 10 req/min per IP)
- [ ] Railway deployment working with env vars set
- [ ] Vercel deployment working
- [ ] All 10 PMs can complete onboarding independently
- [ ] End-to-end test with real Avoma meeting

## Notes
- Add `try/except` around every external API call with specific error messages
- Log pipeline steps to console with timestamps (not a full logging framework, just structured print statements for now)
- Test token expiry by manually setting `token_expiry` to a past time in DB
