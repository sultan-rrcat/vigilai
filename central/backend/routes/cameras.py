from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
from uuid import UUID
from core.db import get_db
from db.models import Camera
from schemas.camera import CameraCreate, CameraResponse
import base64
import os

router = APIRouter(prefix="/cameras", tags=["Cameras"])

# 1. Create the schema for the upload payload
class ReferenceImageUpload(BaseModel):
    snapshot_b64: str

@router.get("", response_model=List[CameraResponse])
async def get_all_cameras(db: AsyncSession = Depends(get_db)):
    """Fetches all registered edge cameras from the database."""
    # Use select() and await the execution
    result = await db.execute(select(Camera).order_by(Camera.created_at.desc()))
    # .scalars() pulls the Camera objects out of the result rows
    return result.scalars().all()

@router.post("", response_model=CameraResponse)
async def add_camera(camera_in: CameraCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new edge camera. It defaults to 'offline' until the edge node sends a heartbeat."""
    new_camera = Camera(
        name=camera_in.name,
        location=camera_in.location,
        rtsp_url=camera_in.rtsp_url,
        status="offline" 
    )
    # db.add() is synchronous (it just modifies local session state)
    db.add(new_camera)
    
    # Committing and refreshing require database calls, so they must be awaited
    await db.commit()
    await db.refresh(new_camera)
    
    return new_camera

@router.delete("/{camera_id}")
async def delete_camera(camera_id: UUID, db: AsyncSession = Depends(get_db)):
    """Deletes a camera and its associated data from the system."""
    result = await db.execute(select(Camera).filter(Camera.id == camera_id))
    camera = result.scalars().first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    await db.delete(camera)
    await db.commit()
    
    return {"message": f"Camera {camera_id} deleted successfully"}

@router.post("/{camera_id}/reference")
async def upload_reference_image(camera_id: UUID, payload: ReferenceImageUpload, db: AsyncSession = Depends(get_db)):
    print(">>> upload_reference_image called")
    """Receives a base64 encoded frame from the edge node and saves it as the reference image."""
    result = await db.execute(select(Camera).filter(Camera.id == camera_id))
    camera = result.scalars().first()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        image_data = base64.b64decode(payload.snapshot_b64)
        
        # Overwrite the same file so we always have the latest view when the edge node restarts
        filepath = os.path.join(os.getcwd(), "camera_references", f"{camera_id}.jpg")
        with open(filepath, "wb") as f:
            f.write(image_data)
            
        return {"message": "Reference image updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")