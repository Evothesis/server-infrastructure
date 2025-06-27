# Analytics Platform - Data-as-a-Service MVP

A privacy-focused data collection and export platform that captures comprehensive website behavioral data and delivers it directly to client S3 buckets. Built for agencies and businesses that need complete data ownership without vendor lock-in.

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Nginx    │    │   FastAPI   │    │ PostgreSQL  │    │  S3 Export  │
│ (Port 80)   │───▶│ (Port 8000) │───▶│ (Port 5432) │───▶│ Client      │
│ Web Server  │    │Event Collect│    │ Raw Events  │    │ Buckets     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                                      │
       ▼                                      ▼
┌─────────────┐                    ┌─────────────┐
│ Demo Site   │                    │  Backup     │
│ tracking.js │                    │  S3 Bucket  │
│ Pixel       │                    │ (Metering)  │
└─────────────┘                    └─────────────┘
```

### Components

- **Nginx**: Reverse proxy serving static demo site and routing API requests
- **FastAPI**: Event collection API with **bulk insert optimization** for high-volume processing
- **PostgreSQL**: Raw event storage with JSONB support and **write-optimized configuration**
- **Tracking Pixel**: JavaScript library for comprehensive behavioral tracking with **intelligent batching**
- **S3 Export**: Automated export to client buckets + backup bucket for metering

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- 4GB+ RAM recommended
- Ports 80, 5432, 8000 available

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd server-infrastructure
   ```

2. **Configure environment**
   ```bash
   # Development (no S3 credentials needed)
   docker compose --env-file .env.development up -d
   
   # Production (with real S3 credentials)
   docker compose --env-file .env.production up -d
   ```

3. **Verify installation**
   ```bash
   # Check all services are running
   docker compose ps
   
   # Check API health
   curl http://localhost:8000/health
   
   # Visit demo site
   open http://localhost
   ```

### Development Setup

For development with hot reload:

```bash
# Start with logs visible
docker compose --env-file .env.development up

# Or run in background
docker compose --env-file .env.development up -d && docker compose logs -f
```

The FastAPI application will automatically reload when you modify files in `api/app/`.

## 📊 Data-as-a-Service Model

### Core Value Proposition
- **Complete Data Ownership**: Raw events exported directly to client S3 buckets
- **No Analytics Lock-in**: Clients build their own dashboards and insights
- **Privacy-First**: GDPR compliant with automatic PII redaction
- **Enterprise Performance**: Handles 200M+ events/month with bulk insert optimization

### Business Model
- **VM-per-client deployment** with unlimited site tracking
- **Usage-based pricing**: $0.01 per 1,000 events (metered billing)
- **Auto-scaling billing** when new sites are added to existing pixels
- **Complete data export** with configurable formats and schedules

## 📡 Event Tracking Capabilities

### Advanced Behavioral Tracking
- **Page Views**: Full attribution tracking with UTM parameters and referrer classification
- **User Interactions**: Clicks, form submissions, text selection/copy, file downloads
- **Behavioral Analytics**: Scroll depth tracking (25%/50%/75%/100% milestones)
- **Session Management**: Cross-tab session persistence with 30-minute timeout
- **Page Visibility**: Focus/blur tracking and time-on-page measurement

### High-Performance Event Processing
- **Bulk Insert Optimization**: Events processed in batches for 50-100x performance improvement
- **Activity-Based Batching**: Intelligent event grouping with 60-second inactivity timeout
- **Write-Optimized Database**: PostgreSQL configured for high-volume write operations
- **Real-Time Processing**: Sub-second event storage and processing

### Privacy & Compliance
- **Automatic PII Redaction**: Passwords, credit cards, SSNs filtered automatically
- **Do Not Track Respect**: Built-in browser DNT preference handling
- **GDPR Compliance**: Privacy-by-design architecture
- **Anonymous Tracking**: Randomly generated visitor IDs, no fingerprinting

## 🗄️ Database Schema

