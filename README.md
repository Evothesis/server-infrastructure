# Server Infrastructure - Analytics Collection Platform

**High-performance event collection backend that receives tracking data from client websites with domain authorization and bulk processing optimizations**

## 🏗️ System Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ Pixel Management    │    │ Server Infrastructure│◄───│  Client Websites   │
│ - Serves tracking   │    │ - Event collection   │    │ - Load pixel from   │
│   pixel to websites │    │ - Domain validation  │    │   pixel-management  │
│ - Domain auth API   │◄───│ - Bulk processing    │    │ - Send events to    │
│ - Privacy settings  │    │ - Client attribution │    │   server infra      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
          │                           │                           
          ▼                           ▼                           
    ┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
    │  Firestore DB   │    │   PostgreSQL        │    │    S3 Pipeline      │
    │ - Domain index  │    │ - Event storage     │    │ - Raw S3 Export     │
    │ - Client data   │    │ - Bulk optimized    │    │ - Processed S3      │
    │ - Privacy levels │    │ - Pipeline ready    │    │ - Client delivery   │
    └─────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## 🔄 Data Processing Pipeline

```
Raw Export (1min)           Processing                   Client Delivery
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   PostgreSQL    │ 1min    │   Raw S3        │ process │ Processed S3    │
│ ┌─────────────┐ │ ────►   │ ┌─────────────┐ │ ──────► │ ┌─────────────┐ │
│ │ Event Batch │ │ export  │ │ Raw JSON    │ │ filter  │ │ Client      │ │
│ │ (client_id) │ │         │ │ (timestamped│ │ privacy │ │ Partitioned │ │
│ └─────────────┘ │         │ │  & metadata)│ │ levels  │ │ JSON Files  │ │
│ ┌─────────────┐ │         │ └─────────────┘ │         │ └─────────────┘ │
│ │Delete after │ │         │ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │raw_exported │ │         │ │ Multiple    │ │         │ │ GDPR/HIPAA  │ │
│ └─────────────┘ │         │ │ Clients     │ │         │ │ Compliant   │ │
└─────────────────┘         │ └─────────────┘ │         │ └─────────────┘ │
                            └─────────────────┘         └─────────────────┘
```

## 🎯 Core Features

**🚀 Bulk Insert Optimization**
- 50-100x performance improvement over individual inserts
- Intelligent event batching with client attribution
- Single transaction processing for event batches
- Supports 200M+ events/month per VM

**🔒 Client Attribution & Security**
- Domain authorization via pixel-management integration
- Unauthorized domain blocking at collection layer
- Privacy compliance (GDPR/HIPAA) per client settings
- Multi-tenant data isolation

**📊 Multi-Tenant Data Pipeline**
- Shared infrastructure with client isolation
- Client-partitioned S3 processing pipeline  
- Privacy-compliant data transformation (GDPR/HIPAA)
- Complete data ownership model with automated delivery

**🔄 S3 Processing Pipeline**
- **Raw Export**: PostgreSQL → Raw S3 (1-minute intervals)
- **Processing**: Client partitioning & privacy filtering → Processed S3
- **Delivery**: EventBridge delivery → Client-owned S3 buckets
- Atomic processing with metadata tracking and retry logic

## 📁 Repository Structure

```
server-infrastructure/
├── api/                    # FastAPI event collection service
│   └── app/
│       ├── s3_export.py   # Raw S3 export pipeline
│       ├── s3_processor.py # Data processing & privacy filtering
│       └── main.py        # Collection & pipeline endpoints
├── database/              # PostgreSQL schema and initialization
├── tracking/              # Integration testing demo site
│   └── testing/           # HTML test files for browser testing
├── nginx/                # Reverse proxy configuration
├── docker-compose.yml    # Service orchestration with S3 pipeline
└── .env.development      # S3 pipeline configuration
```

## 🚀 Quick Start

### Development Setup
```bash
# 1. Clone and configure
git clone <repository>
cd server-infrastructure

# 2. Start services with client attribution
docker compose --env-file .env.development up -d

# 3. Verify integration
curl http://localhost:8001/health                    # API health
curl http://localhost:8001/collect                   # Event collection endpoint
curl http://localhost:8001/pipeline/status           # S3 pipeline status
```

