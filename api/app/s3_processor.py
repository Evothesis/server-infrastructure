import json
import logging
import hashlib
import os
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError

from .s3_export import S3ExportConfig

logger = logging.getLogger(__name__)

class DataProcessor:
    """Data processing functionality for raw S3 → processed S3 pipeline"""
    
    def __init__(self, config: S3ExportConfig):
        self.config = config
        self.raw_s3 = config.get_raw_s3_client()
        self.processed_s3 = config.get_processed_s3_client()
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.pixel_management_url = os.getenv("PIXEL_MANAGEMENT_URL", "https://pixel-management-275731808857.us-central1.run.app")
        self.client_config_cache = {}  # Simple in-memory cache for client configs
    
    def process_raw_files(self) -> Dict[str, Any]:
        """
        Process unprocessed raw S3 files to client-partitioned processed S3
        Main entry point for S3-to-S3 processing
        """
        try:
            # Get unprocessed raw files from S3
            unprocessed_files = self._get_unprocessed_raw_files()
            
            if not unprocessed_files:
                return {
                    "status": "success",
                    "message": "No unprocessed raw files to process",
                    "files_processed": 0,
                    "process_time": datetime.now(timezone.utc).isoformat()
                }
            
            processed_count = 0
            processing_errors = []
            
            # Process each raw file
            for file_key in unprocessed_files:
                try:
                    result = self._process_single_file(file_key)
                    if result["success"]:
                        processed_count += 1
                        self._mark_file_processed(file_key)
                    else:
                        processing_errors.append(f"{file_key}: {result['error']}")
                except Exception as e:
                    processing_errors.append(f"{file_key}: {str(e)}")
                    logger.error(f"Failed to process file {file_key}: {str(e)}")
            
            return {
                "status": "success" if not processing_errors else "partial_success",
                "message": f"Processed {processed_count}/{len(unprocessed_files)} files",
                "files_processed": processed_count,
                "processing_errors": processing_errors,
                "process_time": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data processing failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Data processing failed: {str(e)}",
                "files_processed": 0,
                "process_time": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_unprocessed_raw_files(self) -> List[str]:
        """Get list of unprocessed raw files from S3"""
        try:
            # List files in raw bucket with raw-events/ prefix
            response = self.raw_s3.list_objects_v2(
                Bucket=self.config.raw_bucket,
                Prefix="raw-events/"
            )
            
            if 'Contents' not in response:
                return []
            
            # Filter for unprocessed files (no 'processed' metadata tag)
            unprocessed_files = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.json'):
                    # Check if file has been processed by looking for metadata
                    try:
                        head_response = self.raw_s3.head_object(
                            Bucket=self.config.raw_bucket,
                            Key=key
                        )
                        metadata = head_response.get('Metadata', {})
                        if not metadata.get('processed_at'):
                            unprocessed_files.append(key)
                    except ClientError:
                        # If we can't get metadata, treat as unprocessed
                        unprocessed_files.append(key)
            
            return unprocessed_files[:self.config.batch_size]  # Limit batch size
            
        except Exception as e:
            logger.error(f"Failed to list unprocessed raw files: {str(e)}")
            return []
    
    def _process_single_file(self, file_key: str) -> Dict[str, Any]:
        """Process a single raw file to client-partitioned processed files"""
        try:
            # Download raw file
            response = self.raw_s3.get_object(
                Bucket=self.config.raw_bucket,
                Key=file_key
            )
            raw_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Group events by client_id
            client_groups = self._group_events_by_client(raw_data['events'])
            
            # Process each client group
            upload_results = []
            for client_id, events in client_groups.items():
                processed_data = self._apply_privacy_filtering(client_id, events)
                upload_result = self._upload_processed_data(client_id, processed_data, file_key)
                upload_results.append(upload_result)
            
            # Check if all uploads succeeded
            failed_uploads = [r for r in upload_results if not r["success"]]
            if failed_uploads:
                return {
                    "success": False,
                    "error": f"Failed uploads: {[r['error'] for r in failed_uploads]}"
                }
            
            return {
                "success": True,
                "client_files_created": len(upload_results),
                "clients_processed": list(client_groups.keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _group_events_by_client(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group events by client_id for client-partitioned processing"""
        client_groups = {}
        for event in events:
            client_id = event.get('client_id', 'unknown')
            if client_id not in client_groups:
                client_groups[client_id] = []
            client_groups[client_id].append(event)
        return client_groups
    
    def _apply_privacy_filtering(self, client_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply client-specific privacy filtering to events"""
        # Get client privacy level
        privacy_level = self._get_client_privacy_level(client_id)
        
        # Apply privacy filtering based on client configuration
        filtered_events = []
        for event in events:
            filtered_event = self._filter_event_data(event, privacy_level)
            filtered_events.append(filtered_event)
        
        # Create processed data structure
        processed_metadata = {
            "process_id": f"processed_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "process_time": datetime.now(timezone.utc).isoformat(),
            "client_id": client_id,
            "event_count": len(filtered_events),
            "format": "json",
            "pipeline_stage": "processed",
            "privacy_level": privacy_level
        }
        
        return {
            "process_metadata": processed_metadata,
            "events": filtered_events
        }
    
    def _get_client_privacy_level(self, client_id: str) -> str:
        """Get privacy level for client from pixel-management service"""
        # Check cache first
        if client_id in self.client_config_cache:
            return self.client_config_cache[client_id].get('privacy_level', 'standard')
        
        try:
            # Fetch client config from pixel-management service
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.pixel_management_url}/api/v1/config/client/{client_id}")
                if response.status_code == 200:
                    config = response.json()
                    self.client_config_cache[client_id] = config
                    return config.get('privacy_level', 'standard')
                else:
                    logger.warning(f"Failed to get client config for {client_id}: HTTP {response.status_code}")
                    return 'standard'
        except Exception as e:
            logger.error(f"Error fetching client config for {client_id}: {str(e)}")
            return 'standard'
    
    def _filter_event_data(self, event: Dict[str, Any], privacy_level: str) -> Dict[str, Any]:
        """Apply privacy filtering to individual event based on privacy level"""
        filtered_event = event.copy()
        
        # Apply basic privacy filtering to raw_event_data
        if 'raw_event_data' in filtered_event:
            filtered_event['raw_event_data'] = self._redact_sensitive_data(
                filtered_event['raw_event_data']
            )
        
        # Apply client-specific filtering based on privacy level
        if privacy_level == 'gdpr':
            # GDPR compliance: Hash IP addresses, enhanced PII redaction
            if 'ip_address' in filtered_event and filtered_event['ip_address']:
                filtered_event['ip_address'] = self._hash_ip_address(filtered_event['ip_address'])
            
            # Redact user agent for GDPR
            if 'user_agent' in filtered_event:
                filtered_event['user_agent'] = self._anonymize_user_agent(filtered_event['user_agent'])
            
            # Add GDPR compliance markers
            filtered_event['gdpr_processed'] = True
            filtered_event['ip_anonymized'] = True
            
        elif privacy_level == 'hipaa':
            # HIPAA compliance: Enhanced redaction + audit trails
            if 'ip_address' in filtered_event and filtered_event['ip_address']:
                filtered_event['ip_address'] = self._hash_ip_address(filtered_event['ip_address'])
            
            if 'user_agent' in filtered_event:
                filtered_event['user_agent'] = self._anonymize_user_agent(filtered_event['user_agent'])
            
            # Enhanced redaction for HIPAA
            filtered_event = self._apply_hipaa_redaction(filtered_event)
            
            # Add HIPAA compliance markers
            filtered_event['hipaa_processed'] = True
            filtered_event['audit_required'] = True
            filtered_event['encryption_recommended'] = True
        
        # Standard: Keep all data (basic redaction only)
        return filtered_event
    
    def _hash_ip_address(self, ip_address: str) -> str:
        """Hash IP address for privacy compliance"""
        # Use SHA-256 hash with salt for IP anonymization
        salt = "securepixel_ip_salt"  # In production, use env variable
        combined = f"{ip_address}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]  # First 16 chars for readability
    
    def _anonymize_user_agent(self, user_agent: str) -> str:
        """Anonymize user agent for privacy compliance"""
        if not user_agent or len(user_agent) < 20:
            return "[ANONYMIZED]"
        
        # Keep browser family but remove specific version and system details
        if "Chrome" in user_agent:
            return "Chrome/[VERSION] (anonymized)"
        elif "Firefox" in user_agent:
            return "Firefox/[VERSION] (anonymized)"
        elif "Safari" in user_agent:
            return "Safari/[VERSION] (anonymized)"
        elif "Edge" in user_agent:
            return "Edge/[VERSION] (anonymized)"
        else:
            return "[BROWSER_ANONYMIZED]"
    
    def _apply_hipaa_redaction(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Apply enhanced HIPAA-specific redaction"""
        hipaa_sensitive_patterns = [
            'health', 'medical', 'patient', 'diagnosis', 'treatment',
            'prescription', 'medication', 'hospital', 'clinic', 'doctor',
            'nurse', 'physician', 'therapy', 'insurance', 'medicare',
            'medicaid', 'ssn', 'social_security', 'dob', 'birth_date'
        ]
        
        # Enhanced redaction for raw_event_data
        if 'raw_event_data' in event and isinstance(event['raw_event_data'], dict):
            event['raw_event_data'] = self._deep_redact_patterns(
                event['raw_event_data'], 
                hipaa_sensitive_patterns
            )
        
        return event
    
    def _deep_redact_patterns(self, data: Dict[str, Any], patterns: List[str]) -> Dict[str, Any]:
        """Deep redaction of sensitive patterns for HIPAA compliance"""
        if not isinstance(data, dict):
            return data
        
        redacted_data = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key matches HIPAA sensitive patterns
            is_hipaa_sensitive = any(pattern in key_lower for pattern in patterns)
            
            if is_hipaa_sensitive:
                redacted_data[key] = "[HIPAA_REDACTED]"
            elif isinstance(value, dict):
                redacted_data[key] = self._deep_redact_patterns(value, patterns)
            elif isinstance(value, str):
                # Check value content for sensitive patterns
                value_lower = value.lower()
                if any(pattern in value_lower for pattern in patterns):
                    redacted_data[key] = "[HIPAA_CONTENT_REDACTED]"
                else:
                    redacted_data[key] = value
            else:
                redacted_data[key] = value
        
        return redacted_data
    
    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic sensitive data redaction (mirrors main.py pattern)"""
        if not isinstance(data, dict):
            return data
        
        sensitive_patterns = [
            'password', 'pwd', 'pass', 'secret', 'token', 'key',
            'email', 'mail', 'phone', 'tel', 'ssn', 'social',
            'credit', 'card', 'cvv', 'cvc', 'billing'
        ]
        
        filtered_data = {}
        for key, value in data.items():
            # Check if key contains sensitive patterns
            key_lower = key.lower()
            is_sensitive = any(pattern in key_lower for pattern in sensitive_patterns)
            
            if is_sensitive:
                filtered_data[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered_data[key] = self._redact_sensitive_data(value)
            elif isinstance(value, str) and len(value) > 100:
                # Truncate potentially sensitive long strings
                filtered_data[key] = value[:100] + "..."
            else:
                filtered_data[key] = value
        
        return filtered_data
    
    def _upload_processed_data(self, client_id: str, processed_data: Dict[str, Any], source_file_key: str) -> Dict[str, Any]:
        """Upload processed data to client-partitioned S3 location"""
        try:
            # Generate client-partitioned S3 key
            timestamp = datetime.now(timezone.utc)
            processed_key = f"processed-events/{client_id}/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{processed_data['process_metadata']['process_id']}.json"
            
            # Prepare JSON content
            content = json.dumps(processed_data, indent=2, default=str)
            content_bytes = content.encode('utf-8')
            
            # Upload to processed S3 with atomic operation (temp -> rename pattern)
            temp_key = f"{processed_key}.tmp"
            
            # Upload to temp location first
            self.processed_s3.put_object(
                Bucket=self.config.processed_bucket,
                Key=temp_key,
                Body=content_bytes,
                ContentType="application/json",
                Metadata={
                    'process_id': processed_data['process_metadata']['process_id'],
                    'client_id': client_id,
                    'event_count': str(processed_data['process_metadata']['event_count']),
                    'pipeline_stage': 'processed',
                    'source_file': source_file_key,
                    'format': 'json'
                }
            )
            
            # Atomic rename (copy to final location, delete temp)
            self.processed_s3.copy_object(
                Bucket=self.config.processed_bucket,
                CopySource={'Bucket': self.config.processed_bucket, 'Key': temp_key},
                Key=processed_key
            )
            
            self.processed_s3.delete_object(
                Bucket=self.config.processed_bucket,
                Key=temp_key
            )
            
            logger.info(f"Successfully uploaded {len(processed_data['events'])} events for client {client_id} to processed S3: {processed_key}")
            
            return {
                "success": True,
                "bucket": self.config.processed_bucket,
                "key": processed_key,
                "size_bytes": len(content_bytes),
                "client_id": client_id
            }
            
        except Exception as e:
            error_msg = f"Failed to upload processed data for client {client_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "client_id": client_id
            }
    
    def _mark_file_processed(self, file_key: str):
        """Mark raw file as processed by adding metadata"""
        try:
            # Copy object to itself with updated metadata
            copy_source = {'Bucket': self.config.raw_bucket, 'Key': file_key}
            
            # Get current metadata
            head_response = self.raw_s3.head_object(
                Bucket=self.config.raw_bucket,
                Key=file_key
            )
            current_metadata = head_response.get('Metadata', {})
            
            # Add processed timestamp
            updated_metadata = current_metadata.copy()
            updated_metadata['processed_at'] = datetime.now(timezone.utc).isoformat()
            updated_metadata['pipeline_stage'] = 'processed'
            
            # Copy with updated metadata
            self.raw_s3.copy_object(
                Bucket=self.config.raw_bucket,
                CopySource=copy_source,
                Key=file_key,
                Metadata=updated_metadata,
                MetadataDirective='REPLACE'
            )
            
            logger.info(f"Marked raw file as processed: {file_key}")
            
        except Exception as e:
            logger.error(f"Failed to mark file as processed {file_key}: {str(e)}")
            # Don't raise - this is metadata only, processing was successful

def create_data_processor() -> DataProcessor:
    """Factory function to create DataProcessor with configuration"""
    config = S3ExportConfig()
    return DataProcessor(config)