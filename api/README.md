# FastAPI Analytics Backend

The FastAPI backend serves as the core event collection and processing engine for the analytics platform. It provides high-performance event ingestion, real-time health monitoring, and comprehensive ETL pipeline management.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │───▶│   FastAPI App   │───▶│   PostgreSQL    │
│   Port 80       │    │   Port 8000     │    │   Port 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  ETL Pipeline   │
                    │  Background     │
                    │  Processing     │
                    └─────────────────┘
```

## 📁 Project Structure

```
api/
├── app/
│   ├── __init__.py         # Package initialization
│   ├── main.py            # FastAPI application and event collection
│   ├── database.py        # Database connection and session management
│   ├── models.py          # SQLAlchemy ORM models
│   └── etl.py            # ETL pipeline API endpoints
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

### ETL Pipeline (`etl.py`)

Comprehensive ETL management system featuring:

**Pipeline Operations:**
- `POST /etl/run-sync`: Synchronous ETL execution with detailed results
- `POST /etl/run`: Asynchronous background processing
- `POST /etl/process/{event_type}`: Process specific event types
- `POST /etl/calculate-daily-metrics`: Generate daily aggregations

**Monitoring & Status:**
- `GET /etl/status`: Real-time pipeline health and processing statistics
- `GET /etl/recent-sessions`: Sample processed analytics data
- Unprocessed event counts by type
- Analytics table record counts

**Maintenance Operations:**
- `POST /etl/cleanup`: Automated data retention management
- Configurable retention periods for events and metrics
- Safe deletion of processed events

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

### Health Check

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

### ETL Management

```http
# Run complete ETL pipeline
POST /etl/run-sync?batch_size=1000

# Check processing status
GET /etl/status

# Get recent processed sessions
GET /etl/recent-sessions?limit=5

# Process specific event type
POST /etl/process/pageview?batch_size=1000

# Calculate daily metrics
POST /etl/calculate-daily-metrics?target_date=2025-06-24

# Clean up old data
POST /etl/cleanup?retention_days=90
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/postgres` | PostgreSQL connection string |
| `ENVIRONMENT` | `development` | Application environment (development/production) |

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

### ETL Testing

```bash
# Check ETL status
curl http://localhost:8000/etl/status

# Run ETL pipeline
curl -X POST http://localhost:8000/etl/run-sync

# View processed sessions
curl http://localhost:8000/etl/recent-sessions
```

## 📊 Performance Considerations

### Event Collection Optimization

- **Asynchronous Processing**: Events are stored immediately, ETL runs separately
- **Batch Processing**: ETL handles events in configurable batch sizes
- **Index Optimization**: Strategic database indexes for time-series queries
- **Connection Pooling**: Efficient database connection management

### Scaling Guidelines

**Single Server (Current):**
- Handles 1000+ events/second on modern hardware
- PostgreSQL can store millions of events efficiently
- ETL processing scales with batch size configuration

**Multi-Server Scaling:**
- Run multiple FastAPI instances behind load balancer
- Use managed PostgreSQL service (AWS RDS, Google Cloud SQL)
- Consider read replicas for analytics queries
- Implement Redis for session caching if needed

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

### Common Error Scenarios

**Database Connection Issues:**
- Health check endpoint reports database status
- Automatic connection retry with SQLAlchemy
- Graceful degradation without client impact

**Invalid Event Data:**
- JSON parsing errors return 400 Bad Request
- Missing fields use safe defaults
- JSONB storage handles schema flexibility

**ETL Processing Errors:**
- Individual event failures don't stop batch processing
- Detailed error logging for troubleshooting
- Retry mechanisms for transient failures

## 📈 Monitoring

### Application Metrics

**Built-in Endpoints:**
```bash
# Overall system health
curl http://localhost:8000/health

# Event collection statistics  
curl http://localhost:8000/events/count

# ETL processing status
curl http://localhost:8000/etl/status
```

**Log Monitoring:**
```bash
# View application logs
docker-compose logs -f fastapi

# Filter for errors
docker-compose logs fastapi | grep ERROR
```

### Performance Monitoring

**Database Query Performance:**
```sql
-- View slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

-- Check index usage
SELECT tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

**ETL Processing Metrics:**
- Unprocessed event counts by type
- Processing time per ETL step
- Analytics table growth rates

## 🔒 Security

### Input Validation

- **IP Address Validation**: Automatic validation with safe fallbacks
- **JSON Schema Validation**: Pydantic models for request validation
- **SQL Injection Prevention**: SQLAlchemy ORM parameter binding
- **XSS Prevention**: No direct HTML rendering in API responses

### Production Security

**Recommended Production Settings:**
```python
# Update CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**Database Security:**
- Use connection pooling with limited pool size
- Implement database connection encryption (SSL)
- Regular security updates for PostgreSQL
- Network-level access restrictions

## 🐛 Troubleshooting

### Common Issues

**Container Won't Start:**
```bash
# Check port conflicts
netstat -tulpn | grep :8000

# View detailed logs
docker-compose logs fastapi

# Rebuild container
docker-compose build --no-cache fastapi
```

**Database Connection Failed:**
```bash
# Test database connectivity
docker-compose exec postgres pg_isready -U postgres

# Check connection string
curl http://localhost:8000/health
```

**High Memory Usage:**
```bash
# Monitor container resources
docker stats

# Check for memory leaks in logs
docker-compose logs fastapi | grep -i memory
```

**ETL Processing Stuck:**
```bash
# Check for unprocessed events
curl http://localhost:8000/etl/status

# Run ETL manually
curl -X POST http://localhost:8000/etl/run-sync
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

**ETL Processing Delays:**
- Increase ETL batch size for better throughput
- Check for database lock contention
- Monitor disk I/O for PostgreSQL

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
    restart: unless-stopped
    deploy:
      replicas: 3
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

**Production:**
- Error-level logging only
- Static serving via Nginx
- Managed database service
- Restricted CORS origins
- Connection pooling optimization

---

**For additional help:**
- Main project documentation: [../README.md](../README.md)
- Database schema details: [../database/README.md](../database/README.md)
- ETL testing script: [../tests/etl_test.py](../tests/etl_test.py)