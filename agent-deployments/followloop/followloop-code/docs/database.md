# Database Schema

Supabase (Postgres). All queries go through `backend/db/models.py`. No raw SQL anywhere else.

## Tables

### `pms`
PM user accounts.
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto |
| email | TEXT UNIQUE | their FleetPanda email, matches Avoma host_email |
| name | TEXT | display name |
| google_sub | TEXT UNIQUE | Google user ID from OAuth |
| slack_user_id | TEXT | for DM notifications |
| onboarding_complete | BOOLEAN | default FALSE — agent skips PMs where this is FALSE |
| created_at | TIMESTAMPTZ | auto |

### `oauth_tokens`
One row per PM. Refresh token encrypted at rest.
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto |
| pm_id | UUID FK → pms | cascade delete |
| access_token | TEXT | short-lived, refresh when expired |
| refresh_token | TEXT | **Fernet encrypted** before insert |
| token_expiry | TIMESTAMPTZ | check before using access_token |
| scopes | TEXT[] | ['gmail.compose', 'calendar.readonly'] |
| updated_at | TIMESTAMPTZ | update on every token refresh |

### `style_samples`
Email samples PMs paste in during onboarding. Used as few-shot examples for Claude.
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto |
| pm_id | UUID FK → pms | cascade delete |
| meeting_type | TEXT | onboarding / weekly_sync / qbr / kickoff / escalation / other |
| email_body | TEXT | raw email text, plain text only |
| client_name | TEXT | optional label |
| created_at | TIMESTAMPTZ | auto |

Target: 5–10 samples per PM. Minimum 3 before onboarding_complete can be set TRUE.

### `draft_history`
Every draft the agent generates. Stores both agent output and what PM actually sent (for learning).
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto |
| pm_id | UUID FK → pms | |
| avoma_meeting_id | TEXT | from webhook payload |
| client_name | TEXT | extracted from transcript |
| meeting_type | TEXT | extracted |
| meeting_date | TIMESTAMPTZ | from Avoma metadata |
| transcript | TEXT | full Avoma transcript, stored for audit |
| agent_draft | TEXT | exactly what Claude generated |
| sent_draft | TEXT | what PM actually sent (populated later by background job) |
| gmail_draft_id | TEXT | Gmail API draft ID |
| status | TEXT | pending / sent / discarded |
| was_edited | BOOLEAN | TRUE if sent_draft != agent_draft |
| edit_diff | JSONB | structured diff for future prompt improvement |
| slack_notified_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | auto |

### `clients`
Client contact book. Populated from Calendar + manual entry.
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto |
| pm_id | UUID FK → pms | which PM owns this client |
| name | TEXT | |
| email | TEXT | |
| company | TEXT | |
| UNIQUE | (email, pm_id) | one record per client per PM |

## Key queries needed in `models.py`
- `get_pm_by_email(email)` — used by webhook to find PM from Avoma host_email
- `get_pm_by_id(pm_id)`
- `get_oauth_token(pm_id)` — returns encrypted token record
- `update_oauth_token(pm_id, access_token, expiry)`
- `get_style_samples(pm_id, meeting_type, limit)` — filter by type first, fall back to any
- `save_draft(...)` — insert into draft_history
- `update_draft_status(draft_id, status, sent_draft)` — called when PM sends
- `get_draft_history(pm_id, limit)` — for history page
