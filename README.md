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
    │  Firestore DB   │    │   PostgreSQL        │    │    S3 Export        │
    │ - Domain index  │    │ - Event storage     │    │ - Client buckets    │
    │ - Client data   │    │ - Bulk optimized    │    │ - Backup/metering   │
    └─────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## 🎯 Core Features

**🚀 Bulk Insert Optimization**
- 50-100x performance improvement over individual inserts
- Intelligent event batching with client attribution
- Single transaction processing for event batches
- Supports 200M+ events/month per VM

**🔒 Client Attribution & Security**
- Domain authorization via pixel-management integration
- Client-specific pixel serving with real-time config
- Unauthorized domain blocking at collection layer
- Privacy compliance (GDPR/HIPAA) per client settings

**📊 Multi-Tenant Architecture**
- Shared infrastructure with client isolation
- Per-client S3 export configuration
- Automatic billing event generation
- Complete data ownership model

## 📁 Repository Structure

```
server-infrastructure/
├── api/                    # FastAPI event collection service
├── database/              # PostgreSQL schema and initialization
├── tracking/              # Integration testing and examples
├── nginx/                # Reverse proxy configuration
├── docker-compose.yml    # Service orchestration
└── .env.development      # Configuration templates
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
curl http://localhost:8000/health                    # API health
curl http://localhost:8000/collect                   # Event collection endpoint
```

### Production Deployment
```bash
# 1. Configure client environment
cp .env.development .env.production
# Edit with client S3 credentials and pixel-management URL

# 2. Deploy with optimization
docker compose --env-file .env.production up -d

# 3. Verify bulk processing
docker compose logs fastapi | grep "Bulk inserted"
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
CLIENT_S3_BUCKET=client-analytics-bucket
BACKUP_S3_BUCKET=evothesis-analytics-backup
```

## 📊 Monitoring & Operations

### Health Checks
```bash
# System health
curl http://localhost:8000/health

# Bulk processing verification
docker compose logs fastapi | grep "Processing batch"
docker compose logs fastapi | grep "Bulk inserted"

# Client attribution verification
curl http://localhost:8000/events/recent
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

# S3 export status
curl http://localhost:8000/export/status
```

### Troubleshooting

**Bulk Insert Not Working**
```bash
# Check for batch events
docker compose logs fastapi | grep "eventType.*batch"

# Verify bulk processing logs
docker compose logs fastapi | grep "Bulk inserted"

# Test batch endpoint directly
curl -X POST http://localhost:8000/collect -H "Content-Type: application/json" \
  -d '{"eventType":"batch","sessionId":"test","siteId":"localhost","events":[{"eventType":"click"},{"eventType":"scroll"}]}'
```

**Client Attribution Issues**
```bash
# Check pixel-management connectivity
curl $PIXEL_MANAGEMENT_URL/api/v1/config/domain/localhost

# Verify client_id in events
curl http://localhost:8000/events/recent | jq '.[] | select(.client_id != null)'

# Check domain authorization logs
docker compose logs fastapi | grep "Domain.*authorized"
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

## 📚 Documentation

- [API Reference](api/README.md) - FastAPI collection service with bulk optimizations
- [Database Schema](database/README.md) - PostgreSQL optimization and client attribution
- [Tracking Pixel](tracking/README.md) - JavaScript library with domain authorization

## 🆘 Support

### Common Issues

**Events Not Attributed to Client**
- Verify `PIXEL_MANAGEMENT_URL` environment variable
- Check domain authorization in pixel-management system
- Ensure pixel URL includes correct client_id

**Poor Performance Despite Bulk Optimization**
- Verify batch events are being sent (look for `eventType: "batch"`)
- Check PostgreSQL memory configuration
- Monitor database connection pool utilization

**S3 Export Failures**
- Verify S3 credentials and bucket permissions
- Check export schedule configuration
- Monitor backup bucket for billing/metering data

---

**Built for enterprise-scale analytics with complete data ownership and privacy compliance**