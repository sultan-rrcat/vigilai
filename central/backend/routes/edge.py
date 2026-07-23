from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import hashlib
import json

from core.db import get_db
from db.models import Camera, Zone, Tripwire

router = APIRouter(prefix="/edge", tags=["Edge Sync"])


@router.get("/{camera_id}/config")
async def get_edge_config(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Called by the edge node to pull its current zones and tripwires.
    Generates a dynamic config_version hash so the edge knows when to reload.
    """
    # Fetch camera
    cam_result = await db.execute(select(Camera).filter(Camera.id == camera_id))
    camera = cam_result.scalars().first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not registered.")

    # Fetch active zones
    zones_result = await db.execute(
        select(Zone).filter(Zone.camera_id == camera_id, Zone.enabled == True)
    )
    zones = zones_result.scalars().all()

    # Fetch active tripwires
    tripwires_result = await db.execute(
        select(Tripwire).filter(Tripwire.camera_id == camera_id, Tripwire.enabled == True)
    )
    tripwires = tripwires_result.scalars().all()

    # format the payload
    zones_payload = [
        {
            "id": str(z.id),
            "name": z.name,
            "polygon": z.polygon,
            "min_dwell_seconds": float(z.min_dwell_seconds),
        }
        for z in zones
    ]

    tripwires_payload = [
        {
            "id": str(t.id),
            "name": t.name,
            "line": t.line,
            "watched_direction": t.watched_direction,
        }
        for t in tripwires
    ]

    # Hash the payload to generate a unique config_version
    # If a zone is added/edited/deleted, this hash changes, triggering the edge to reload
    config_string = json.dumps(
        {"z": zones_payload, "t": tripwires_payload}, sort_keys=True
    )
    config_version = hashlib.md5(config_string.encode("utf-8")).hexdigest()[:8]

    return {
        "config_version": config_version,
        "min_dwell_seconds": 2.0,  # Default global fallback
        "track_ttl_seconds": 5.0,
        "zones": zones_payload,
        "tripwires": tripwires_payload,
    }