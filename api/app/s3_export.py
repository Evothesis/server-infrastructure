import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from io import StringIO
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import EventLog

logger = logging.getLogger(__name__)

class S3ExportConfig:
    """Configuration for S3 export operations (raw and processed buckets)"""
    
    def __init__(self):
        # Raw S3 configuration
        self.raw_bucket = os.getenv("RAW_S3_BUCKET")
        self.raw_access_key = os.getenv("RAW_S3_ACCESS_KEY")
        self.raw_secret_key = os.getenv("RAW_S3_SECRET_KEY")
        self.raw_region = os.getenv("RAW_S3_REGION", "us-east-1")
        
        # Processed S3 configuration
        self.processed_bucket = os.getenv("PROCESSED_S3_BUCKET")
        self.processed_access_key = os.getenv("PROCESSED_S3_ACCESS_KEY")
        self.processed_secret_key = os.getenv("PROCESSED_S3_SECRET_KEY")
        self.processed_region = os.getenv("PROCESSED_S3_REGION", "us-east-1")
        
        # Export configuration
        self.export_format = "json"  # JSON only for MVP
        self.export_schedule = "1min"  # 1-minute intervals
        self.batch_size = int(os.getenv("EXPORT_BATCH_SIZE", "10000"))
        
        # Validation
        self.validate_config()
    
    def validate_config(self):
        """Validate configuration completeness"""
        errors = []
        
        if not self.raw_bucket:
            errors.append("RAW_S3_BUCKET is required")
        
        if not self.processed_bucket:
            errors.append("PROCESSED_S3_BUCKET is required")
        
        if self.batch_size <= 0:
            errors.append("EXPORT_BATCH_SIZE must be positive")
        
        if errors:
            raise ValueError(f"S3 Export configuration errors: {', '.join(errors)}")
    
    def get_raw_s3_client(self):
        """Get S3 client for raw bucket"""
        if self.raw_access_key and self.raw_secret_key:
            return boto3.client(
                's3',
                aws_access_key_id=self.raw_access_key,
                aws_secret_access_key=self.raw_secret_key,
                region_name=self.raw_region
            )
        else:
            # Use default credentials (IAM role, profile, etc.)
            return boto3.client('s3', region_name=self.raw_region)
    
    def get_processed_s3_client(self):
        """Get S3 client for processed bucket"""
        if self.processed_access_key and self.processed_secret_key:
            return boto3.client(
                's3',
                aws_access_key_id=self.processed_access_key,
                aws_secret_access_key=self.processed_secret_key,
                region_name=self.processed_region
            )
        else:
            # Use default credentials (IAM role, profile, etc.)
            return boto3.client('s3', region_name=self.processed_region)

