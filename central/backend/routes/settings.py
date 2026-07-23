from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from db.models import SystemSettings
from schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

async def get_or_create_settings(db: AsyncSession) -> SystemSettings:
    """Helper to ensure the singleton settings row always exists."""
    result = await db.execute(select(SystemSettings).filter(SystemSettings.id == 1))
    settings = result.scalars().first()
    
    if not settings:
        settings = SystemSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings

@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Fetch global system configuration."""
    return await get_or_create_settings(db)

@router.put("", response_model=SettingsResponse)
async def update_settings(settings_in: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    """Update global system configuration."""
    settings = await get_or_create_settings(db)
    
    settings.escalation_timeout_sec = settings_in.escalation_timeout_sec
    settings.webhook_url = settings_in.webhook_url
    settings.retention_days = settings_in.retention_days
    
    await db.commit()
    await db.refresh(settings)
    return settings