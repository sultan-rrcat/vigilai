import time
import logging
from enum import Enum, auto
from app.core.config import settings

logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Lifecycle states defined in ARCHITECTURE.md §4"""

    NEW_TRACK = auto()
    CANDIDATE = auto()
    CONFIRMED_INTRUSION = auto()
    RESOLVED = auto()
    DISCARDED = auto()


class PerTrackMachine:
    """Holds the individual state for a single track_id."""

    def __init__(self, track_id: str):
        self.track_id = track_id
        self.state = TrackState.NEW_TRACK
        self.last_seen_time = time.time()
        self.dwell_start_time = None
        self.has_alerted = False

    def update_seen(self):
        self.last_seen_time = time.time()


class EdgeStateMachine:
    """Manages the state lifecycles for all active tracks."""

    def __init__(self):
        self.min_dwell = settings.MIN_DWELL_SECONDS
        self.ttl = settings.TRACK_TTL_SECONDS
        self.tracks: dict[str, PerTrackMachine] = {}

    def process_frame(self, active_track_ids: set, zone_memberships: dict) -> list:
        """
        Evaluates track lifetimes and zone memberships to trigger state transitions.
        zone_memberships is a dict mapping track_id -> bool (True if currently inside a zone).
        Returns a list of events (e.g., confirmed intrusions or resolutions) to send to Kafka.
        """
        events = []
        now = time.time()

        # 1. Update existing tracks and handle active state transitions
        for tid in active_track_ids:
            if tid not in self.tracks:
                self.tracks[tid] = PerTrackMachine(tid)
                logger.debug(f"[{tid}] NEW_TRACK")

            track = self.tracks[tid]
            track.update_seen()
            is_in_zone = zone_memberships.get(tid, False)

            if track.state == TrackState.NEW_TRACK:
                if is_in_zone:
                    track.state = TrackState.CANDIDATE
                    track.dwell_start_time = now
                    logger.info(
                        f"[{tid}] Entered zone -> CANDIDATE. Dwell timer started."
                    )

            elif track.state == TrackState.CANDIDATE:
                if is_in_zone:
                    # Accumulate dwell time
                    dwell_time = now - track.dwell_start_time
                    if dwell_time >= self.min_dwell:
                        track.state = TrackState.CONFIRMED_INTRUSION
                        track.has_alerted = True

                        # Generate the event payload (Kafka producer will attach image/bbox later)
                        events.append(
                            {
                                "type": "intrusion_confirmed",
                                "track_id": tid,
                                "dwell_seconds": dwell_time,
                            }
                        )
                        logger.warning(
                            f"[{tid}] Dwell threshold ({self.min_dwell}s) met -> CONFIRMED_INTRUSION!"
                        )
                else:
                    # Left the zone before the dwell threshold was met
                    track.state = TrackState.NEW_TRACK
                    track.dwell_start_time = None
                    logger.debug(
                        f"[{tid}] Left zone before threshold -> Reset to NEW_TRACK."
                    )

            elif track.state == TrackState.CONFIRMED_INTRUSION:
                # Once confirmed, it stays confirmed until it completely expires (resolved)
                pass

        # 2. Cleanup lost or stale tracks
        stale_tids = []
        for tid, track in self.tracks.items():
            if tid not in active_track_ids:
                time_lost = now - track.last_seen_time

                if time_lost > self.ttl:
                    stale_tids.append(tid)

                    if track.state == TrackState.CONFIRMED_INTRUSION:
                        # EDGE MEMORY CLEANUP ONLY
                        # We change state to DISCARDED locally but DO NOT send a "track_resolved"
                        # event to Kafka. This forces the human operator to resolve it centrally.
                        track.state = TrackState.DISCARDED
                        # events.append(
                        #     {
                        #         "type": "track_resolved",
                        #         "track_id": tid,
                        #         "reason": "exited_view_or_lost",
                        #     }
                        # )
                        # logger.info(f"[{tid}] Track lost for >{self.ttl}s -> RESOLVED.")
                    else:
                        track.state = TrackState.DISCARDED
                        logger.debug(
                            f"[{tid}] Track lost before threshold -> DISCARDED."
                        )

        # Remove stale tracks from memory
        for tid in stale_tids:
            del self.tracks[tid]

        return events