### Production Deployment
```bash
# 1. Configure client environment
cp .env.development .env.production
# Edit with raw/processed S3 credentials and pixel-management URL

# 2. Deploy with optimization
docker compose --env-file .env.production up -d

# 3. Verify pipeline processing
docker compose logs fastapi | grep "Successfully uploaded.*raw S3"
docker compose logs fastapi | grep "Successfully uploaded.*processed S3"
```

## ⚡ Performance Optimizations

### Bulk Insert Implementation
**Before:** Individual event processing
```python
for event in events:
    db.add(EventLog(event))
    db.commit()  # 200M transactions/month
```

**After:** Batch processing with client attribution
```python
# Process entire batch in single transaction
db.bulk_insert_mappings(EventLog, events_with_client_id)
db.commit()  # 20M transactions/month (90% reduction)
```

### Performance Benchmarks
- **Event Volume**: 200M+ events/month capacity per VM
- **Processing Time**: <1ms per batch with bulk processing
- **Database Load**: 90% reduction in transaction overhead
- **Scalability**: Handles burst traffic through intelligent batching

## 📦 S3 Data Pipeline & Formats

### Raw Data Export
**Frequency**: Every 1 minute  
**Location**: `raw-events/{year}/{month}/{day}/raw_export_{timestamp}.json`  
**Purpose**: Backup and processing source

**Raw Data Format**:
```json
{
  "export_metadata": {
    "export_id": "raw_export_20250719_154912",
    "export_time": "2025-07-19T15:49:12.123456Z",
    "event_count": 13,
    "format": "json",
    "pipeline_stage": "raw",
    "time_range": {
      "start": "2025-07-19T15:45:00.000000Z",
      "end": "2025-07-19T15:49:00.000000Z"
    }
  },
  "events": [
    {
      "id": 123,
      "event_id": "uuid-123-456",
      "event_type": "page_view",
      "session_id": "session_abc",
      "visitor_id": "visitor_xyz",
      "site_id": "example.com",
      "timestamp": "2025-07-19T15:47:30.123456Z",
      "url": "https://example.com/page",
      "path": "/page",
      "user_agent": "Mozilla/5.0...",
      "ip_address": "192.168.1.100",
      "client_id": "client_evothesis_admin",
      "created_at": "2025-07-19T15:47:30.123456Z",
      "raw_event_data": {
        "referrer": "https://google.com",
        "page_title": "Example Page"
      }
    }
  ]
}
```

### Processed Data
**Frequency**: On-demand or scheduled  
**Location**: `processed-events/{client_id}/{year}/{month}/{day}/processed_{timestamp}.json`  
**Purpose**: Client delivery with privacy compliance

**Processed Data Format**:
```json
{
  "process_metadata": {
    "process_id": "processed_20250719_154922",
    "process_time": "2025-07-19T15:49:22.123456Z",
    "client_id": "client_evothesis_admin",
    "event_count": 13,
    "format": "json",
    "pipeline_stage": "processed",
    "privacy_level": "gdpr"
  },
  "events": [
    {
      "id": 123,
      "event_id": "uuid-123-456",
      "event_type": "page_view",
      "session_id": "session_abc",
      "visitor_id": "visitor_xyz",
      "site_id": "example.com",
      "timestamp": "2025-07-19T15:47:30.123456Z",
      "url": "https://example.com/page",
      "path": "/page",
      "user_agent": "Chrome/[VERSION] (anonymized)",
      "ip_address": "2e0870240092daf4",
      "client_id": "client_evothesis_admin",
      "created_at": "2025-07-19T15:47:30.123456Z",
      "raw_event_data": {
        "referrer": "https://google.com",
        "page_title": "Example Page"
      },
      "gdpr_processed": true,
      "ip_anonymized": true
    }
  ]
}
```

### Privacy Filtering Levels

**Standard (default)**:
- Basic sensitive data redaction (passwords, SSNs, etc.)
- Full IP addresses preserved
- Complete user agent strings

**GDPR Compliance**:
- IP addresses hashed with SHA-256
- User agents anonymized to browser family only
- Enhanced PII redaction
- `gdpr_processed: true` marker

**HIPAA Compliance**:
- All GDPR protections plus:
- Medical/health keyword filtering
- Enhanced redaction patterns
- `hipaa_processed: true` and `audit_required: true` markers

