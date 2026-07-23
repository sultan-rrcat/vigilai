/**
 * Vigil AI — Frozen Contracts (TypeScript)
 * ==========================================
 *
 * Mirrors contracts/schemas.py. This file is hand-kept in sync with the
 * Python contract, not code-generated — when you change one, change the
 * other in the same commit and bump CONTRACT_VERSION in both.
 *
 * See ARCHITECTURE.md §5 and CONVENTIONS.md for the narrative spec.
 */

export const CONTRACT_VERSION = "1.0.0";

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

/** Normalized coordinate, per CONVENTIONS.md §2: always in [0, 1]. */
export type NormCoord = number;

/** Normalized [x, y] point. */
export type Point = [NormCoord, NormCoord];

export type ObjectClass = "person" | "vehicle";

export type TriggerType = "zone_dwell" | "line_crossing";

/** Per CONVENTIONS.md §5. "both" is only valid as a config value. */
export type CrossingDirection = "a_to_b" | "b_to_a" | "both";

/** Direction actually observed on a fired crossing event — never "both". */
export type FiredCrossingDirection = "a_to_b" | "b_to_a";

export type DeviceStatus = "online" | "degraded" | "offline";

export type TrackResolutionReason = "exited_zone" | "left_frame" | "track_lost";

export type IncidentStatus = "active" | "acknowledged" | "escalated" | "resolved";

// ---------------------------------------------------------------------------
// Config-pull / zone-editor shapes: GET/PUT via zones.py, tripwires.py, edge.py
// ---------------------------------------------------------------------------

export interface Zone {
  id: string;
  name: string;
  /** Normalized, >= 3 points, not closed (CONVENTIONS.md §4). */
  polygon: Point[];
  min_dwell_seconds: number;
  enabled: boolean;
}

export interface Tripwire {
  id: string;
  name: string;
  /** [P1, P2] — order defines a_to_b direction (CONVENTIONS.md §5). */
  line: [Point, Point];
  watched_direction: CrossingDirection;
  enabled: boolean;
}

export interface EdgeConfigResponse {
  camera_id: string;
  config_version: string;
  zones: Zone[];
  tripwires: Tripwire[];
  track_ttl_seconds: number;
  reference_width?: number;
  reference_height?: number;
}

// ---------------------------------------------------------------------------
// Kafka-derived event shapes, as they arrive over the incidents/WebSocket API
// (the frontend never talks to Kafka directly — these mirror the payloads
// the backend re-emits over incidents.py / the WebSocket broadcaster).
// ---------------------------------------------------------------------------

export interface IntrusionConfirmedEvent {
  type: "intrusion_confirmed";
  camera_id: string;
  track_id: string;
  object_class: ObjectClass;
  trigger_type: TriggerType;
  zone_id?: string;
  tripwire_id?: string;
  dwell_seconds?: number;
  crossing_direction?: FiredCrossingDirection;
  bbox: [number, number, number, number];
  trajectory: Point[];
  confidence: number;
  timestamp: string;
  snapshot_b64?: string; // typically resolved to a URL by the backend instead
  snapshot_url?: string;
}

export interface HeartbeatEvent {
  type: "heartbeat";
  camera_id: string;
  device_status: DeviceStatus;
  active_tracks: number;
  fps: number;
  cpu_temp_c?: number;
  config_version: string;
  timestamp: string;
}

export interface TrackResolvedEvent {
  type: "track_resolved";
  camera_id: string;
  track_id: string;
  reason: TrackResolutionReason;
  timestamp: string;
}

export type EdgeEvent = IntrusionConfirmedEvent | HeartbeatEvent | TrackResolvedEvent;

// ---------------------------------------------------------------------------
// Incident (as persisted + returned by incidents.py)
// ---------------------------------------------------------------------------

export interface Incident {
  id: string;
  camera_id: string;
  track_id: string;
  object_class: ObjectClass;
  trigger_type: TriggerType;
  zone_id?: string;
  tripwire_id?: string;
  snapshot_path?: string;
  confidence: number;
  status: IncidentStatus;
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolved_at?: string;
  created_at: string;
}