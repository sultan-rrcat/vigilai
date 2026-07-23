import cv2
import numpy as np
import logging
import time
import requests
import base64
import signal
import sys

from app.services.capture import VideoCaptureManager
from app.services.inference import YoloInferenceEngine
from app.services.tracker import ObjectTracker
from app.services.zone_engine import get_normalized_anchor, is_point_in_polygon
from app.services.state_machine import EdgeStateMachine, TrackState
from app.services.kafka_producer import EdgeTelemetryProducer
from app.services.config_sync import ConfigSyncClient
from app.services.perf_monitor import PerfMonitor

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Global flag for graceful headless shutdown
shutdown_requested = False

def handle_shutdown(signum, frame):
    """Listens for termination signals (Ctrl+C, Docker stop) to close gracefully."""
    global shutdown_requested
    logger.info("Shutdown signal received. Terminating pipeline gracefully...")
    shutdown_requested = True


def main():
    global shutdown_requested
    
    # Register signal handlers for background execution
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("Initializing Autonomous Edge Pipeline (Headless Mode)...")

    # Initialize all microservices
    capture = VideoCaptureManager()
    inference = YoloInferenceEngine()
    tracker = ObjectTracker()
    state_machine = EdgeStateMachine()
    telemetry = EdgeTelemetryProducer()
    monitor = PerfMonitor()

    # Initialize the background config synchronizer
    sync = ConfigSyncClient()

    capture.start()

    # We will grab the very first frame to establish the baseline for the Zone Editor
    logger.info("Capturing baseline reference frame for Central Dashboard...")
    for frame in capture.get_frames():
        # Compress to JPEG to save bandwidth
        _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        b64_img = base64.b64encode(buffer).decode("utf-8")

        try:
            cam_id = settings.CAMERA_ID
            res = requests.post(
                f"{settings.CENTRAL_API_URL}/cameras/{cam_id}/reference",
                json={"snapshot_b64": b64_img},
                timeout=5,
                proxies={
                    "http": None,
                    "https": None,
                },
            )
            res.raise_for_status()
            logger.info("Successfully uploaded reference frame to Central Core.")
        except Exception as e:
            logger.error(
                f"Failed to upload reference frame. Make sure Central API is running. Error: {e}"
            )

        break  # We only need one frame, then we break to start the real inference loop

    last_heartbeat = time.time()
    frames_processed = 0
    start_time = time.time()

    try:
        # Give the ConfigSyncClient a moment to pull the initial payload from the API
        time.sleep(1.5)

        for frame in capture.get_frames():
            # Check if a shutdown was requested by the OS/User
            if shutdown_requested:
                break
            
            monitor.begin_frame()

            frames_processed += 1
            height, width = frame.shape[:2]

            # 1. Pull the latest dynamic geometry from the sync client
            active_zones = sync.get_zones()
            config_version = sync.get_config_version()

            # 2. Vision Pipeline
            with monitor.stage("inference"):
                detections = inference.process_frame(frame)
            with monitor.stage("tracker"):
                tracked_objects = tracker.update(detections, frame)
            
            # 3. Zone intersection check
            with monitor.stage("zone_engine"):
                active_track_ids = set()
                zone_memberships = {}
                track_data_map = {}

                for obj in tracked_objects:
                    tid = obj["track_id"]
                    active_track_ids.add(tid)
                    track_data_map[tid] = obj

                    norm_anchor = get_normalized_anchor(obj["bbox"], width, height)
                    is_inside = False
                    triggered_zone_id = None
                    triggered_dwell = 2.0

                    for zone in active_zones:
                        poly = zone.get("polygon", [])
                        if len(poly) >= 3 and is_point_in_polygon(norm_anchor, poly):
                            is_inside = True
                            triggered_zone_id = zone.get("id")
                            triggered_dwell = zone.get("min_dwell_seconds", 2.0)
                            break  # Assign to the first matching zone for this iteration

                    zone_memberships[tid] = is_inside

                    # Attach the specific zone context to the track data for Kafka routing
                    if is_inside:
                        track_data_map[tid]["zone_id"] = triggered_zone_id
                        track_data_map[tid]["dwell_sec"] = triggered_dwell

            # 4. Tick the State Machine
            with monitor.stage("state_machine"):
                events = state_machine.process_frame(active_track_ids, zone_memberships)

            # 5. Route state machine events to Kafka
            for event in events:
                if event["type"] == "intrusion_confirmed":
                    tid = event["track_id"]
                    obj_data = track_data_map.get(tid, {})

                    telemetry.send_intrusion_confirmed(
                        track_id=tid,
                        obj_class=obj_data.get("class_name", "unknown"),
                        trigger_type="zone_dwell",
                        zone_id=obj_data.get("zone_id", "unknown_zone"),
                        dwell_sec=obj_data.get(
                            "dwell_sec", event.get("dwell_seconds", 2.0)
                        ),
                        bbox=obj_data.get("bbox", []),
                        confidence=0.99,
                        frame=frame,
                    )
                elif event["type"] == "track_resolved":
                    telemetry.send_track_resolved(event["track_id"], event["reason"])

            # 6. Send Heartbeat every 3 seconds
            now = time.time()
            if now - last_heartbeat >= 3.0:
                current_fps = frames_processed / (now - start_time)
                telemetry.send_heartbeat(
                    active_tracks=len(active_track_ids),
                    fps=current_fps,
                    config_version=config_version,
                )
                last_heartbeat = now
                frames_processed = 0
                start_time = now
                
            # 7. Flush perf record for this frame
            elapsed = time.time() - start_time if start_time else 1
            live_fps = frames_processed / elapsed if elapsed > 0 else 0
            monitor.flush(fps=live_fps, active_tracks=len(active_track_ids))  # ← end of frame

    except KeyboardInterrupt:
        logger.info("Pipeline stopped manually via KeyboardInterrupt.")
    finally:
        # Cleanly shut down all background threads and connections
        sync.close()
        telemetry.close()
        capture.release()
        monitor.close()
        logger.info("Edge Pipeline terminated cleanly.")


if __name__ == "__main__":
    main()