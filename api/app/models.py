from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.sql import func
from .database import Base
import uuid

class EventLog(Base):
    __tablename__ = "events_log"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(100), index=True)
    visitor_id = Column(String(100), index=True)
    site_id = Column(String(100), index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    url = Column(Text)
    path = Column(String(500))
    user_agent = Column(Text)
    ip_address = Column(INET)
    raw_event_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    client_id = Column(String(255), index=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # ADDED: For bulk processing
    export_status = Column(String(20), default='pending', index=True)  # ADDED: For S3 export tracking
    
    def __repr__(self):
        return f"<EventLog(id={self.id}, event_type='{self.event_type}', session_id='{self.session_id}', client_id='{self.client_id}')>"