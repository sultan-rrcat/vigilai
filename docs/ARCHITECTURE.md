======================================================================
VIGIL AI: DISTRIBUTED EDGE-TO-CORE INTRUSION DETECTION SYSTEM (AIRGAPPED)
======================================================================

# 0. Overview

Vigil AI is an air-gapped, distributed perimeter and restricted-zone
intrusion detection system. It follows an **edge-to-core** architecture:
all real-time perception (detection + tracking) runs on low-power edge
nodes co-located with each camera, while the central core is responsible
purely for aggregation, persistence, escalation, and operator-facing
visualization.

The system detects people (and optionally vehicles) entering
operator-defined **restricted zones** or crossing **virtual tripwires**,
confirms the intrusion using multi-frame object tracking (not
single-frame confidence), and raises an incident that is synced in
real time to a central dashboard for human acknowledgement and
escalation.

This document is self-contained and covers: architecture, data flow,
message schemas, state machines, database schema, API surface, folder
structure, and a phased implementation task list. It is intended to be
sufficient on its own to begin implementation.

Two companion files at the repo root make the contracts in this
document concrete and enforceable in code:
- `CONVENTIONS.md` — the normalized coordinate system, anchor point,
  and tripwire direction definition referenced throughout §4–§6.
- `contracts/` — frozen Pydantic (`schemas.py`) and TypeScript
  (`types.ts`) definitions of the message/response shapes in §5,
  meant to be imported directly by edge, central, and frontend code
  rather than re-derived from this document each time.

---

# 1. High-Level Architecture Diagram

```
[ EDGE NODE - Raspberry Pi 4 (4GB) / Jetson-class device ]
Location: Camera Housing / Near CCTV
Role: Real-time inference, Object Tracking, Zone Logic & State Management

  ┌─────────────────┐
  │ CCTV Camera     │
  │ (RTSP Stream)   │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Python ONNX          │
  │ - Read frames (N FPS)│
  │ - YOLOv26 (person/    │
  │   vehicle detector)  │
  └────────┬────────────┘
           │  raw detections (bboxes + class + conf)
           ▼
  ┌─────────────────────┐
  │ Tracker              │
  │ (DeepSORT)            │
  │ - Assigns track_id    │
  │ - Maintains identity   │
  │   across frames        │
  └────────┬────────────┘
           │  tracked objects (track_id, bbox, class)
           ▼
  ┌─────────────────────┐
  │ Zone / Tripwire      │
  │ Engine                │
  │ - Point-in-polygon    │
  │ - Line-crossing       │
  │ - Dwell-time check     │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Edge State Machine   │
  │ (Per-track lifecycle) │
  │ - Evaluates dwell/     │
  │   crossing conditions │
  │ - Triggers Alarm       │
  └────────┬────────────┘
           │ (JSON + B64 JPEG on events / Heartbeat every 3s)
           ▼
  ┌─────────────────────┐
  │ Kafka Producer        │
  │ (confluent-kafka)     │
  └────────┬────────────┘
           │
======================================================================
                         [ AIRGAPPED NETWORK ]
======================================================================
           │
           ▼
[ CENTRAL SERVER (CORE) - High Compute Node / DB Server ]
Role: Aggregation, Self-Healing Sync, Escalation, Persistence & UI

  ┌─────────────────────┐        ┌───────────────────────┐
  │ Kafka Broker         │ ◄───── │ Local Docker Registry │
  │ (edge_events)         │        │ (Update Edge Images)  │
  └────────┬────────────┘        └───────────────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Ingestion Worker      │
  │ (Kafka Consumer)      │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Incident Manager       │
  │ - Late-Joiner Sync      │
  │ - Auto-Escalation       │
  └────────┬────────────┘
           │
    ┌──────┴───────┐
    ▼              ▼
┌────────┐    ┌──────────────┐
│ Postgres │    │ WebSockets   │
│ Database │    │ (Broadcaster)│
└────────┘    └──────┬───────┘
                     │
======================================================================
                     [ CLIENT / BROWSER ]
======================================================================
                     │
                     ▼
            ┌─────────────────────┐
            │ React Dashboard      │
            │ - Incident Grid       │
            │ - Zone/Map Overlay    │
            │ - Static Snapshots    │
            │ - Alert Toasts         │
            └─────────────────────┘
```

---

# 2. Core Features

## 2.1 Autonomous Edge Pipeline (Raspberry Pi / Jetson)

### Local Inference
Runs an optimized ONNX YOLOv26 model directly on the camera source to
detect people and (optionally) vehicles.

