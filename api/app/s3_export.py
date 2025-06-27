import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from io import StringIO, BytesIO
import polars as pl
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import EventLog

logger = logging.getLogger(__name__)

class S3ExportConfig:
    """Configuration for S3 export operations"""
    
    def __init__(self):
        # Client S3 configuration
        self.client_bucket = os.getenv("CLIENT_S3_BUCKET")
        self.client_access_key = os.getenv("CLIENT_S3_ACCESS_KEY")
        self.client_secret_key = os.getenv("CLIENT_S3_SECRET_KEY")
        self.client_region = os.getenv("CLIENT_S3_REGION", "us-east-1")
        
        # Backup S3 configuration (for metering)
        self.backup_bucket = os.getenv("BACKUP_S3_BUCKET")
        self.backup_access_key = os.getenv("BACKUP_S3_ACCESS_KEY")
        self.backup_secret_key = os.getenv("BACKUP_S3_SECRET_KEY")
        self.backup_region = os.getenv("BACKUP_S3_REGION", "us-east-1")
        
        # Export configuration
        self.export_format = os.getenv("EXPORT_FORMAT", "json").lower()
        self.export_schedule = os.getenv("EXPORT_SCHEDULE", "hourly")
        self.site_id = os.getenv("SITE_ID", "default")
        
        # Validation
        self.validate_config()
    
    def validate_config(self):
        """Validate configuration completeness"""
        errors = []
        
        if not self.client_bucket:
            errors.append("CLIENT_S3_BUCKET is required")
        
        if self.export_format not in ["json", "csv", "parquet"]:
            errors.append(f"Invalid EXPORT_FORMAT: {self.export_format}")
        
        if errors:
            raise ValueError(f"S3 Export configuration errors: {', '.join(errors)}")
    
    def get_client_s3_client(self):
        """Get S3 client for client bucket"""
        if self.client_access_key and self.client_secret_key:
            return boto3.client(
                's3',
                aws_access_key_id=self.client_access_key,
                aws_secret_access_key=self.client_secret_key,
                region_name=self.client_region
            )
        else:
            # Use default credentials (IAM role, profile, etc.)
            return boto3.client('s3', region_name=self.client_region)
    
    def get_backup_s3_client(self):
        """Get S3 client for backup bucket"""
        if not self.backup_bucket:
            return None
            
        if self.backup_access_key and self.backup_secret_key:
            return boto3.client(
                's3',
                aws_access_key_id=self.backup_access_key,
                aws_secret_access_key=self.backup_secret_key,
                region_name=self.backup_region
            )
        else:
            # Use default credentials
            return boto3.client('s3', region_name=self.backup_region)

