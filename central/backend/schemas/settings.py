# central/backend/schemas/settings.py
from pydantic import BaseModel
from typing import Optional

class SettingsUpdate(BaseModel):
    escalation_timeout_sec: int
    webhook_url: Optional[str] = None
    retention_days: int

class SettingsResponse(SettingsUpdate):
    pass
    
    class Config:
        from_attributes = True