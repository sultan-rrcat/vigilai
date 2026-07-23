from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from uuid import UUID 
import hashlib
import json

from core.db import get_db
from db.models import Zone, Camera, Incident
from schemas.geometry import ZoneCreate, ZoneResponse

router = APIRouter(prefix="/cameras/{camera_id}/zones", tags=["Zones"])

@router.get("/", response_model=list[ZoneResponse])
async def get_zones(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    """List all zones for a specific camera."""
    result = await db.execute(select(Zone).filter(Zone.camera_id == camera_id))
    return result.scalars().all()

@router.post("/", response_model=ZoneResponse)
async def create_zone(camera_id: UUID, zone_in: ZoneCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new restricted zone for a specific camera."""
    cam_result = await db.execute(select(Camera).filter(Camera.id == camera_id))
    camera = cam_result.scalars().first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    new_zone = Zone(
        camera_id = camera_id,
        name = zone_in.name,
        polygon=zone_in.polygon,
        min_dwell_seconds=zone_in.min_dwell_seconds
    )
    
    db.add(new_zone)
    await db.commit()
    await db.refresh(new_zone)
    return new_zone

@router.delete("/")
async def delete_all_zones(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    """Deletes all saved zones for a specific camera while preserving historical incidents."""
    
    # 1. Create a subquery of zone IDs to detach
    zones_to_delete_stmt = select(Zone.id).filter(Zone.camera_id == camera_id).scalar_subquery()
    
    # 2. Detach incidents from these zones by setting zone_id to NULL
    await db.execute(
        update(Incident)
        .where(Incident.zone_id.in_(zones_to_delete_stmt))
        .values(zone_id=None)
    )
    
    # 3. Now it is safe to delete the zones
    delete_result = await db.execute(
        delete(Zone).where(Zone.camera_id == camera_id)
    )
    
    await db.commit()
    
    return {"message": f"Deleted {delete_result.rowcount} zones for camera {camera_id}"}