### Pipeline Control Endpoints

```bash
# Raw Export
POST /export/run              # Trigger manual raw export
GET  /export/status           # Check export status
GET  /export/config           # View S3 configuration

# Data Processing
POST /process/run             # Trigger manual processing
GET  /process/status          # Check processing status

# Pipeline Overview
GET  /pipeline/status         # Complete pipeline status
```

## 🔧 Integration with Pixel Management System

### Event Collection Flow
1. Client websites load tracking pixel from pixel-management system
2. Websites send tracking events directly to this server infrastructure's `/collect` endpoint
3. Server validates domain authorization via pixel-management API before processing
4. Authorized events processed with automatic client attribution and bulk optimization

### Configuration Integration
```bash
# Environment variables for pixel-management integration
PIXEL_MANAGEMENT_URL=https://pixel-management-url.run.app

# S3 Pipeline Configuration
RAW_S3_BUCKET=securepixel-raw-events
RAW_S3_REGION=us-east-1
RAW_S3_ACCESS_KEY=AKIA...
RAW_S3_SECRET_KEY=...

PROCESSED_S3_BUCKET=securepixel-processed-events
PROCESSED_S3_REGION=us-east-1
PROCESSED_S3_ACCESS_KEY=AKIA...
PROCESSED_S3_SECRET_KEY=...

# Pipeline Settings
EXPORT_BATCH_SIZE=10000
EXPORT_FORMAT=json
```

## 🧪 Testing & Development

### Integration Test Site
The repository includes a comprehensive test site for validating the complete analytics pipeline:

```
tracking/testing/
├── index.html          # Homepage with comprehensive interaction testing
├── products.html       # E-commerce simulation with form testing
└── contact.html        # Contact page with lead generation forms
```

**Test Site Features:**
- **Page Views**: Full attribution tracking with UTM parameters
- **User Interactions**: Clicks, form submissions, text selection/copy
- **Behavioral Analytics**: Scroll depth tracking and session management
- **E-commerce Simulation**: Product pages with cart interactions
- **Form Testing**: Contact forms and inquiry submissions

### Local Testing
```bash
# Start development environment
docker compose --env-file .env.development up -d

# Access test site
open http://localhost

# Monitor event collection and pipeline
docker compose logs -f fastapi | grep "Bulk inserted"
docker compose logs -f fastapi | grep "Successfully uploaded.*S3"
```

### API Testing
```bash
# Test single event
curl -X POST http://localhost:8001/collect \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "pageview",
    "sessionId": "test_session",
    "visitorId": "test_visitor",
    "siteId": "localhost",
    "url": "http://localhost/test"
  }'

# Test batch processing
curl -X POST http://localhost:8001/collect \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "batch",
    "sessionId": "test_session", 
    "siteId": "localhost",
    "events": [
      {"eventType": "click", "eventData": {"element": "test1"}},
      {"eventType": "scroll", "eventData": {"depth": 50}}
    ]
  }'

# Verify client attribution
curl http://localhost:8001/events/recent

# Test S3 pipeline
curl -X POST http://localhost:8001/export/run      # Trigger raw export
curl -X POST http://localhost:8001/process/run     # Trigger processing
curl http://localhost:8001/pipeline/status         # Check pipeline status
```

### Browser Testing
1. Open `http://localhost` in browser
2. Interact with test site elements (click buttons, scroll, fill forms)
3. Monitor Network tab for `/collect` requests
4. Verify bulk batching in request payloads
5. Check event attribution in logs
6. Test S3 pipeline processing with generated events

## 📊 Monitoring & Operations

### Health Checks
```bash
# System health
curl http://localhost:8001/health

# Bulk processing verification
docker compose logs fastapi | grep "Processing batch"
docker compose logs fastapi | grep "Bulk inserted"

# Client attribution verification
curl http://localhost:8001/events/recent
```

### Performance Monitoring
```bash
# Database performance
docker compose exec postgres psql -U postgres -c "
SELECT client_id, COUNT(*) as events, 
       DATE_TRUNC('hour', created_at) as hour
FROM events_log 
GROUP BY client_id, hour 
ORDER BY hour DESC LIMIT 20;"

# S3 pipeline status
curl http://localhost:8001/pipeline/status
curl http://localhost:8001/export/status
curl http://localhost:8001/process/status
```

