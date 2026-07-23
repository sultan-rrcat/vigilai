from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from core.db import get_db
from db.models import Incident

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.get("")
async def get_incidents(
    status: str = Query("active,escalated", description="Comma-separated list of statuses"), 
    db: AsyncSession = Depends(get_db)
):
    """Fetch incidents filtered by status (supports multiple statuses)."""
    status_list = [s.strip() for s in status.split(",")]
    
    result = await db.execute(
        select(Incident).filter(Incident.status.in_(status_list)).order_by(Incident.created_at.desc())
    )
    return result.scalars().all()

@router.post("/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Operator explicitly acknowledges an alarm, preventing escalation."""
    result = await db.execute(select(Incident).filter(Incident.id == incident_id))
    incident = result.scalars().first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    if incident.status not in ["active", "escalated"]:
        raise HTTPException(status_code=400, detail=f"Cannot acknowledge incident in '{incident.status}' state")
        
    incident.status = "acknowledged"
    await db.commit()
    
    return {"message": "Incident acknowledged", "incident_id": incident_id}

@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Operator manually resolves an incident."""
    result = await db.execute(select(Incident).filter(Incident.id == incident_id))
    incident = result.scalars().first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    incident.status = "resolved"
    await db.commit()
    
    return {"message": "Incident resolved", "incident_id": incident_id}