### Multi-Object Tracking (DeepSORT)
Unlike simple frame-by-frame confidence smoothing, each detected object
is assigned a persistent `track_id` using **DeepSORT** (Kalman filter
motion model + appearance re-identification embedding). This solves two
problems that raw detection alone cannot:

- **Identity persistence** — the same intruder is tracked as a single
  entity across occlusion/flicker, instead of being treated as N
  independent detections.
- **Trajectory-aware logic** — enables direction-of-travel and
  line-crossing detection (e.g. "entered through the north fence"),
  and dwell-time accumulation per individual rather than per frame.

### Zone & Tripwire Engine
Operators define, per camera, one or more of:
- **Restricted zones** — arbitrary polygons; a track is "inside" a zone
  once its anchor point (bottom-center of bbox) falls within it.
- **Tripwires** — a directional line segment; crossing it in the
  configured direction raises a crossing event.

### Stateful Per-Track Consensus
A per-track state machine (see §4) replaces raw single-frame
thresholding. A track must satisfy a **minimum dwell time inside a
zone** (or a valid tripwire crossing) before an incident is confirmed,
which suppresses transient false positives (e.g. a person briefly
clipping the edge of a zone boundary due to detector jitter).

### Smart Telemetry
Uses **Confluent Kafka** to:
- Send visual evidence (annotated snapshot) only after a confirmed
  intrusion.
- Publish lightweight heartbeats every 3 seconds containing device
  health, active track count, and current state summary.

## 2.2 Central Core (Aggregation & Orchestration)

### Kafka Event Ingestion
A daemonized consumer continuously processes intrusion events and edge
heartbeats.

### Self-Healing Synchronization
Heartbeats automatically:
- Recover dropped UI states.
- Clear ghost alarms if an edge node reports no active tracks.
- Synchronize newly connected dashboard clients with current system
  state.

### Automatic Escalation
Background workers monitor unacknowledged incidents. If an alarm is
ignored for the configured timeout (default **15 seconds**), it is
automatically escalated (e.g. notification to a secondary contact
list).

### PostgreSQL Persistence
Stores:
- Incident metadata (zone/tripwire, track_id, class, timestamps)
- Alarm history and acknowledgement audit trail
- Captured evidence snapshots (path/reference)
- Escalation logs
- Zone/tripwire definitions per camera

## 2.3 Frontend Dashboard
Built with **React + Vite**:
- Real-time WebSocket synchronization
- Instant alarm notifications
- Camera management + live zone/tripwire editor (draw polygons/lines
  on a snapshot of the camera view)
- Incident grid with snapshot, track trajectory summary, and
  acknowledge/escalate controls
- Dynamic system settings (dwell-time thresholds, escalation timeout,
  storage retention)

---

# 3. Repository Philosophy

Vigil AI is designed for secure, bandwidth-constrained environments
such as:
- Air-gapped facilities
- Perimeter fences and restricted yards
- Industrial plants
- Government / defense installations

The architecture emphasizes:

## Bandwidth Efficiency
Edge devices never stream continuous video to the core. Only a single
Base64-encoded annotated frame is transmitted after an intrusion is
confirmed.

## Decentralized Compute
All expensive inference, tracking, and decision-making occurs on the
edge. The central server remains lightweight, enabling large-scale
horizontal deployment across many camera nodes.

## Fault Tolerance
If network connectivity is interrupted:
- Edge devices continue detecting, tracking, and evaluating zone logic
  autonomously, buffering unsent events locally.
- Heartbeats automatically restore backend and dashboard state once
  communication resumes.

---

# 4. Edge State Machine

Detection alone is not evidence of an intrusion — an object must
persist inside a restricted zone (or complete a valid tripwire
crossing) for a configured duration before an alarm is raised. State is
tracked **per `track_id`**, not globally per camera.

```
NEW_TRACK → CANDIDATE → CONFIRMED_INTRUSION → RESOLVED
                │
                └──(track lost before threshold)──→ DISCARDED
```

| State | Trigger / Condition |
|---|---|
| `NEW_TRACK` | DeepSORT assigns a new `track_id` for a detected person/vehicle. |
| `CANDIDATE` | Track's anchor point enters a defined zone, or crosses a tripwire in the watched direction. Dwell timer starts. |
| `CONFIRMED_INTRUSION` | Track remains inside the zone for ≥ `min_dwell_seconds` (configurable, default 2s), OR a tripwire crossing is instantaneously confirmed. Kafka event emitted with snapshot. |
| `RESOLVED` | Track exits the zone / leaves camera view / is lost by the tracker for > `track_ttl_seconds`. A resolution event is emitted so the core can auto-clear the incident if unacknowledged action is not required. |
| `DISCARDED` | Track lost by DeepSORT before the dwell threshold was met (e.g. detector jitter, pass-through without lingering). No event emitted. |

