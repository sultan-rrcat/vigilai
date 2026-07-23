import cv2
import numpy as np
import logging
import time
from app.services.capture import VideoCaptureManager
from app.services.inference import YoloInferenceEngine
from app.services.tracker import ObjectTracker
from app.services.zone_engine import get_normalized_anchor, is_point_in_polygon
from app.services.state_machine import EdgeStateMachine, TrackState
from app.services.kafka_producer import EdgeTelemetryProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CUSTOM_ZONE = []

def mouse_callback(event, x, y, flags, param):
    global CUSTOM_ZONE
    width, height = param
    if event == cv2.EVENT_LBUTTONDOWN:
        norm_x = x / width
        norm_y = y / height
        CUSTOM_ZONE.append([norm_x, norm_y])

def main():
    global CUSTOM_ZONE
    logger.info("Initializing Full Edge Pipeline with Telemetry...")
    
    capture = VideoCaptureManager()
    inference = YoloInferenceEngine()
    tracker = ObjectTracker()
    state_machine = EdgeStateMachine()
    telemetry = EdgeTelemetryProducer() # Initialize our stateless producer

    capture.start()
    cv2.namedWindow("Vigil AI - Telemetry Test")
    
    last_heartbeat = time.time()
    frames_processed = 0
    start_time = time.time()

    try:
        for frame in capture.get_frames():
            frames_processed += 1
            height, width = frame.shape[:2]
            cv2.setMouseCallback("Vigil AI - Telemetry Test", mouse_callback, param=(width, height))

            # Draw custom zone
            if len(CUSTOM_ZONE) > 0:
                zone_pts = np.array([[(int(x * width), int(y * height)) for x, y in CUSTOM_ZONE]], np.int32)
                is_closed = len(CUSTOM_ZONE) >= 3
                cv2.polylines(frame, zone_pts, isClosed=is_closed, color=(255, 0, 0), thickness=2)
                for pt in CUSTOM_ZONE:
                    cv2.circle(frame, (int(pt[0]*width), int(pt[1]*height)), 4, (0, 0, 255), -1)

            detections = inference.process_frame(frame)
            tracked_objects = tracker.update(detections, frame)

            active_track_ids = set()
            zone_memberships = {}
            track_data_map = {} 

            for obj in tracked_objects:
                tid = obj["track_id"]
                active_track_ids.add(tid)
                track_data_map[tid] = obj 
                
                norm_anchor = get_normalized_anchor(obj["bbox"], width, height)
                is_inside = False
                if len(CUSTOM_ZONE) >= 3:
                    is_inside = is_point_in_polygon(norm_anchor, CUSTOM_ZONE)
                zone_memberships[tid] = is_inside

            # Tick the State Machine
            events = state_machine.process_frame(active_track_ids, zone_memberships)
            
            # Route state machine events to Kafka
            for event in events:
                if event["type"] == "intrusion_confirmed":
                    tid = event["track_id"]
                    obj_data = track_data_map.get(tid, {})
                    
                    telemetry.send_intrusion_confirmed(
                        track_id=tid,
                        obj_class=obj_data.get("class_name", "unknown"),
                        trigger_type="zone_dwell",
                        zone_id="custom_test_zone",
                        dwell_sec=event["dwell_seconds"],
                        bbox=obj_data.get("bbox", []),
                        confidence=0.99, 
                        frame=frame 
                    )
                elif event["type"] == "track_resolved":
                    telemetry.send_track_resolved(event["track_id"], event["reason"])

            # Send Heartbeat every 3 seconds
            now = time.time()
            if now - last_heartbeat >= 3.0:
                current_fps = frames_processed / (now - start_time)
                telemetry.send_heartbeat(
                    active_tracks=len(active_track_ids),
                    fps=current_fps,
                    config_version="local_test_1"
                )
                last_heartbeat = now
                frames_processed = 0
                start_time = now

            # Draw Results Based on State
            for obj in tracked_objects:
                tid = obj["track_id"]
                x1, y1, x2, y2 = obj["bbox"]
                norm_anchor = get_normalized_anchor(obj["bbox"], width, height)

                track_state = state_machine.tracks[tid].state if tid in state_machine.tracks else TrackState.NEW_TRACK

                if track_state == TrackState.CONFIRMED_INTRUSION:
                    color = (0, 0, 255) 
                    status = "INTRUSION!"
                elif track_state == TrackState.CANDIDATE:
                    color = (0, 255, 255) 
                    status = "DWELLING..."
                else:
                    color = (0, 165, 255) 
                    status = "TRACKING"

                label = f"{obj['class_name']} [{tid}] - {status}"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + len(label)*9, y1), color, -1)
                cv2.putText(frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

                anchor_pixel = (int(norm_anchor[0] * width), int(norm_anchor[1] * height))
                cv2.circle(frame, anchor_pixel, radius=5, color=(0, 255, 0), thickness=-1)

            cv2.imshow("Vigil AI - Telemetry Test", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                CUSTOM_ZONE = []
                logger.info("Custom zone cleared.")
                
    finally:
        telemetry.close()
        capture.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()