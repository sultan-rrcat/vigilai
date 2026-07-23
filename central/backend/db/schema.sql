-- Users
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'operator', -- admin / operator
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Cameras / edge nodes
CREATE TABLE IF NOT EXISTS cameras (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    location        TEXT,
    rtsp_url        TEXT,
    status          TEXT DEFAULT 'offline', -- online / offline
    last_heartbeat  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Restricted zones (polygons) per camera
CREATE TABLE IF NOT EXISTS zones (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id         UUID REFERENCES cameras(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    polygon           JSONB NOT NULL,      -- [[x,y], [x,y], ...] in normalized coords
    min_dwell_seconds NUMERIC DEFAULT 2.0,
    active_schedule   JSONB,               -- optional time-of-day activation windows
    enabled           BOOLEAN DEFAULT true,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Tripwires (directional line segments) per camera
CREATE TABLE IF NOT EXISTS tripwires (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id          UUID REFERENCES cameras(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    line                JSONB NOT NULL,     -- [P1,P2] normalized coords, order defines direction
    watched_direction   TEXT NOT NULL,      -- "a_to_b" | "b_to_a" | "both"
    enabled             BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Confirmed incidents
CREATE TABLE IF NOT EXISTS incidents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id         UUID REFERENCES cameras(id),
    track_id          TEXT NOT NULL,
    object_class      TEXT NOT NULL,       -- person / vehicle
    trigger_type      TEXT NOT NULL,       -- zone_dwell / line_crossing
    zone_id           UUID REFERENCES zones(id),
    tripwire_id       UUID REFERENCES tripwires(id),
    snapshot_path     TEXT,
    confidence        NUMERIC,
    status            TEXT DEFAULT 'active', -- active / acknowledged / escalated / resolved
    acknowledged_by   UUID REFERENCES users(id),
    acknowledged_at   TIMESTAMPTZ,
    resolved_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Escalation audit trail
CREATE TABLE IF NOT EXISTS escalations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id   UUID REFERENCES incidents(id) ON DELETE CASCADE,
    escalated_to  TEXT,        -- contact name/channel
    channel       TEXT,        -- sms / email / webhook
    escalated_at  TIMESTAMPTZ DEFAULT now()
);

-- Emergency / escalation contacts
CREATE TABLE IF NOT EXISTS contacts (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name     TEXT,
    channel  TEXT,   -- sms / email / webhook
    address  TEXT,   -- phone / email / URL
    priority INT DEFAULT 1
);