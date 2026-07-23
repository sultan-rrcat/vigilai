import uuid
from sqlalchemy import Integer, Column, String, Boolean, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.db import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location = Column(String)
    rtsp_url = Column(String)
    status = Column(String, default="offline")
    last_heartbeat = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships let you easily access related data (e.g., camera.zones)
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    tripwires = relationship("Tripwire", back_populates="camera", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="camera")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    polygon = Column(JSONB, nullable=False) # Normalized coords [[x,y], ...]
    min_dwell_seconds = Column(Numeric, default=2.0)
    active_schedule = Column(JSONB)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    camera = relationship("Camera", back_populates="zones")
    incidents = relationship("Incident", back_populates="zone")

class Tripwire(Base):
    __tablename__ = "tripwires"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    line = Column(JSONB, nullable=False)
    watched_direction = Column(String, nullable=False) # "a_to_b" | "b_to_a" | "both"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    camera = relationship("Camera", back_populates="tripwires")
    incidents = relationship("Incident", back_populates="tripwire")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id"))
    track_id = Column(String, nullable=False)
    object_class = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    tripwire_id = Column(UUID(as_uuid=True), ForeignKey("tripwires.id"), nullable=True)
    snapshot_path = Column(String)
    confidence = Column(Numeric)
    status = Column(String, default="active") # active / acknowledged / escalated / resolved
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    camera = relationship("Camera", back_populates="incidents")
    zone = relationship("Zone", back_populates="incidents")
    tripwire = relationship("Tripwire", back_populates="incidents")
    escalations = relationship("Escalation", back_populates="incident", cascade="all, delete-orphan")

class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"))
    escalated_to = Column(String)
    channel = Column(String)
    escalated_at = Column(DateTime(timezone=True), server_default=func.now())

    incident = relationship("Incident", back_populates="escalations")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="operator")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    channel = Column(String)
    address = Column(String)
    priority = Column(Numeric, default=1)
    
class SystemSettings(Base):
    __tablename__ = "system_settings"

    # We will enforce a single row (id=1) for global settings
    id = Column(Integer, primary_key=True, index=True, default=1)
    escalation_timeout_sec = Column(Integer, default=15)
    webhook_url = Column(String, nullable=True)
    retention_days = Column(Integer, default=30)
    
