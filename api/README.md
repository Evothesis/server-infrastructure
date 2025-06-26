# FastAPI Data Collection Backend

The FastAPI backend serves as the core event collection engine for the data-as-a-service analytics platform. It provides high-performance event ingestion, real-time health monitoring, and automated S3 export pipeline for complete data ownership.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │───▶│   FastAPI App   │───▶│   PostgreSQL    │───▶│   S3 Export     │
│   Port 80       │    │   Port 8000     │    │   Port 5432     │    │ Client Buckets  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐       ┌─────────────────┐
                    │  Health & Stats │       │  Backup Bucket  │
                    │  Monitoring     │       │  (Metering)     │
                    └─────────────────┘       └─────────────────┘
```

## 📁 Project Structure

```
api/
├── app/
│   ├── __init__.py         # Package initialization
│   ├── main.py            # FastAPI application and event collection
│   ├── database.py        # Database connection and session management
│   ├── models.py          # SQLAlchemy ORM models
│   └── s3_export.py       # S3 export pipeline (planned)
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md            # This file
```

## 🚀 Core Components

### Event Collection API (`main.py`)

The primary FastAPI application handles:

- **Event Ingestion**: High-throughput collection of analytics events via `/collect` endpoint
- **Health Monitoring**: Database connectivity checks and system status reporting
- **CORS Handling**: Cross-origin request support for web tracking
- **IP Extraction**: Real client IP detection through proxy headers
- **Timestamp Parsing**: Robust ISO timestamp handling with timezone support

**Key Features:**
- Graceful error handling that never blocks client requests
- Automatic IP address validation and fallback
- JSON and query parameter support for flexible event submission
- Comprehensive request logging for debugging

### Database Layer (`database.py`, `models.py`)

**Database Configuration:**
- PostgreSQL connection with SQLAlchemy ORM
- Environment-based configuration for different deployment scenarios
- Connection pooling for high-concurrency workloads
- Automatic table creation on startup

**Data Models:**
- `EventLog`: Primary event storage with JSONB flexibility and extracted core fields
- Optimized for time-series queries with strategic indexing
- Support for multi-tenant data separation by site_id

### S3 Export Pipeline (`s3_export.py`) - Planned

The core data-as-a-service functionality featuring:

**Export Operations:**
- `POST /export/run`: Manual export trigger
- `GET /export/status`: Export pipeline health and statistics
- `GET /export/config`: Client export configuration
- Automated scheduling with configurable intervals

**Client Configuration:**
- Per-client S3 credentials (encrypted storage)
- Configurable export formats (JSON, CSV, Parquet)
- Dual export (client bucket + backup bucket)
- Export frequency settings (hourly, daily, real-time)

## 📡 API Endpoints

### Event Collection

```http
POST /collect
Content-Type: application/json