class S3Exporter:
    """Main S3 export functionality"""
    
    def __init__(self, config: S3ExportConfig):
        self.config = config
        self.client_s3 = config.get_client_s3_client()
        self.backup_s3 = config.get_backup_s3_client()
    
    def export_events(self, db: Session, since: Optional[datetime] = None, limit: int = 10000) -> Dict[str, Any]:
        """Export events to S3 buckets"""
        try:
            # Get events to export
            events = self._get_events_for_export(db, since, limit)
            
            if not events:
                return {
                    "status": "success",
                    "message": "No events to export",
                    "events_exported": 0,
                    "export_time": datetime.now(timezone.utc).isoformat()
                }
            
            # Generate export data
            export_data = self._prepare_export_data(events)
            
            # Export to client bucket
            client_upload_result = self._upload_to_s3(
                self.client_s3,
                self.config.client_bucket,
                export_data,
                "client"
            )
            
            # Export to backup bucket (if configured)
            backup_upload_result = None
            if self.backup_s3 and self.config.backup_bucket:
                backup_upload_result = self._upload_to_s3(
                    self.backup_s3,
                    self.config.backup_bucket,
                    export_data,
                    "backup"
                )
            
            # Update exported_at timestamps
            event_ids = [event.id for event in events]
            self._mark_events_exported(db, event_ids)
            
            return {
                "status": "success",
                "message": f"Exported {len(events)} events successfully",
                "events_exported": len(events),
                "export_time": datetime.now(timezone.utc).isoformat(),
                "client_upload": client_upload_result,
                "backup_upload": backup_upload_result,
                "format": self.config.export_format
            }
            
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Export failed: {str(e)}",
                "events_exported": 0,
                "export_time": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_events_for_export(self, db: Session, since: Optional[datetime], limit: int) -> List[EventLog]:
        """Get events that need to be exported"""
        query = db.query(EventLog).filter(EventLog.processed_at.is_(None))
        
        if since:
            query = query.filter(EventLog.created_at >= since)
        
        # Order by created_at for consistent export order
        query = query.order_by(EventLog.created_at)
        
        return query.limit(limit).all()
    
    def _prepare_export_data(self, events: List[EventLog]) -> Dict[str, Any]:
        """Prepare event data for export"""
        export_metadata = {
            "export_id": f"export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "export_time": datetime.now(timezone.utc).isoformat(),
            "event_count": len(events),
            "format": self.config.export_format,
            "site_id": self.config.site_id
        }
        
        if events:
            export_metadata["time_range"] = {
                "start": events[0].created_at.isoformat(),
                "end": events[-1].created_at.isoformat()
            }
        
        # Convert events to serializable format
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
                "created_at": event.created_at.isoformat(),
                "raw_event_data": event.raw_event_data
            }
            event_records.append(record)
        
        return {
            "export_metadata": export_metadata,
            "events": event_records
        }
    
    def _upload_to_s3(self, s3_client, bucket: str, export_data: Dict[str, Any], upload_type: str) -> Dict[str, Any]:
        """Upload export data to S3 bucket"""
        try:
            # Generate S3 key
            timestamp = datetime.now(timezone.utc)
            key = f"analytics/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{export_data['export_metadata']['export_id']}.{self.config.export_format}"
            
            # Prepare data based on format
            if self.config.export_format == "json":
                content = json.dumps(export_data, indent=2, default=str)
                content_type = "application/json"
                
            elif self.config.export_format == "csv":
                # Convert events to CSV using Polars
                df = pl.DataFrame(export_data['events'])
                csv_buffer = StringIO()
                df.write_csv(csv_buffer)
                content = csv_buffer.getvalue()
                content_type = "text/csv"
                
            elif self.config.export_format == "parquet":
                # Convert events to Parquet using Polars
                df = pl.DataFrame(export_data['events'])
                parquet_buffer = BytesIO()
                df.write_parquet(parquet_buffer)
                content = parquet_buffer.getvalue()
                content_type = "application/octet-stream"
            
            # Upload to S3
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'export_id': export_data['export_metadata']['export_id'],
                    'event_count': str(export_data['export_metadata']['event_count']),
                    'export_type': upload_type
                }
            )
            
            return {
                "success": True,
                "bucket": bucket,
                "key": key,
                "size_bytes": len(content),
                "upload_type": upload_type
            }
            
        except ClientError as e:
            logger.error(f"S3 upload failed for {upload_type}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "upload_type": upload_type
            }
        except Exception as e:
            logger.error(f"Unexpected error during {upload_type} upload: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "upload_type": upload_type
            }
    
    def _mark_events_exported(self, db: Session, event_ids: List[int]):
        """Mark events as exported"""
        try:
            export_time = datetime.now(timezone.utc)
            db.query(EventLog).filter(EventLog.id.in_(event_ids)).update(
                {"processed_at": export_time},
                synchronize_session=False
            )
            db.commit()
            logger.info(f"Marked {len(event_ids)} events as exported")
        except Exception as e:
            logger.error(f"Failed to mark events as exported: {str(e)}")
            db.rollback()
            raise
    
    def get_export_status(self, db: Session) -> Dict[str, Any]:
        """Get export pipeline status"""
        try:
            # Count events by status
            total_events = db.query(EventLog).count()
            exported_events = db.query(EventLog).filter(EventLog.processed_at.isnot(None)).count()
            pending_events = total_events - exported_events
            
            # Get latest export
            latest_exported = db.query(EventLog).filter(
                EventLog.processed_at.isnot(None)
            ).order_by(EventLog.processed_at.desc()).first()
            
            return {
                "total_events": total_events,
                "exported_events": exported_events,
                "pending_events": pending_events,
                "latest_export": latest_exported.processed_at.isoformat() if latest_exported else None,
                "export_format": self.config.export_format,
                "client_bucket": self.config.client_bucket,
                "backup_bucket": self.config.backup_bucket,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get export status: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

def create_s3_exporter() -> S3Exporter:
    """Factory function to create S3Exporter with configuration"""
    config = S3ExportConfig()
    return S3Exporter(config)