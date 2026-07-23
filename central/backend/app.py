import threading
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.kafka_consumer_service import CoreEventConsumer
from services.escalation_service import EscalationWorker
from services.camera_health_service import CameraHealthWorker

from routes import incidents, zones, edge, websockets, cameras, settings

from core.db import Base, engine
from core.logging import setup_logging

import asyncio
import os

# Configure logger
logger = setup_logging()

# Instantiate our background workers
escalation_worker = None
consumer_worker = None
camera_health_worker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_worker
    
    # Run the synchronous create_all method safely inside an async connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Starting background workers...")
    
    # Grab the active event loop Uvicorn is running on
    main_loop = asyncio.get_running_loop()
    
    escalation_worker = EscalationWorker(
        timeout_seconds=15,
        loop=main_loop
    )
    escalation_worker.start()
    
    # Initialize and start the Camera Health Worker
    camera_health_worker = CameraHealthWorker(loop=main_loop, timeout_seconds=15)
    camera_health_worker.start()
    
    # Pass loop to consumer
    consumer_worker = CoreEventConsumer(loop=main_loop)
    consumer_thread = threading.Thread(target=consumer_worker.run, daemon=True)
    consumer_thread.start()
    
    yield
    
    logger.info("Shutting down core services...")
    escalation_worker.stop()
    consumer_worker.stop()
    camera_health_worker.stop()
    
app = FastAPI(title="Vigil AI Central Core", lifespan=lifespan)

# Allow the React frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the incident images directory so the frontend can load the snapshots directly
IMAGE_DIR = os.path.join(os.getcwd(), "incident_images")
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount("/incident_images", StaticFiles(directory=IMAGE_DIR), name="incident_images")

REF_DIR = os.path.join(os.getcwd(), "camera_references")
os.makedirs(REF_DIR, exist_ok=True)
app.mount("/camera_references", StaticFiles(directory=REF_DIR), name="camera_references")

# Register our routers
app.include_router(incidents.router)
app.include_router(zones.router)
app.include_router(edge.router)
app.include_router(websockets.router)
app.include_router(cameras.router)
app.include_router(settings.router)


@app.get("/health")
async def health_check():
    """Endpoint for Docker healthchecks."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8000
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)