class RawDataExporter:
    """Raw data export functionality for MVP pipeline"""
    
    def __init__(self, config: S3ExportConfig):
        self.config = config
        self.raw_s3 = config.get_raw_s3_client()
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    def export_raw_events(self, db: Session) -> Dict[str, Any]:
        """
        Export unprocessed events to raw S3 bucket
        Main entry point for 1-minute scheduled exports
        """
        try:
            # Get unprocessed events
            events = self._get_unprocessed_events(db)
            
            if not events:
                return {
                    "status": "success",
                    "message": "No unprocessed events to export",
                    "events_exported": 0,
                    "export_time": datetime.now(timezone.utc).isoformat()
                }
            
            # Prepare raw export data
            export_data = self._prepare_raw_export_data(events)
            
            # Upload to raw S3 with retry logic
            upload_result = self._upload_to_raw_s3_with_retry(export_data)
            
            if upload_result["success"]:
                # Mark events as processed (will be updated in Task 1.2 for raw_exported_at)
                event_ids = [event.id for event in events]
                self._mark_events_raw_exported(db, event_ids)
                
                return {
                    "status": "success",
                    "message": f"Exported {len(events)} events to raw S3",
                    "events_exported": len(events),
                    "export_time": datetime.now(timezone.utc).isoformat(),
                    "s3_key": upload_result["key"],
                    "s3_size_bytes": upload_result["size_bytes"]
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to upload to raw S3: {upload_result['error']}",
                    "events_exported": 0,
                    "export_time": datetime.now(timezone.utc).isoformat()
                }
            
        except Exception as e:
            logger.error(f"Raw export failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Raw export failed: {str(e)}",
                "events_exported": 0,
                "export_time": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_unprocessed_events(self, db: Session) -> List[EventLog]:
        """Get events that haven't been exported to raw S3"""
        # Use raw_exported_at IS NULL for precise raw export tracking
        query = db.query(EventLog).filter(EventLog.raw_exported_at.is_(None))
        
        # Order by created_at for consistent processing order
        query = query.order_by(EventLog.created_at)
        
        # Limit batch size for efficient processing
        return query.limit(self.config.batch_size).all()
    
    def _prepare_raw_export_data(self, events: List[EventLog]) -> Dict[str, Any]:
        """Prepare raw event data for S3 export"""
        export_metadata = {
            "export_id": f"raw_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "export_time": datetime.now(timezone.utc).isoformat(),
            "event_count": len(events),
            "format": "json",
            "pipeline_stage": "raw"
        }
        
        if events:
            export_metadata["time_range"] = {
                "start": events[0].created_at.isoformat(),
                "end": events[-1].created_at.isoformat()
            }
        
        # Convert events to raw format (minimal processing)
        event_records = []
        for event in events:
            record = {
                "id": event.id,
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "session_id": event.session_id,
                "visitor_id": event.visitor_id,
                "site_id": event.site_id,
                "timestamp": event.timestamp.isoformat(),
                "url": event.url,
                "path": event.path,
                "user_agent": event.user_agent,
                "ip_address": str(event.ip_address) if event.ip_address else None,
                "client_id": event.client_id,  # Critical for pipeline processing
                "created_at": event.created_at.isoformat(),
                "raw_event_data": event.raw_event_data
            }
            event_records.append(record)
        
        return {
            "export_metadata": export_metadata,
            "events": event_records
        }
    
    def _upload_to_raw_s3_with_retry(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload to raw S3 bucket with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = self._upload_to_raw_s3(export_data)
                if result["success"]:
                    return result
                last_error = result.get("error", "Unknown error")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Raw S3 upload attempt {attempt + 1} failed: {last_error}")
            
            # Exponential backoff for retries
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                time.sleep(delay)
        
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} attempts: {last_error}"
        }
    
    def _upload_to_raw_s3(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload export data to raw S3 bucket"""
        try:
            # Generate S3 key with date partitioning for efficient processing
            timestamp = datetime.now(timezone.utc)
            key = f"raw-events/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{export_data['export_metadata']['export_id']}.json"
            
            # Prepare JSON content
            content = json.dumps(export_data, indent=2, default=str)
            content_bytes = content.encode('utf-8')
            
            # Upload to raw S3
            self.raw_s3.put_object(
                Bucket=self.config.raw_bucket,
                Key=key,
                Body=content_bytes,
                ContentType="application/json",
                Metadata={
                    'export_id': export_data['export_metadata']['export_id'],
                    'event_count': str(export_data['export_metadata']['event_count']),
                    'pipeline_stage': 'raw',
                    'format': 'json'
                }
            )
            
            logger.info(f"Successfully uploaded {len(export_data['events'])} events to raw S3: {key}")
            
            return {
                "success": True,
                "bucket": self.config.raw_bucket,
                "key": key,
                "size_bytes": len(content_bytes)
            }
            
        except ClientError as e:
            error_msg = f"S3 upload failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error during raw S3 upload: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _mark_events_raw_exported(self, db: Session, event_ids: List[int]):
        """
        Mark events as raw exported using raw_exported_at timestamp
        """
        try:
            export_time = datetime.now(timezone.utc)
            db.query(EventLog).filter(EventLog.id.in_(event_ids)).update(
                {"raw_exported_at": export_time},
                synchronize_session=False
            )
            db.commit()
            logger.info(f"Marked {len(event_ids)} events as raw exported")
        except Exception as e:
            logger.error(f"Failed to mark events as raw exported: {str(e)}")
            db.rollback()
            raise
    
    def get_export_status(self, db: Session) -> Dict[str, Any]:
        """Get raw export pipeline status"""
        try:
            # Count events by raw export status
            total_events = db.query(EventLog).count()
            raw_exported_events = db.query(EventLog).filter(EventLog.raw_exported_at.isnot(None)).count()
            pending_events = total_events - raw_exported_events
            
            # Get latest raw export
            latest_raw_exported = db.query(EventLog).filter(
                EventLog.raw_exported_at.isnot(None)
            ).order_by(EventLog.raw_exported_at.desc()).first()
            
            return {
                "total_events": total_events,
                "raw_exported_events": raw_exported_events,
                "pending_events": pending_events,
                "latest_raw_export": latest_raw_exported.raw_exported_at.isoformat() if latest_raw_exported else None,
                "raw_bucket": self.config.raw_bucket,
                "export_format": self.config.export_format,
                "batch_size": self.config.batch_size,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get export status: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

def create_raw_data_exporter() -> RawDataExporter:
    """Factory function to create RawDataExporter with configuration"""
    config = S3ExportConfig()
    return RawDataExporter(config)