{
  "eventType": "pageview",
  "sessionId": "sess_abc123",
  "visitorId": "vis_xyz789", 
  "siteId": "example-com",
  "timestamp": "2025-06-22T12:00:00Z",
  "url": "https://example.com/page",
  "path": "/page",
  "attribution": {
    "utmParams": {
      "utm_source": "google",
      "utm_medium": "cpc"
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Event received and stored",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-06-22T12:00:00.123Z"
}
```

### System Monitoring

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected", 
  "timestamp": "2025-06-22T12:00:00.123Z"
}
```

### Data Export (Planned)

```http
# Trigger manual export
POST /export/run?format=json&since=2025-06-22T00:00:00Z

# Check export status
GET /export/status

# Get client configuration
GET /export/config
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/postgres` | PostgreSQL connection string |
| `ENVIRONMENT` | `development` | Application environment (development/production) |
| `S3_BACKUP_BUCKET` | None | Backup bucket for metering and retention |
| `CLIENT_S3_BUCKET` | None | Client's S3 bucket for data export |
| `CLIENT_S3_ACCESS_KEY` | None | Client-provided S3 access key |
| `CLIENT_S3_SECRET_KEY` | None | Client-provided S3 secret key |
| `EXPORT_SCHEDULE` | `hourly` | Default export frequency |
| `EXPORT_FORMAT` | `json` | Default export format |

### Database Configuration

The application automatically creates database tables on startup using SQLAlchemy models. For production deployments, consider using database migrations with Alembic.

**Connection Pool Settings:**
```python
# Configured in database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## 🔧 Development

### Local Development Setup

1. **Install Dependencies**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost:5432/analytics"
   export ENVIRONMENT="development"
   ```

3. **Run Development Server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Testing Event Collection

```bash
# Test basic event collection
curl -X POST http://localhost:8000/collect \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "test",
    "sessionId": "test_session", 
    "visitorId": "test_visitor",
    "siteId": "localhost"
  }'

# Check health
curl http://localhost:8000/health

# View recent events
curl http://localhost:8000/events/recent
```

### S3 Export Testing (Planned)

```bash
# Test export pipeline
curl -X POST http://localhost:8000/export/run

# Check export status
curl http://localhost:8000/export/status

# Verify S3 upload
aws s3 ls s3://client-bucket/analytics/
```

## 📊 Data Export Architecture

### Raw Event Export Strategy

**Why Raw Events Only:**
- **Client Flexibility**: Clients build their own analytics and dashboards
- **Reduced Complexity**: No analytics processing pipeline to maintain
- **Faster Time-to-Market**: Simpler architecture, fewer moving parts
- **Complete Data Ownership**: Clients get all captured data without vendor interpretation

### Export Formats

**JSON (Default):**
```json
{
  "export_metadata": {
    "export_id": "exp_abc123",
    "export_time": "2025-06-22T12:00:00Z",
    "event_count": 1543,
    "time_range": {
      "start": "2025-06-22T11:00:00Z",
      "end": "2025-06-22T12:00:00Z"
    }
  },
  "events": [
    {
      "id": 12345,
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "pageview",
      "session_id": "sess_abc123",
      "visitor_id": "vis_xyz789",
      "site_id": "example-com",
      "timestamp": "2025-06-22T11:30:15Z",
      "url": "https://example.com/page",
      "raw_event_data": {...}
    }
  ]
}
```

**CSV Format:**
```csv
id,event_id,event_type,session_id,visitor_id,site_id,timestamp,url,path,raw_event_data
12345,550e8400-e29b-41d4,pageview,sess_abc123,vis_xyz789,example-com,2025-06-22T11:30:15Z,https://example.com/page,/page,"{...}"
```

**Parquet Format:**
- Columnar storage for efficient analytics processing
- Schema evolution support for new event types
- Optimized for data warehouse ingestion

### Export Scheduling

**Configurable Frequency:**
- **Hourly** (default): Exports every hour at minute 0
- **Daily**: Exports daily at midnight UTC
- **Real-time**: Streaming exports for enterprise clients
- **Custom**: Cron-based scheduling for specific requirements

**Export Triggers:**
- **Scheduled**: Automatic exports based on configuration
- **Manual**: API-triggered exports for testing/backfill
- **Threshold**: Export when event count reaches specified limit
- **On-demand**: Client-requested exports via webhook

## 📈 Performance Considerations

### Event Collection Optimization

- **Asynchronous Processing**: Events stored immediately, exports run separately
- **Batch Processing**: Exports handle thousands of events efficiently
- **Index Optimization**: Strategic database indexes for time-series queries
- **Connection Pooling**: Efficient database connection management

### Scaling Guidelines

**Single VM (Current):**
- Handles 10,000+ events/hour on modern hardware
- PostgreSQL can store millions of events efficiently
- S3 export scales with available bandwidth

**Multi-Client Scaling:**
- **VM-per-client**: Isolated infrastructure for enterprise clients
- **Shared Infrastructure**: Agency model with multi-tenant data separation
- **Auto-scaling**: Horizontal scaling based on event volume
- **Global Distribution**: Regional VMs for latency optimization

## 🚨 Error Handling

### Event Collection Resilience

The API is designed to never lose events due to processing errors:

```python
# Graceful error handling example
try:
    # Process and store event
    db.add(event_record)
    db.commit()
    return {"status": "success"}
except Exception as e:
    logger.error(f"Error processing event: {e}")
    # Still return success to client
    return {"status": "error", "message": "Event processing failed"}
```

### S3 Export Error Handling

**Retry Logic:**
- Exponential backoff for temporary S3 failures
- Dead letter queue for permanently failed exports
- Client notification for export failures
- Manual retry capability via API

**Common Error Scenarios:**
- **S3 Credentials Invalid**: Client notification + export pause
- **Network Connectivity**: Automatic retry with backoff
- **Data Format Errors**: Validation before export attempt
- **Quota Exceeded**: Client notification + billing integration

## 🔒 Security

### Input Validation

- **IP Address Validation**: Automatic validation with safe fallbacks
- **JSON Schema Validation**: Pydantic models for request validation
- **SQL Injection Prevention**: SQLAlchemy ORM parameter binding
- **XSS Prevention**: No direct HTML rendering in API responses

### S3 Export Security

**Credential Management:**
- Client S3 credentials encrypted at rest
- No long-term credential storage
- IAM role-based access where possible
- Credential rotation support

**Data Protection:**
- TLS encryption for all S3 transfers
- Bucket-level access policies
- Export audit logging
- Data integrity verification

### Production Security

**Recommended Production Settings:**
```python
# Update CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://client-domain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**Infrastructure Security:**
- Database connection encryption (SSL)
- Regular security updates for all dependencies
- Network-level access restrictions
- Container security scanning

## 🐛 Troubleshooting

### Common Issues

**Container Won't Start:**
```bash
# Check port conflicts
netstat -tulpn | grep :8000

# View detailed logs
docker compose logs fastapi

# Rebuild container
docker compose build --no-cache fastapi
```

**Database Connection Failed:**
```bash
# Test database connectivity
docker compose exec postgres pg_isready -U postgres

# Check connection string
curl http://localhost:8000/health
```

**High Memory Usage:**
```bash
# Monitor container resources
docker stats

# Check for memory leaks in logs
docker compose logs fastapi | grep -i memory
```

**S3 Export Failures:**
```bash
# Check export status
curl http://localhost:8000/export/status

# Test S3 credentials
aws s3 ls s3://client-bucket/ --profile client-profile

# View export logs
docker compose logs fastapi | grep -i s3
```

### Debug Mode

Enable detailed logging for development:

```python
# In main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

**Slow Event Collection:**
- Check database connection pool settings
- Monitor `pg_stat_activity` for blocking queries
- Verify sufficient database resources

**S3 Export Delays:**
- Check network bandwidth to S3
- Monitor export queue size
- Verify S3 bucket permissions and quotas

## 🔄 Deployment

### Production Deployment

**Docker Production Configuration:**
```yaml
# docker-compose.prod.yml
services:
  fastapi:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://user:pass@db.example.com:5432/analytics
      - ENVIRONMENT=production
      - S3_BACKUP_BUCKET=evothesis-backup-bucket
      - CLIENT_S3_BUCKET=client-analytics-bucket
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

**Health Check Configuration:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Environment-Specific Settings

**Development:**
- Debug logging enabled
- Hot reload with `--reload` flag
- Local database connection
- Permissive CORS settings
- Mock S3 exports for testing

**Production:**
- Error-level logging only
- Static serving via Nginx
- Managed database service
- Restricted CORS origins
- Real S3 integration
- Connection pooling optimization

### VM-per-Client Deployment

**Client Onboarding Process:**
1. **VM Provisioning**: Create dedicated client VM
2. **Configuration**: Set client-specific environment variables
3. **Deployment**: Deploy with client S3 credentials
4. **Testing**: Verify event collection and S3 export
5. **Pixel Integration**: Provide client with tracking pixel URL

**Configuration Template:**
```bash
# Client-specific environment
export CLIENT_NAME="client-company"
export CLIENT_S3_BUCKET="client-analytics-bucket"
export CLIENT_S3_ACCESS_KEY="AKIA..."
export CLIENT_S3_SECRET_KEY="..."
export EXPORT_SCHEDULE="hourly"
export EXPORT_FORMAT="json"

# Deploy
docker compose -f docker-compose.prod.yml up -d
```

---

**For additional help:**
- Main project documentation: [../README.md](../README.md)
- Database schema details: [../database/README.md](../database/README.md)
- Tracking pixel documentation: [../tracking/README.md](../tracking/README.md)