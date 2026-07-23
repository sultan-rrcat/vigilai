import logging
import asyncio
from datetime import datetime, timedelta
from threading import Thread
from sqlalchemy import select

from core.db import SessionLocal
from db.models import Camera
from core.websocket import manager

logger = logging.getLogger(__name__)

class CameraHealthWorker:
    def __init__(self, loop, timeout_seconds: int = 15):
        self.timeout_seconds = timeout_seconds
        self.loop = loop
        self.running = True
        self.worker_thread = Thread(target=self._run_thread, daemon=True)

    def start(self):
        logger.info(f"Starting Camera Health Worker (Timeout: {self.timeout_seconds}s)")
        self.worker_thread.start()

    def stop(self):
        self.running = False

    def _run_thread(self):
        """Synchronous wrapper to launch the async loop inside the thread."""
        asyncio.run(self._async_poll_health())

    async def _async_poll_health(self):
        while self.running:
            async with SessionLocal() as db:
                try:
                    cutoff_time = datetime.utcnow() - timedelta(seconds=self.timeout_seconds)
                    
                    result = await db.execute(
                        select(Camera).filter(
                            Camera.status == "online",
                            Camera.last_heartbeat <= cutoff_time
                        )
                    )
                    stale_cameras = result.scalars().all()

                    for cam in stale_cameras:
                        cam.status = "offline"
                        logger.warning(f"⚠️ Camera {cam.name} ({cam.id}) went OFFLINE! No heartbeat in {self.timeout_seconds}s.")
                        
                        if self.loop:
                            ws_payload = {
                                "type": "camera_update",
                                "data": {
                                    "id": str(cam.id),
                                    "status": "offline"
                                }
                            }
                            asyncio.run_coroutine_threadsafe(manager.broadcast(ws_payload), self.loop)
                    
                    if stale_cameras:
                        await db.commit()

                except Exception as e:
                    logger.error(f"Error in Camera Health Worker loop: {e}", exc_info=True)
                    await db.rollback()

            # Sleep asynchronously to not block the thread's event loop
            await asyncio.sleep(5)