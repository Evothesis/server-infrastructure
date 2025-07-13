# Create new file: api/app/validation_schemas.py

from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

class EventData(BaseModel):
    """Individual event data with size limits"""
    class Config:
        # Pydantic v2 fix: renamed from max_anystr_length
        str_max_length = 10000
        
    # Allow any additional fields but validate size
    def __init__(self, **data):
        # Convert to JSON and check size
        json_str = json.dumps(data)
        if len(json_str.encode('utf-8')) > 10000:
            raise ValueError("Individual event exceeds 10KB limit")
        super().__init__(**data)

class IndividualEvent(BaseModel):
    """Single event within a batch"""
    eventType: str = Field(..., max_length=100)
    timestamp: Optional[str] = Field(None, max_length=50)
    eventData: Optional[Dict[str, Any]] = None
    
    @validator('eventType')
    def validate_event_type(cls, v):
        if not v or not v.strip():
            raise ValueError('eventType cannot be empty')
        return v.strip()
    
    @validator('eventData')
    def validate_event_data_size(cls, v):
        if v is None:
            return v
        # Check serialized size
        json_str = json.dumps(v)
        if len(json_str.encode('utf-8')) > 10000:
            raise ValueError('eventData exceeds 10KB limit')
        return v

class CollectionRequest(BaseModel):
    """Main collection request validation"""
    eventType: str = Field(..., max_length=100)
    sessionId: Optional[str] = Field(None, max_length=200)
    visitorId: Optional[str] = Field(None, max_length=200)
    siteId: Optional[str] = Field(None, max_length=200)
    timestamp: Optional[str] = Field(None, max_length=50)
    url: Optional[str] = Field(None, max_length=2000)
    path: Optional[str] = Field(None, max_length=1000)
    
    # Batch event handling
    events: Optional[List[IndividualEvent]] = Field(None, max_items=100)
    
    # Additional event data
    eventData: Optional[Dict[str, Any]] = None
    batchMetadata: Optional[Dict[str, Any]] = None
    
    @validator('events')
    def validate_batch_size(cls, v):
        if v is not None and len(v) > 100:
            raise ValueError('Batch cannot exceed 100 events')
        return v
    
    @validator('url')
    def validate_url_format(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('eventData')
    def validate_event_data_size(cls, v):
        if v is None:
            return v
        json_str = json.dumps(v)
        if len(json_str.encode('utf-8')) > 10000:
            raise ValueError('eventData exceeds 10KB limit')
        return v

class ClientIdPath(BaseModel):
    """Path parameter validation for client_id"""
    # Pydantic v2 fix: renamed from regex to pattern
    client_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$', max_length=100)
    
    @validator('client_id')
    def validate_client_id_format(cls, v):
        if not v or len(v) < 3:
            raise ValueError('client_id must be at least 3 characters')
        return v