### Troubleshooting

**Events Not Being Collected**
```bash
# Check domain authorization
curl $PIXEL_MANAGEMENT_URL/api/v1/config/domain/your-domain.com

# Check browser console for JavaScript errors

# Verify pixel accessibility (if using pixel-management)
curl http://your-vm/pixel/your_client_id/tracking.js
```

**No Client Attribution**
```bash
# Verify pixel-management connectivity
docker compose logs fastapi | grep "pixel-management"

# Check domain in pixel-management system
# Ensure domain is added to client in admin interface

# Verify client_id in events
curl http://localhost:8001/events/recent | jq '.[] | select(.client_id == null)'
```

**Poor Performance Despite Bulk Optimization**
```bash
# Verify bulk batching
docker compose logs fastapi | grep "Processing batch"

# Check batch sizes (should be 5+ events)
docker compose logs fastapi | grep "batch with" | grep -o "with [0-9]*" | sort | uniq -c

# Monitor for individual event processing (should be minimal)
docker compose logs fastapi | grep -v "batch" | grep "Processing"
```

**Database Performance Issues**
```bash
# Check PostgreSQL configuration
docker compose exec postgres psql -U postgres -c "SHOW shared_buffers;"
docker compose exec postgres psql -U postgres -c "SHOW work_mem;"

# Monitor connection pool
docker compose logs fastapi | grep -i "pool"
```

## 🔒 Privacy & Compliance

### Built-in Privacy Protection
- **No PII Collection**: Visitor IDs are random, not personal identifiers
- **Sensitive Data Redaction**: Automatic filtering of passwords, SSNs, etc.
- **Client-Specific Privacy**: GDPR/HIPAA settings from pixel-management
- **Data Retention**: Client-controlled via S3 lifecycle policies

### Compliance Integration
- **Domain Authorization**: Prevents unauthorized data collection
- **Client Attribution**: Enables data subject rights by client
- **Audit Trail**: Complete event provenance in backup S3
- **Export Capabilities**: Complete data portability for clients

## 📈 Scaling Guidelines

### Resource Allocation
```bash
# Small deployment (< 50M events/month)
POSTGRES_SHARED_BUFFERS=512MB
POSTGRES_WORK_MEM=4MB

# Medium deployment (50-200M events/month)
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_WORK_MEM=8MB

# Large deployment (200M+ events/month)
POSTGRES_SHARED_BUFFERS=4GB
POSTGRES_WORK_MEM=16MB
```

### Multi-Client Deployment
- **VM-per-Client**: Dedicated infrastructure for enterprise clients
- **Shared Infrastructure**: Cost-effective for smaller clients
- **Auto-Scaling**: Environment-based resource allocation
- **Load Balancing**: Multiple VMs behind load balancer for high-volume clients

## 🚀 Production Integration Examples

### Client-Specific VM Deployment
```html
<!-- Each client gets dedicated pixel URL -->
<script src="https://acme-analytics.evothesis.com/pixel/client_acme_corp/tracking.js"></script>
<script src="https://beta-analytics.evothesis.com/pixel/client_beta_inc/tracking.js"></script>
```

### Shared Infrastructure Model
```html
<!-- Multiple clients share infrastructure with domain isolation -->
<script src="https://shared-vm.evothesis.com/pixel/client_acme_corp/tracking.js"></script>
```

### Enterprise Integration
```javascript
// Advanced configuration for enterprise clients
window.EvothesisConfig = {
  client_id: 'client_enterprise',
  endpoint: 'https://dedicated-vm.client.com/collect',
  batch_size: 50,        // Larger batches for high volume
  flush_interval: 2000,  // Faster flushing for real-time needs
  privacy_mode: 'hipaa', // Enhanced compliance
  custom_fields: {
    tenant_id: 'tenant_123',
    environment: 'production'
  }
};
```

## 📚 Documentation

- [API Reference](api/README.md) - FastAPI collection service with bulk optimizations
- [Database Schema](database/README.md) - PostgreSQL optimization and client attribution

---

**Built for enterprise-scale analytics with complete data ownership and privacy compliance**