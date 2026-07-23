from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    rtsp_url: Optional[str] = None

class CameraResponse(CameraCreate):
    id: UUID
    status: str
    last_heartbeat: Optional[datetime] = None

    class Config:
        from_attributes = True