### Optimized Raw Event Storage
- **`events_log`**: Primary table storing all raw events as JSONB with extracted core fields
- **Bulk Insert Performance**: Single transaction processing for event batches
- **Write-Optimized Configuration**: PostgreSQL tuned for high-volume write operations
- **Flexible Schema**: JSONB storage handles any event structure without migrations
- **Time-Series Optimized**: Indexed for chronological queries and export operations
- **Multi-Tenant**: Site-based data separation with automatic site ID detection

### Key Performance Features
```sql
-- Bulk insert optimization in action
db.bulk_insert_mappings(EventLog, events_batch)
db.commit()  -- Single transaction for entire batch

-- vs. old pattern (50-100x slower)
for event in events:
    db.add(EventLog(event))
    db.commit()  -- Individual transaction per event
```

## 📤 S3 Export Pipeline

### Export Configuration
- **Dual Export**: Client bucket + backup bucket for metering
- **Configurable Schedule**: Hourly default, customizable per client
- **Multiple Formats**: JSON, CSV, and Parquet support
- **Buffer-Based Processing**: Short-term database storage (hours) before S3 export

### Client Configuration
```bash
# Environment-based scaling
# Development
export POSTGRES_SHARED_BUFFERS=128MB
export CLIENT_S3_BUCKET=dev-bucket

# Production  
export POSTGRES_SHARED_BUFFERS=2GB
export CLIENT_S3_BUCKET=client-analytics-bucket
```

### Data Flow
```
Raw Events → Bulk Insert → PostgreSQL Buffer → S3 Export → Client Analytics
                                      ↓
                               Backup S3 (Metering)
```

## 🔧 API Endpoints

### Event Collection (Optimized)
```bash
POST /collect          # Bulk-optimized event collection endpoint
OPTIONS /collect       # CORS preflight handling
```

### System Monitoring
```bash
GET /health           # Health check with database connectivity
GET /events/count     # Total event count for monitoring
GET /events/recent    # Recent events (debugging)
```

### S3 Export Management
```bash
POST /export/run      # Manual export trigger
GET /export/status    # Export pipeline status
GET /export/config    # Client export configuration
```

## 🚀 Deployment Architecture

### VM-per-Client Model
- **Dedicated Infrastructure**: Each client gets isolated VM deployment
- **Multi-Site Support**: Single pixel tracks unlimited client domains
- **Auto-Discovery**: New domains automatically detected and billed
- **Scalable Pricing**: Usage-based billing by event volume

### Performance Scaling
- **Single VM Capacity**: Handles 200M+ events/month with optimization
- **Database Performance**: Write-optimized PostgreSQL configuration
- **Memory Scaling**: Environment-based resource allocation
- **Connection Pooling**: Optimized for high-concurrency write operations

### Production Deployment

1. **Server Requirements**
   - Ubuntu 20.04+ or CentOS 8+
   - 4GB+ RAM, 20GB+ storage
   - Docker and Docker Compose installed

2. **Client Onboarding**
   ```bash
   # Configure client-specific environment
   cp .env.development .env.client
   # Edit .env.client with client S3 credentials
   
   # Deploy with client configuration
   docker compose --env-file .env.client up -d
   ```

3. **Pixel Deployment**
   ```html
   <!-- Add to client websites -->
   <script src="https://client-vm.evothesis.com/js/tracking.js"></script>
   ```

## 🔍 Monitoring & Operations

### Performance Monitoring
```bash
# System health
curl http://vm-hostname:8000/health

# Event collection rate
curl http://vm-hostname:8000/events/count

# Container status
docker compose ps

# Database performance
docker compose logs postgres
```

### Bulk Insert Verification
```bash
# Test single event
curl -X POST http://localhost:8000/collect -H "Content-Type: application/json" \
  -d '{"eventType":"test","sessionId":"test_session","siteId":"localhost"}'

# Test batch processing (critical for performance)
curl -X POST http://localhost:8000/collect -H "Content-Type: application/json" \
  -d '{"eventType":"batch","sessionId":"test","siteId":"localhost","events":[{"eventType":"click"},{"eventType":"scroll"}]}'

# Verify bulk insert in logs
docker compose logs fastapi | grep "Bulk inserted"
```

