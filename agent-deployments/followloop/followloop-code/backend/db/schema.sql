-- FleetPanda Meeting Summary Agent
-- Run this in Supabase SQL editor to initialize the schema.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- PM user accounts
CREATE TABLE IF NOT EXISTS pms (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    google_sub          TEXT UNIQUE,
    slack_user_id       TEXT,
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- OAuth tokens — one row per PM, refresh token encrypted at rest
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pm_id         UUID NOT NULL REFERENCES pms(id) ON DELETE CASCADE,
    access_token  TEXT NOT NULL,
    refresh_token TEXT NOT NULL,  -- Fernet encrypted
    token_expiry  TIMESTAMPTZ NOT NULL,
    scopes        TEXT[] NOT NULL DEFAULT '{}',
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS oauth_tokens_pm_id_idx ON oauth_tokens(pm_id);

-- Style samples — past emails pasted in by PM during onboarding
CREATE TABLE IF NOT EXISTS style_samples (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pm_id        UUID NOT NULL REFERENCES pms(id) ON DELETE CASCADE,
    meeting_type TEXT NOT NULL CHECK (meeting_type IN (
        'onboarding', 'weekly_sync', 'qbr', 'kickoff', 'escalation', 'other'
    )),
    email_body   TEXT NOT NULL,
    client_name  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Draft history — every draft the agent generates
CREATE TABLE IF NOT EXISTS draft_history (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pm_id              UUID NOT NULL REFERENCES pms(id),
    avoma_meeting_id   TEXT NOT NULL,
    client_name        TEXT,
    meeting_type       TEXT,
    meeting_date       TIMESTAMPTZ,
    transcript         TEXT,
    agent_draft        TEXT,
    sent_draft         TEXT,
    gmail_draft_id     TEXT,
    status             TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'sent', 'discarded'
    )),
    was_edited         BOOLEAN,
    edit_diff          JSONB,
    slack_notified_at  TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Client contact book
CREATE TABLE IF NOT EXISTS clients (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pm_id      UUID NOT NULL REFERENCES pms(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    company    TEXT,
    UNIQUE (email, pm_id)
);

-- Sessions table for Flask session tokens
CREATE TABLE IF NOT EXISTS sessions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pm_id      UUID NOT NULL REFERENCES pms(id) ON DELETE CASCADE,
    token      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);
