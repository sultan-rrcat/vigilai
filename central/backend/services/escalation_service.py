import asyncio
from datetime import datetime, timedelta
from threading import Thread
import httpx
from sqlalchemy import select

from db.models import Incident, Escalation, SystemSettings
from core.logging import setup_logging
from core.db import SessionLocal
from core.websocket import manager
from core.time_utils import to_iso_z

logger = setup_logging()

class EscalationWorker:
    def __init__(self, timeout_seconds: int = 15, loop = None):
        self.loop = loop
        self.timeout_seconds = timeout_seconds
        self.running = True
        self.worker_thread = Thread(target=self._run_thread, daemon=True)

    def start(self):
        logger.info(f"Starting Escalation Worker (Default Timeout: {self.timeout_seconds}s)")
        self.worker_thread.start()

    def stop(self):
        self.running = False

    def _run_thread(self):
        asyncio.run(self._async_poll_incidents())

    async def _get_settings(self, db):
        result = await db.execute(select(SystemSettings).filter(SystemSettings.id == 1))
        return result.scalars().first()

    async def _send_webhook(self, url: str, payload: dict):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status() 
                logger.info(f"Webhook successfully delivered to {url}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to deliver webhook to {url}. Error: {str(e)}")

    async def _async_poll_incidents(self):
        while self.running:
            async with SessionLocal() as db:
                try:
                    settings = await self._get_settings(db)
                    current_timeout = settings.escalation_timeout_sec if settings else self.timeout_seconds
                    webhook_url = settings.webhook_url if settings else None

                    cutoff_time = datetime.utcnow() - timedelta(seconds=current_timeout)
                    
                    result = await db.execute(
                        select(Incident).filter(
                            Incident.status == "active",
                            Incident.created_at <= cutoff_time
                        )
                    )
                    stale_incidents = result.scalars().all()

                    for incident in stale_incidents:
                        incident.status = "escalated"
                        
                        escalation_record = Escalation(
                            incident_id=incident.id,
                            escalated_to="Default Security Team",
                            channel="System Log" if not webhook_url else "Webhook"
                        )
                        db.add(escalation_record)
                        
                        logger.critical(
                            f"🚨 ESCALATION TRIGGERED: Incident {incident.id} "
                            f"(Track: {incident.track_id}) was unacknowledged for >{current_timeout}s!"
                        )
                        
                        if webhook_url and self.loop:
                            webhook_payload = {
                                "event": "intrusion_escalated",
                                "incident_id": str(incident.id),
                                "camera_id": str(incident.camera_id),
                                "track_id": incident.track_id,
                                "object_class": incident.object_class,
                                "timestamp": to_iso_z(datetime.utcnow())
                            }
                            
                            asyncio.run_coroutine_threadsafe(
                                self._send_webhook(webhook_url, webhook_payload), 
                                self.loop
                            )
                    
                    if stale_incidents:
                        await db.commit()

                        if self.loop:
                            for incident in stale_incidents:
                                ws_payload = {
                                    "type": "incident_update",
                                    "data": {
                                        "id": str(incident.id),
                                        "camera_id": str(incident.camera_id),
                                        "track_id": incident.track_id,
                                        "object_class": incident.object_class,
                                        "trigger_type": incident.trigger_type,
                                        "snapshot_path": incident.snapshot_path,
                                        "confidence": float(incident.confidence) if incident.confidence else 0,
                                        "status": incident.status,
                                        "created_at": to_iso_z(incident.created_at),
                                    },
                                }

                                asyncio.run_coroutine_threadsafe(
                                    manager.broadcast(ws_payload),
                                    self.loop,
                                )

                except Exception as e:
                    logger.error(f"Error in Escalation Worker loop: {e}", exc_info=True)
                    await db.rollback()

            await asyncio.sleep(2)