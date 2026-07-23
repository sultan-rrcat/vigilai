from pydantic import BaseModel, Field, field_validator
from typing import List
from uuid import UUID

# pydantic enforces type safety, data validation & parsing

class Point(BaseModel):
    x : float = Field(..., ge=0.0, le=1.0) # enforces required field
    y : float = Field(..., ge=0.0, le=1.0)

class ZoneCreate(BaseModel):
    name: str
    polygon: List[List[float]]
    min_dwell_seconds: float = 2.0

    @field_validator('polygon')
    def validate_polygon(cls, v):
        if len(v) < 3:
            raise ValueError('A zone polygon must have at least 3 points.')
        for point in v:
            if len(point) != 2:
                raise ValueError('Each point must be an [x, y] pair.')
            if not (0.0 <= point[0] <= 1.0 and 0.0 <= point[1] <= 1.0):
                raise ValueError('Coordinates must be normalized between 0.0 and 1.0')
        return v

class ZoneResponse(ZoneCreate):
    id : UUID
    camera_id : UUID
    
    class Config:
        from_attributes = True