This design intentionally removes reliance on weighted-average
confidence smoothing across a whole frame; confidence per-frame is only
used at the detector layer (thresholding raw YOLO output), while
**identity + dwell/crossing time** — derived from tracking, not
averaged confidence — is what confirms an incident.

---

# 5. Kafka Topic & Message Schemas

## 5.1 Topic

A single topic is used for all edge→core telemetry, keyed by
`camera_id` (so all messages from one camera land on the same
partition and are processed in order). Each message carries a `type`
discriminator; the ingestion worker branches on it.

| Topic | Producer | Consumer | Key | Purpose |
|---|---|---|---|---|
| `edge_events` | Edge | Central Ingestion Worker | `camera_id` | All edge telemetry — intrusion confirmations, heartbeats, and track resolutions, distinguished by `type` |

This keeps the pipeline to one producer config on the edge and one
consumer group on the core — simpler to operate and debug for a
single-developer deployment than managing multiple topics'
retention/partitioning independently. If event volume or differing
retention needs ever justify it, `edge_events` can be split by `type`
into dedicated topics later without changing the message schemas
below.

## 5.2 `type: "intrusion_confirmed"`

```json
{
  "type": "intrusion_confirmed",
  "camera_id": "b6f2b6b0-1234-4d3a-9f1a-000000000001",
  "track_id": "trk_00234",
  "object_class": "person",
  "trigger_type": "zone_dwell",
  "zone_id": "zone_north_fence",
  "dwell_seconds": 2.4,
  "bbox": [412, 180, 96, 210],
  "trajectory": [[400, 390], [408, 385], [412, 380]],
  "confidence": 0.91,
  "timestamp": "2026-07-13T10:15:32.120Z",
  "snapshot_b64": "<base64 jpeg>"
}
```

For a tripwire crossing, `trigger_type` is `"line_crossing"`,
`zone_id` is replaced conceptually by `"tripwire_id"`, and
`dwell_seconds` is omitted in favor of `"crossing_direction"`, whose
value is always the observed `"a_to_b"` or `"b_to_a"` (never `"both"`
— see `CONVENTIONS.md §5` for how direction is defined and detected).

## 5.3 `type: "heartbeat"`

```json
{
  "type": "heartbeat",
  "camera_id": "b6f2b6b0-1234-4d3a-9f1a-000000000001",
  "device_status": "online",
  "active_tracks": 2,
  "fps": 8.7,
  "cpu_temp_c": 61.2,
  "config_version": "3",
  "timestamp": "2026-07-13T10:15:33.000Z"
}
```

`config_version` reports which zone/tripwire config revision the edge
is currently running (see §5.5), so the core can detect a stale edge
node even without an explicit config-pull log.

## 5.4 `type: "track_resolved"`

```json
{
  "type": "track_resolved",
  "camera_id": "b6f2b6b0-1234-4d3a-9f1a-000000000001",
  "track_id": "trk_00234",
  "reason": "exited_zone",
  "timestamp": "2026-07-13T10:16:02.500Z"
}
```

## 5.5 Config Distribution (Core → Edge) — outside Kafka

Kafka in this architecture is intentionally **unidirectional**
(edge → core telemetry only). Zone and tripwire definitions therefore
do **not** travel over Kafka — pushing config that way would require
the edge to also run a Kafka consumer and trust inbound broker
traffic, which adds complexity without benefit at this scale.

Instead, config flows core → edge over the same plain HTTP channel
already used for OTA/model updates:

1. The dashboard's Zone/Tripwire Editor saves changes via a normal
   REST call to the central backend (`PUT /cameras/{id}/zones`, etc.),
   which increments a `config_version` for that camera.
2. Each edge node polls `GET /edge/{camera_id}/config` on a timer
   (e.g. every 30–60s) and on startup.
3. The edge compares the returned `config_version` against its local
   cache; if unchanged, it does nothing. If changed, it reloads the
   Zone/Tripwire Engine (§4) with the new geometry and thresholds.
4. The edge persists the last-known-good config to local disk, so it
   keeps operating with it if the core becomes unreachable — consistent
   with the fault-tolerance principle in §3.

