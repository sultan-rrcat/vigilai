import json
import base64
import time
import cv2
import logging
from confluent_kafka import Producer
from app.core.config import settings

logger = logging.getLogger(__name__)

class EdgeTelemetryProducer:
    def __init__(self):
        self.camera_id = settings.CAMERA_ID
        self.topic = "edge_events"
        
        # Configure Kafka Producer
        conf = {
            'bootstrap.servers': settings.KAFKA_BROKER,
            'client.id': f'vigil-edge-{self.camera_id}',
            'message.timeout.ms': 5000, # Fail fast, drop message if network is down
        }
        self.producer = Producer(conf)
        logger.info(f"Kafka Producer initialized for broker {settings.KAFKA_BROKER}")

    def _delivery_callback(self, err, msg):
        """Called once for each message produced to indicate delivery result."""
        if err is not None:
            # We explicitly drop the message here instead of writing to disk
            logger.error(f"Message delivery failed: {err}. Message dropped to preserve edge storage.")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def send_intrusion_confirmed(self, track_id: str, obj_class: str, trigger_type: str, 
                                 zone_id: str, dwell_sec: float, bbox: list, 
                                 confidence: float, frame):
        """Emits an intrusion event with an attached base64 snapshot."""
        # Encode snapshot to base64 JPEG
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        snapshot_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Schema matches ARCHITECTURE.md 5.2
        payload = {
            "type": "intrusion_confirmed",
            "camera_id": self.camera_id,
            "track_id": track_id,
            "object_class": obj_class,
            "trigger_type": trigger_type,
            "zone_id": zone_id,
            "dwell_seconds": round(dwell_sec, 2),
            "bbox": bbox,
            "trajectory": [], # Left empty for Phase 1.5; can track history in state machine later
            "confidence": round(float(confidence), 2),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "snapshot_b64": snapshot_b64
        }
        
        self.producer.produce(
            self.topic, 
            key=self.camera_id, 
            value=json.dumps(payload), 
            callback=self._delivery_callback
        )
        self.producer.poll(0)
        logger.warning(f"Sent INTRUSION_CONFIRMED for {track_id}")

    def send_track_resolved(self, track_id: str, reason: str):
        """Emits a track resolution event for auto-clearing incidents."""
        # Schema matches ARCHITECTURE.md 5.4
        payload = {
            "type": "track_resolved",
            "camera_id": self.camera_id,
            "track_id": track_id,
            "reason": reason,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        }
        self.producer.produce(self.topic, key=self.camera_id, value=json.dumps(payload), callback=self._delivery_callback)
        self.producer.poll(0)
        logger.info(f"Sent TRACK_RESOLVED for {track_id}")

    def send_heartbeat(self, active_tracks: int, fps: float, config_version: str):
        """Emits periodic health and state telemetry."""
        # Schema matches ARCHITECTURE.md 5.3
        payload = {
            "type": "heartbeat",
            "camera_id": self.camera_id,
            "device_status": "online",
            "active_tracks": active_tracks,
            "fps": round(fps, 1),
            "cpu_temp_c": 0.0, # Placeholder until hardware temp reads are added
            "config_version": config_version,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        }
        self.producer.produce(self.topic, key=self.camera_id, value=json.dumps(payload), callback=self._delivery_callback)
        self.producer.poll(0)

    def close(self):
        self.producer.flush()