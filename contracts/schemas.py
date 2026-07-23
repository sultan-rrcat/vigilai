"""
Vigil AI — Frozen Contracts (Python / Pydantic v2)
====================================================

Single source of truth for:
  1. The `edge_events` Kafka message schemas (edge -> central), and
  2. The `GET /edge/{camera_id}/config` response schema (central -> edge).

See ARCHITECTURE.md §5 for the narrative spec and CONVENTIONS.md for
the coordinate system these fields assume (normalized [0,1] points,
bottom-center anchor, a_to_b/b_to_a tripwire direction).

Usage
-----
This file is meant to be imported unmodified by both:
  - edge/app/services/kafka_producer.py   (construct + serialize before publish)
  - central/backend/services/kafka_consumer_service.py (parse + validate on ingest)
  - central/backend/routes/edge.py         (response_model=EdgeConfigResponse)

Because this is a monorepo (central/ and edge/ under one root), both
sides should import this module directly (e.g. via a shared path added
in each Dockerfile / PYTHONPATH) rather than copy-pasting it. If it
must be copied, copy the whole file verbatim and keep CONTRACT_VERSION
in sync on both sides.

Changing a field here is a breaking-contract change: bump
CONTRACT_VERSION and update every producer/consumer of that field in
the same commit.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, confloat, conlist

CONTRACT_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

# A normalized coordinate, per CONVENTIONS.md §2: always in [0.0, 1.0].
NormCoord = Annotated[float, Field(ge=0.0, le=1.0)]

# A normalized [x, y] point.
Point = conlist(NormCoord, min_length=2, max_length=2)

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class ObjectClass(str, Enum):
    person = "person"
    vehicle = "vehicle"


class TriggerType(str, Enum):
    zone_dwell = "zone_dwell"
    line_crossing = "line_crossing"


class CrossingDirection(str, Enum):
    """Per CONVENTIONS.md §5 — unambiguous given a tripwire's P1->P2 order."""

    a_to_b = "a_to_b"
    b_to_a = "b_to_a"
    both = "both"  # only valid as a *config* value (watched_direction),
    # never as a value inside a fired crossing event.


class DeviceStatus(str, Enum):
    online = "online"
    degraded = "degraded"
    offline = "offline"


class TrackResolutionReason(str, Enum):
    exited_zone = "exited_zone"
    left_frame = "left_frame"
    track_lost = "track_lost"


class IncidentStatus(str, Enum):
    active = "active"
    acknowledged = "acknowledged"
    escalated = "escalated"
    resolved = "resolved"


# ---------------------------------------------------------------------------
# Kafka: `edge_events` topic, discriminated by `type` (ARCHITECTURE.md §5.1)
# ---------------------------------------------------------------------------


class IntrusionConfirmedEvent(BaseModel):
    """Emitted once when a track's state machine reaches CONFIRMED_INTRUSION."""

    type: Literal["intrusion_confirmed"] = "intrusion_confirmed"
    camera_id: str
    track_id: str
    object_class: ObjectClass
    trigger_type: TriggerType

    # Exactly one of these is set, matching trigger_type.
    zone_id: str | None = None
    tripwire_id: str | None = None

    # zone_dwell only:
    dwell_seconds: float | None = Field(default=None, ge=0.0)
    # line_crossing only — the direction actually observed, never "both":
    crossing_direction: Literal[CrossingDirection.a_to_b, CrossingDirection.b_to_a] | None = None

    bbox: conlist(float, min_length=4, max_length=4)  # [x, y, w, h] in source pixels
    trajectory: list[Point] = Field(default_factory=list)  # normalized anchor points
    confidence: Confidence
    timestamp: str  # ISO-8601 UTC, e.g. "2026-07-13T10:15:32.120Z"
    snapshot_b64: str


class HeartbeatEvent(BaseModel):
    """Emitted every 3s by each edge node (ARCHITECTURE.md §2.1 Smart Telemetry)."""

    type: Literal["heartbeat"] = "heartbeat"
    camera_id: str
    device_status: DeviceStatus
    active_tracks: int = Field(ge=0)
    fps: float = Field(ge=0.0)
    cpu_temp_c: float | None = None
    config_version: str  # lets central detect stale-config edge nodes
    timestamp: str


class TrackResolvedEvent(BaseModel):
    """Emitted once when a track exits RESOLVED, enabling incident auto-clear."""

    type: Literal["track_resolved"] = "track_resolved"
    camera_id: str
    track_id: str
    reason: TrackResolutionReason
    timestamp: str


EdgeEvent = Annotated[
    Union[IntrusionConfirmedEvent, HeartbeatEvent, TrackResolvedEvent],
    Field(discriminator="type"),
]


class EdgeEventEnvelope(BaseModel):
    """
    Convenience wrapper for validating a raw Kafka message value.

    Usage on the consumer side:
        raw = json.loads(msg.value())
        event = EdgeEventEnvelope.model_validate({"event": raw}).event
    """

    event: EdgeEvent


# ---------------------------------------------------------------------------
# Config-pull: GET /edge/{camera_id}/config  (ARCHITECTURE.md §5.5)
# ---------------------------------------------------------------------------


class Zone(BaseModel):
    id: str
    name: str
    polygon: conlist(Point, min_length=3)  # normalized, not closed (CONVENTIONS.md §4)
    min_dwell_seconds: float = Field(default=2.0, ge=0.0)
    enabled: bool = True


class Tripwire(BaseModel):
    id: str
    name: str
    line: conlist(Point, min_length=2, max_length=2)  # [P1, P2], order defines direction
    watched_direction: CrossingDirection = CrossingDirection.both
    enabled: bool = True


class EdgeConfigResponse(BaseModel):
    """Response body for GET /edge/{camera_id}/config."""

    camera_id: str
    config_version: str
    zones: list[Zone] = Field(default_factory=list)
    tripwires: list[Tripwire] = Field(default_factory=list)
    track_ttl_seconds: float = Field(default=5.0, ge=0.0)
    # Reference frame this geometry was authored against — lets the edge
    # sanity-check aspect ratio per CONVENTIONS.md §7.
    reference_width: int | None = None
    reference_height: int | None = None