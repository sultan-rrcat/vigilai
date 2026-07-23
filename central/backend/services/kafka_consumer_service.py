import json
import uuid
from confluent_kafka import Consumer, KafkaError
from sqlalchemy import select
from core.config import settings
from core.db import SessionLocal
from db.models import Camera, Incident, Zone
from core.logging import setup_logging
from core.websocket import manager
from core.time_utils import to_iso_z
import base64
import os
from datetime import datetime
import asyncio

logger = setup_logging()

IMAGE_DIR = os.path.join(os.getcwd(), "incident_images")
os.makedirs(IMAGE_DIR, exist_ok=True)


class CoreEventConsumer:
    def __init__(self, loop=None):
        self.loop = loop
        self.topic = "edge_events"
        self.running = True

        conf = {
            "bootstrap.servers": settings.KAFKA_BROKER,
            "group.id": "vigil-core-ingestion",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
        self.consumer = Consumer(conf)
        logger.info(f"Kafka Ingestion Worker configured for broker: {settings.KAFKA_BROKER}")

    def stop(self):
        self.running = False

    def run(self):
        self.consumer.subscribe([self.topic])
        logger.info(f"Subscribed to topic: {self.topic}. Ingestion started...")

        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka partition error: {msg.error()}")
                        break

                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    msg_type = payload.get("type")

                    # Execute the asynchronous DB pipeline from the synchronous consumer loop
                    success = asyncio.run(self._process_message_transaction(msg_type, payload))
                    
                    if success:
                        self.consumer.commit(msg, asynchronous=False)

                except json.JSONDecodeError:
                    logger.error("Received bad message format (Non-JSON payload). Skipping.")

        except KeyboardInterrupt:
            logger.info("Ingestion loop stopped manually.")
        finally:
            self.consumer.close()

    async def _process_message_transaction(self, msg_type: str, payload: dict) -> bool:
        """Wraps the DB interaction to ensure commits and rollbacks happen asynchronously."""
        async with SessionLocal() as db:
            try:
                await self._process_message(db, msg_type, payload)
                await db.commit()
                return True
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to process message transaction: {e}", exc_info=True)
                return False

    async def _process_message(self, db, msg_type: str, payload: dict):
        camera_uuid = uuid.UUID(payload["camera_id"])

        if msg_type == "intrusion_confirmed":
            logger.warning(f"🚨 INTRUSION CONFIRMED received from Camera {camera_uuid} | Track: {payload['track_id']}")

            result = await db.execute(select(Zone).filter(Zone.camera_id == camera_uuid))
            zone = result.scalars().first()
            zone_id = zone.id if zone else None

            snapshot_path = None
            if "snapshot_b64" in payload and payload["snapshot_b64"]:
                try:
                    image_data = base64.b64decode(payload["snapshot_b64"])
                    filename = f"inc_{payload['track_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                    filepath = os.path.join(IMAGE_DIR, filename)

                    with open(filepath, "wb") as f:
                        f.write(image_data)

                    snapshot_path = f"incident_images/{filename}"
                except Exception as e:
                    logger.error(f"Failed to decode/save snapshot for track {payload['track_id']}: {e}")

            incident = Incident(
                camera_id=camera_uuid,
                track_id=payload["track_id"],
                object_class=payload["object_class"],
                trigger_type=payload["trigger_type"],
                zone_id=zone_id,
                confidence=payload["confidence"],
                snapshot_path=snapshot_path,
                status="active",
            )
            db.add(incident)
            await db.flush()

            if self.loop:
                ws_payload = {
                    "type": "new_incident",
                    "data": {
                        "id": str(incident.id),
                        "camera_id": str(incident.camera_id),
                        "track_id": incident.track_id,
                        "object_class": incident.object_class,
                        "trigger_type": incident.trigger_type,
                        "snapshot_path": incident.snapshot_path,
                        "confidence": float(incident.confidence) if incident.confidence else 0,
                        "status": incident.status,
                        "created_at": to_iso_z(datetime.utcnow()),
                    },
                }
                asyncio.run_coroutine_threadsafe(manager.broadcast(ws_payload), self.loop)

        elif msg_type == "heartbeat":
            result = await db.execute(select(Camera).filter(Camera.id == camera_uuid))
            camera = result.scalars().first()
            
            if camera:
                was_offline = camera.status != "online"
                camera.status = "online"
                camera.last_heartbeat = datetime.utcnow()
                
                if was_offline and self.loop:
                    logger.info(f"Camera {camera.name} is back ONLINE!")
                    ws_payload = {
                        "type": "camera_update",
                        "data": {"id": str(camera.id), "status": "online"},
                    }
                    asyncio.run_coroutine_threadsafe(manager.broadcast(ws_payload), self.loop)
                    
                logger.debug(f"💓 Heartbeat updated for camera {camera.name}")
            else:
                logger.warning(f"Heartbeat received for unregistered camera ID: {camera_uuid}")

        elif msg_type == "track_resolved":
            logger.info(f"✅ Track {payload['track_id']} has resolved from Camera {camera_uuid}")

            result = await db.execute(
                select(Incident).filter(
                    Incident.camera_id == camera_uuid,
                    Incident.track_id == payload["track_id"],
                    Incident.status == "active",
                )
            )
            incident = result.scalars().first()

            if incident:
                incident.status = "resolved"
                logger.info(f"Auto-cleared active incident for track: {payload['track_id']}")