This keeps the two channels cleanly separated: **Kafka = telemetry
out**, **REST = config in**, which is easier to reason about and debug
solo than a bidirectional Kafka setup.

---

# 6. Database Schema (PostgreSQL)

```sql
-- Cameras / edge nodes
CREATE TABLE cameras (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    location        TEXT,
    rtsp_url        TEXT,
    status          TEXT DEFAULT 'offline', -- online / offline
    last_heartbeat  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Restricted zones (polygons) per camera
CREATE TABLE zones (
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
CREATE TABLE tripwires (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id          UUID REFERENCES cameras(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    line                JSONB NOT NULL,     -- [P1,P2] normalized coords, order defines direction
    watched_direction   TEXT NOT NULL,      -- "a_to_b" | "b_to_a" | "both" — see CONVENTIONS.md §5
    enabled             BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Confirmed incidents
CREATE TABLE incidents (
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
CREATE TABLE escalations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id   UUID REFERENCES incidents(id) ON DELETE CASCADE,
    escalated_to  TEXT,        -- contact name/channel
    channel       TEXT,        -- sms / email / webhook
    escalated_at  TIMESTAMPTZ DEFAULT now()
);

-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'operator', -- admin / operator
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Emergency / escalation contacts
CREATE TABLE contacts (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name     TEXT,
    channel  TEXT,   -- sms / email / webhook
    address  TEXT,   -- phone / email / URL
    priority INT DEFAULT 1
);
```

---

# 7. Backend API Surface (FastAPI)

| Route file | Responsibility |
|---|---|
| `auth.py` | Login, token issuance, session management |
| `cameras.py` | CRUD for camera/edge-node registration |
| `zones.py` | CRUD for restricted zone polygons per camera |
| `tripwires.py` | CRUD for tripwire line segments per camera |
| `incidents.py` | List/get incidents, acknowledge, resolve, filter by camera/zone/date |
| `contacts.py` | CRUD for escalation contacts |
| `edge.py` | Edge node registration; `GET /edge/{camera_id}/config` for zone/tripwire config pull (versioned, see §5.5); health endpoints |
| `settings.py` | Global settings: dwell thresholds, escalation timeout, retention policy |
| `users.py` | User management (admin only) |

Note the addition of `zones.py` and `tripwires.py`, which did not exist
in a simple single-region detection design — these are required so
operators can draw and manage detection geometry per camera from the
dashboard.

---

# 8. Repository Structure

```text
vigil-ai-core/
│
├── central/
│   ├── backend/
│   │   ├── core/               # security, logging, db session
│   │   ├── db/                 # schema.sql, migrations
│   │   ├── routes/              # auth, cameras, zones, tripwires,
│   │   │                        # incidents, contacts, edge, settings, users
│   │   ├── services/
│   │   │   ├── kafka_consumer_service.py
│   │   │   ├── incident_service.py
│   │   │   ├── escalation_service.py
│   │   │   └── ws_manager.py
│   │   ├── incident_images/     # stored intrusion snapshots
│   │   ├── models/              # YOLOv26 ONNX weights (for edge image builds)
│   │   ├── tests/
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── frontend/                # React + Vite dashboard
│   │   └── src/
│   │       ├── components/
│   │       │   ├── ZoneEditor.tsx       # draw polygons/tripwires on camera snapshot
│   │       │   ├── EdgeCameraCard.tsx
│   │       │   ├── IncidentGrid.tsx
│   │       │   └── ...
│   │       ├── pages/
│   │       ├── context/
│   │       └── hooks/
│   │
│   └── docker-compose.yaml
│
├── edge/
│   ├── app/
│   │   ├── core/                # edge config
│   │   ├── models/               # YOLOv26 ONNX model
│   │   ├── services/
│   │   │   ├── inference.py       # YOLOv26 ONNX detection
│   │   │   ├── tracker.py          # DeepSORT wrapper
│   │   │   ├── zone_engine.py       # polygon / line-crossing logic
│   │   │   ├── state_machine.py      # per-track lifecycle (§4)
│   │   │   └── kafka_producer.py
│   │   └── tests/
│   ├── docker-compose.yaml
│   └── Dockerfile
│
└── README.md
```

---

# 9. Deployment Topology

## Central Server
- Linux host, Docker + Docker Compose
- Python 3.10+
- Kafka (KRaft mode, single-broker for on-prem/air-gapped)
- PostgreSQL
- No GPU required — inference is fully offloaded to edge nodes.

