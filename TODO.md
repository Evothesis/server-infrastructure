# S3 Pipeline MVP Development Tasks

## MVP Pipeline Architecture
```
PostgreSQL → Raw S3 → Processed S3 → EventBridge → Client S3 (Client-Owned)
    ↓           ↓          ↓              ↓
  Delete     1min      Transform     Client Schedule
```

## Client Attribution & Privacy Filtering Clarification Needed
**Client Attribution:** Each event tagged with client_id for data separation
**Privacy Filtering:** Apply client-specific rules during processing:
- **Standard clients:** Full data (IP addresses, complete event data)
- **GDPR clients:** Hash IP addresses, redact PII fields, apply consent flags
- **HIPAA clients:** Enhanced redaction + audit trails + encryption markers

*Please confirm if this understanding is correct for the MVP scope.*

## MVP Development Tasks

### Phase 1: Raw Data Export (MVP Core)
- [X] **Task 1.1:** Create `RawDataExporter` class in `api/app/s3_export.py`
  - Implement 1-minute scheduled raw data dumps from PostgreSQL
  - Export unprocessed events (where `processed_at IS NULL`) to raw S3 bucket
  - Use efficient batch processing with JSON format
  - Add basic retry logic and error handling

- [X] **Task 1.2:** Update database schema (fresh start)
  - Add `raw_exported_at` timestamp field to events_log table in `database/01_init.sql`
  - Update SQLAlchemy model in `api/app/models.py`
  - Add index on `raw_exported_at` for efficient queries

- [X] **Task 1.3:** Configure raw S3 environment variables
  - Add `RAW_S3_BUCKET`, `RAW_S3_REGION`, `RAW_S3_ACCESS_KEY`, `RAW_S3_SECRET_KEY`
  - Update `docker-compose.yml` environment section
  - Update deployment scripts with new variables

### Phase 2: Data Processing Pipeline (MVP Core)
- [X] **Task 2.1:** Create `DataProcessor` class
  - Implement raw S3 → processed S3 transformation
  - Apply client attribution (separate files by client_id)
  - Apply privacy filtering based on client privacy_level
  - Support JSON output format (Parquet for later iteration)

- [X] **Task 2.2:** Implement S3-to-S3 processing
  - Monitor raw S3 bucket for new files (S3 event notifications)
  - Process files and write to processed S3 bucket with client partitioning
  - Use atomic operations (write to temp, then rename)
  - Add basic error handling and retry logic

- [X] **Task 2.3:** Configure processed S3 environment variables
  - Add `PROCESSED_S3_BUCKET`, `PROCESSED_S3_REGION`, etc.
  - Update environment configuration files

**✅ Phase 2 COMPLETED** (implemented beyond MVP requirements):
- **s3_processor.py**: Complete DataProcessor class with privacy filtering
- **Client-specific privacy levels**: Standard/GDPR/HIPAA with proper redaction
- **Pixel-management integration**: Dynamic privacy level fetching 
- **Processing endpoints**: `/process/run`, `/process/status`, `/pipeline/status`
- **Atomic S3 operations**: Temp upload → rename pattern for consistency
- **Enhanced privacy filtering**: IP hashing, user-agent anonymization, HIPAA redaction
- **Client partitioning**: `processed-events/{client_id}/` structure
- **Environment configuration**: Full processed S3 setup in docker-compose.yml
- **AWS IAM policies**: Raw + processed bucket permissions configured
- **Documentation**: Complete README updates with data format examples
- **Testing**: End-to-end pipeline validation successful

### Phase 3: Database Cleanup (MVP Core)
- [X] **Task 3.1:** Create `DatabaseCleaner` class
  - Verify successful raw S3 write before deletion (check S3 object exists)
  - Implement batch deletion from PostgreSQL
  - Update `processed_at` timestamp before deletion
  - Add basic safety checks (minimum age before deletion)

- [X] **Task 3.2:** Integrate cleanup with export pipeline
  - Trigger cleanup after successful raw export
  - Add configurable cleanup delay (default: 1 hour)
  - Include basic error logging

**✅ Phase 3 COMPLETED** (implemented with enhanced safety mechanisms):
- **database_cleaner.py**: Complete DatabaseCleaner class with multi-layer safety
- **S3 verification**: Confirms backup exists before allowing any deletion
- **Age-based protection**: Configurable minimum age (1-24 hours)
- **Batch processing**: Safe atomic transactions (500-1000 events per batch)
- **Environment configuration**: Full cleanup settings in docker-compose.yml
- **API endpoints**: `/cleanup/run`, `/cleanup/status` for manual control
- **Pipeline integration**: Enhanced `/pipeline/status` includes cleanup metrics
- **Comprehensive safety**: Multiple verification layers prevent data loss
- **Production-ready**: Conservative defaults with extensive logging
- **Transaction safety**: Atomic operations with rollback capability
- **Monitoring**: Complete status tracking and audit trails

### Phase 4: EventBridge Client Sync (MVP Core)
- [ ] **Task 4.1:** Extend client configuration for sync
  - Add `sync_frequency` field to Firestore client schema (hourly/daily/weekly)
  - Add `client_s3_bucket`, `client_s3_region`, `client_s3_access_key`, `client_s3_secret_key` fields
  - Update `backend/app/schemas.py` and Firestore models

- [ ] **Task 4.2:** Create EventBridge sync function
  - Create `ClientSyncFunction` class to copy from processed S3 to client S3
  - Filter processed data by client_id
  - Apply final privacy filtering before client delivery
  - Handle client S3 authentication and permissions

- [ ] **Task 4.3:** Configure EventBridge scheduling
  - Set up EventBridge rules based on client sync_frequency
  - Create Lambda function or container task for sync execution
  - Add basic retry logic for failed syncs

### Phase 5: Basic Configuration (MVP Essential)
- [ ] **Task 5.1:** Update environment configuration
  - Add all S3 bucket configurations to `docker-compose.yml`
  - Update deployment scripts with EventBridge configuration
  - Add pipeline timing configurations (1-minute export, cleanup delay)

- [ ] **Task 5.2:** Add client S3 configuration to admin interface
  - Update `frontend/src/components/ClientForm.js` to include:
    - Client S3 bucket credentials
    - Sync frequency selection (hourly/daily/weekly)
  - Add form validation for S3 configuration

### Phase 6: MVP Testing & Validation
- [ ] **Task 6.1:** Create pipeline integration test
  - Test complete flow: PostgreSQL → Raw S3 → Processed S3 → Client S3
  - Validate client attribution and privacy filtering
  - Test database cleanup after successful export

- [ ] **Task 6.2:** Test EventBridge integration
  - Validate sync scheduling works correctly
  - Test client-owned S3 bucket permissions
  - Verify data format in client buckets

## Implementation Priority (MVP)
1. **✅ Phase 1:** Raw export pipeline (core data movement) - **COMPLETED**
2. **✅ Phase 2:** Data processing (client attribution + privacy) - **COMPLETED**
3. **✅ Phase 3:** Database cleanup (storage optimization) - **COMPLETED**
4. **⏳ Phase 4:** EventBridge sync (client delivery) - **NEXT**
5. **Phase 5:** Configuration (admin interface)
6. **Phase 6:** Testing (validation)

## MVP Scope - Excluded Items
- ❌ Pipeline monitoring dashboard
- ❌ Real-time metrics and alerting
- ❌ Complex scheduling UI
- ❌ Client export functionality
- ❌ Performance analytics
- ❌ Data recovery procedures
- ❌ Multiple output formats (JSON only for MVP)
- ❌ Audit trails (basic logging only)