### Data Export Verification
```bash
# Check export status
curl http://vm-hostname:8000/export/status

# Manual export trigger
curl -X POST http://vm-hostname:8000/export/run

# View recent exports
aws s3 ls s3://client-bucket/analytics/ --recursive
```

## 🔒 Privacy & Compliance

### Built-in Privacy Protection
- **No PII Collection**: Visitor IDs are randomly generated, not personal identifiers
- **Sensitive Data Redaction**: Automatic filtering of passwords, credit cards, SSNs
- **Session Isolation**: Each session gets unique ID, no cross-session tracking
- **Configurable Retention**: Client-controlled data retention policies

### GDPR Compliance Features
- **Do Not Track**: Respects browser DNT headers automatically
- **Data Portability**: Complete export capabilities for user data requests
- **Right to Deletion**: Visitor ID-based data removal procedures
- **Consent Integration**: Built-in support for consent management platforms

## 📈 Business Model Integration

### Automatic Billing Events
- **Event Volume Tracking**: Real-time monitoring for metered billing
- **Domain Discovery**: New site_id values trigger billing adjustments
- **Export Verification**: Successful S3 exports confirm service delivery
- **Performance Metrics**: Bulk insert efficiency for cost optimization

### Client Value Delivery
- **Enterprise Performance**: 200M+ events/month processing capability
- **Real-Time Data**: Events available in S3 within configured export schedule
- **Complete Ownership**: Clients control their data, infrastructure, and retention
- **Integration Ready**: Standard formats compatible with any analytics platform
- **Vendor Independence**: No lock-in, clients can export and migrate anytime

## 🛠️ Recent Performance Optimizations

### Bulk Insert Implementation ✅
- **50-100x Performance Improvement**: Batch processing vs. individual inserts
- **Single Transaction Processing**: Entire event batches in one database commit
- **Activity-Based Batching**: Intelligent grouping based on user behavior patterns
- **Write-Optimized Database**: PostgreSQL configured for high-volume operations

### Infrastructure Scaling ✅
- **Environment-Based Configuration**: Automatic scaling based on deployment environment
- **Memory Optimization**: Efficient resource allocation for different server sizes
- **Connection Pool Tuning**: Optimized for high-concurrency write operations
- **Monitoring Integration**: Performance tracking and alerting capabilities

## 📚 Documentation

- [Database Schema](database/README.md) - Optimized event storage documentation
- [API Reference](api/README.md) - FastAPI endpoint documentation with performance details
- [Tracking Pixel](tracking/README.md) - JavaScript library documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/optimization`)
3. Commit changes (`git commit -am 'Add performance optimization'`)
4. Push to branch (`git push origin feature/optimization`)
5. Create Pull Request

### Code Standards
- **Python**: Black formatting, type hints, docstrings
- **SQL**: Consistent naming, proper indexing, performance-focused
- **JavaScript**: ESLint configuration, browser compatibility
- **Documentation**: Update README files with any performance changes

## 📄 License

[MIT License](LICENSE) - See LICENSE file for details

## 🆘 Support

### Common Issues

**Bulk insert not working**
```bash
# Check for batch processing logs
docker compose logs fastapi | grep "Processing batch"
docker compose logs fastapi | grep "Bulk inserted"

# Test batch endpoint
curl -X POST http://localhost:8000/collect -H "Content-Type: application/json" \
  -d '{"eventType":"batch","events":[{"eventType":"test1"},{"eventType":"test2"}]}'
```

**Database performance issues**
```bash
# Check PostgreSQL configuration
docker compose exec postgres psql -U postgres -c "SHOW shared_buffers;"
docker compose exec postgres psql -U postgres -c "SHOW work_mem;"

# Monitor connection pool
docker compose logs fastapi | grep -i "pool"
```

**S3 Export Issues**
```bash
# Check export configuration
curl http://localhost:8000/export/config

# Verify credentials
curl http://localhost:8000/export/status

# Manual export test
curl -X POST http://localhost:8000/export/run
```

---

**Built with ❤️ for complete data ownership, enterprise performance, and privacy-first analytics**