## Edge Device
- Raspberry Pi 4 (4GB+) or Jetson-class device for higher camera counts
- Docker + Docker Compose
- Python 3.10+
- Local Docker registry on the central server distributes updated edge
  images without internet access.

---

# 10. Implementation Plan & Task List

## Phase 0 — Foundations
- [ ] Define normalized coordinate convention (0–1 range) shared by
      edge zone/tripwire evaluation and frontend drawing tools.
- [ ] Finalize Kafka topic names/partitioning and message schemas
      (§5) as the contract between edge and core.
- [ ] Provision Kafka (KRaft) and PostgreSQL on the central server.

## Phase 1 — Edge Pipeline
- [ ] RTSP capture loop (configurable FPS).
- [ ] YOLOv26 ONNX inference wrapper (load pre-trained model, class
      filtering to person/vehicle).
- [ ] Integrate DeepSORT: appearance embedding model, Kalman filter
      tracker, track ID lifecycle.
- [ ] Zone engine: point-in-polygon test against normalized zone
      definitions pulled from core.
- [ ] Tripwire engine: line-crossing detection with direction check.
- [ ] Per-track state machine (§4) with configurable
      `min_dwell_seconds` and `track_ttl_seconds`.
- [ ] Kafka producer: confirmed-intrusion events, heartbeats,
      track-resolution events.
- [ ] Local buffering/retry for Kafka publish during network
      interruption.
- [ ] Edge config sync: implement the versioned HTTP pull described in
      §5.5 (`GET /edge/{camera_id}/config`) — poll on a timer and on
      boot, reload the Zone/Tripwire Engine on version change, cache
      last-known-good config to disk for offline resilience.
- [ ] Unit tests: tracker identity continuity, zone/tripwire math,
      state transitions.

## Phase 2 — Central Ingestion & Persistence
- [ ] Kafka consumer service for all three topics.
- [ ] Incident manager: create/update incident rows, auto-clear on
      `track_resolved`, late-joiner state sync for new WS clients.
- [ ] PostgreSQL schema migration (§6).
- [ ] Snapshot storage (`incident_images/`) with retention policy.
- [ ] Escalation worker: poll unacknowledged incidents, apply
      configurable timeout (default 15s), notify configured contacts.
- [ ] WebSocket broadcaster for real-time dashboard updates.

## Phase 3 — Backend API
- [ ] `auth.py`, `users.py` — authentication and role-based access.
- [ ] `cameras.py` — register/edit edge nodes.
- [ ] `zones.py`, `tripwires.py` — CRUD + validation of geometry.
- [ ] `incidents.py` — list/filter/acknowledge/resolve.
- [ ] `contacts.py`, `settings.py` — escalation config, thresholds.
- [ ] `edge.py` — edge registration, heartbeat ingestion endpoint (if
      not solely via Kafka), config-pull endpoint.

## Phase 4 — Frontend Dashboard
- [ ] Camera management view.
- [ ] **Zone/tripwire editor**: overlay a live camera snapshot,
      draw/edit polygons and directional lines, save normalized
      coordinates.
- [ ] Incident grid with snapshot, track trajectory summary, and
      acknowledge/escalate actions.
- [ ] Real-time alert toasts via WebSocket.
- [ ] Settings pages: dwell threshold, escalation timeout, retention.
- [ ] Auth/login, protected routes, user management.

## Phase 5 — Hardening & Ops
- [ ] Docker image builds for edge (ARM64) and central (amd64), pushed
      to the local Docker registry.
- [ ] Load testing with multiple simulated edge nodes.
- [ ] Documentation: deployment runbook, troubleshooting guide.
- [ ] Optional: OpenVINO/TensorRT acceleration for higher-FPS edge
      inference.
- [ ] Optional: SMS/email/webhook integrations for escalation channel.

---

# 11. Key Architectural Differences from a Naive Single-Frame Design

| Aspect | Naive approach | Vigil AI approach |
|---|---|---|
| Confirmation signal | Weighted-average confidence over a rolling frame window | Per-track dwell time inside a zone, or a discrete tripwire crossing, derived from tracked identity |
| Object identity | None — each frame's detections are independent | DeepSORT assigns and maintains a `track_id` across frames |
| False-positive suppression | Frame-level confidence smoothing | Track-level persistence + configurable dwell threshold |
| Directional awareness | Not possible without identity | Supported via tripwire crossing direction and trajectory logging |
| State granularity | Per-camera global state | Per-track state machine, multiple concurrent tracks per camera |