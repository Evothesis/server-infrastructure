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
- **FastAPI**: Event collection API with real-time processing and health checks
- **PostgreSQL**: Raw event storage with JSONB support for flexible data capture
- **Tracking Pixel**: JavaScript library for comprehensive behavioral tracking
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

2. **Start the platform**
   ```bash
   docker compose up -d
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
docker compose up

# Or run in background
docker compose up -d && docker compose logs -f
```

The FastAPI application will automatically reload when you modify files in `api/app/`.

## 📊 Data-as-a-Service Model

### Core Value Proposition
- **Complete Data Ownership**: Raw events exported directly to client S3 buckets
- **No Analytics Lock-in**: Clients build their own dashboards and insights
- **Privacy-First**: GDPR compliant with automatic PII redaction
- **Multi-Site Support**: Single pixel deployment tracks unlimited domains

### Business Model
- **VM-per-client deployment** with unlimited site tracking
- **Usage-based pricing** determined by unique domains detected
- **Auto-scaling billing** when new sites are added to existing pixels
- **Complete data export** with configurable formats and schedules

## 📡 Event Tracking Capabilities

### Advanced Behavioral Tracking
- **Page Views**: Full attribution tracking with UTM parameters and referrer classification
- **User Interactions**: Clicks, form submissions, text selection/copy, file downloads
- **Behavioral Analytics**: Scroll depth tracking (25%/50%/75%/100% milestones)
- **Session Management**: Cross-tab session persistence with 30-minute timeout
- **Page Visibility**: Focus/blur tracking and time-on-page measurement

### Privacy & Compliance
- **Automatic PII Redaction**: Passwords, credit cards, SSNs filtered automatically
- **Do Not Track Respect**: Built-in browser DNT preference handling
- **GDPR Compliance**: Privacy-by-design architecture
- **Anonymous Tracking**: Randomly generated visitor IDs, no fingerprinting

### Data Collection Features
- **Activity-Based Batching**: Intelligent event grouping with 60-second inactivity timeout
- **Real-Time Processing**: Sub-second event storage and processing
- **Browser Compatibility**: Support for modern browsers with graceful fallbacks
- **Cross-Domain Tracking**: Single pixel deployment across multiple domains

## 🗄️ Database Schema

### Raw Event Storage
- **`events_log`**: Primary table storing all raw events as JSONB with extracted core fields
- **Flexible Schema**: JSONB storage handles any event structure without migrations
- **Time-Series Optimized**: Indexed for chronological queries and export operations
- **Multi-Tenant**: Site-based data separation with automatic site ID detection

### Key Fields
```sql
CREATE TABLE events_log (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    visitor_id VARCHAR(100),
    site_id VARCHAR(100),
    timestamp TIMESTAMPTZ NOT NULL,
    url TEXT,
    path VARCHAR(500),
    user_agent TEXT,
    ip_address INET,
    raw_event_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    exported_at TIMESTAMPTZ  -- Tracks S3 export status
);
```

## 📤 S3 Export Pipeline

### Export Configuration
- **Dual Export**: Client bucket + backup bucket for metering
- **Configurable Schedule**: Hourly default, customizable per client
- **Multiple Formats**: JSON, CSV, and Parquet support
- **Mixed Data**: All sites in single export stream with site_id separation

### Client Configuration
```yaml
# Per-client VM configuration
s3_export:
  client_bucket: "client-analytics-bucket"
  backup_bucket: "evothesis-backup-bucket"
  format: "json"  # json, csv, parquet
  schedule: "hourly"  # hourly, daily, real-time
  credentials:
    access_key: "client-provided"
    secret_key: "client-provided"
    region: "us-east-1"
```

### Data Flow
```
Raw Events → PostgreSQL → Batch Processor → S3 Export → Client Analytics
                                      ↓
                               Backup S3 (Metering)
```

## 🔧 API Endpoints

### Event Collection
```bash
POST /collect          # Primary event collection endpoint
OPTIONS /collect       # CORS preflight handling
```

### System Monitoring
```bash
GET /health           # Health check with database connectivity
GET /events/count     # Total event count for monitoring
GET /events/recent    # Recent events (debugging)
```

### S3 Export Management (Planned)
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
- **Scalable Pricing**: Usage-based billing by unique domain count

### Multi-Tenant Agencies
- **Single VM**: Agencies deploy one VM for all client sites
- **Domain Separation**: Data exported with site_id for client separation
- **Flexible Billing**: Per-site pricing with agency-level management
- **Easy Client Handoff**: Individual client data easily separated

### Production Deployment

1. **Server Requirements**
   - Ubuntu 20.04+ or CentOS 8+
   - 4GB+ RAM, 20GB+ storage
   - Docker and Docker Compose installed

2. **Client Onboarding**
   ```bash
   # Configure client S3 credentials
   export CLIENT_S3_BUCKET="client-bucket-name"
   export CLIENT_S3_ACCESS_KEY="provided-by-client"
   export CLIENT_S3_SECRET_KEY="provided-by-client"
   
   # Deploy with client configuration
   docker compose up -d
   ```

3. **Pixel Deployment**
   ```html
   <!-- Add to client websites -->
   <script src="https://client-vm.evothesis.com/js/tracking.js"></script>
   ```

## 🔍 Monitoring & Operations

### Health Monitoring
```bash
# System health
curl http://vm-hostname:8000/health

# Event collection rate
curl http://vm-hostname:8000/events/count

# Container status
docker compose ps
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

### Performance Monitoring
- **Event Collection Rate**: Monitor events/second for capacity planning
- **S3 Export Success**: Track successful vs failed exports
- **Domain Discovery**: Monitor new domains for billing adjustments
- **Storage Growth**: Track PostgreSQL and S3 storage usage

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
- **Domain Discovery**: New site_id values trigger billing webhooks
- **Usage Tracking**: Event volume monitoring for overage billing
- **Export Verification**: Successful S3 exports confirm service delivery
- **Retention Compliance**: Automated data lifecycle management

### Client Value Delivery
- **Real-Time Data**: Events available in S3 within configured export schedule
- **Complete Ownership**: Clients control their data, infrastructure, and retention
- **Integration Ready**: Standard formats compatible with any analytics platform
- **Vendor Independence**: No lock-in, clients can export and migrate anytime

## 🛠️ Development Roadmap

### Current Status: Data Collection MVP ✅
- Event collection and storage complete
- Tracking pixel with comprehensive behavioral data
- Privacy compliance and PII redaction
- Demo environment for testing

### Next Phase: S3 Export Pipeline 🚧
- S3 client integration with per-client credentials
- Automated export scheduling (hourly default)
- Dual export (client + backup buckets)
- Export status tracking and monitoring

### Future Enhancements
- Real-time streaming exports
- Advanced export filtering and transformation
- Client dashboard for export monitoring
- Advanced billing and usage analytics

## 📚 Documentation

- [Database Schema](database/README.md) - Raw event storage documentation
- [API Reference](api/README.md) - FastAPI endpoint documentation  
- [Tracking Pixel](tracking/README.md) - JavaScript library documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/s3-export`)
3. Commit changes (`git commit -am 'Add S3 export pipeline'`)
4. Push to branch (`git push origin feature/s3-export`)
5. Create Pull Request

### Code Standards
- **Python**: Black formatting, type hints, docstrings
- **SQL**: Consistent naming, proper indexing, comments
- **JavaScript**: ESLint configuration, browser compatibility
- **Documentation**: Update README files with any changes

## 📄 License

[MIT License](LICENSE) - See LICENSE file for details

## 🆘 Support

### Common Issues

**Container won't start**
```bash
# Check port conflicts
netstat -tulpn | grep :80
netstat -tulpn | grep :5432

# Rebuild containers
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

**Database connection failed**
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Test connection manually
docker compose exec postgres psql -U postgres -d postgres
```

**Events not being tracked**
```bash
# Check browser console for errors
# Verify tracking.js is loading
curl http://localhost/js/tracking.js

# Check API endpoint
curl http://localhost:8000/health
```

**S3 Export Issues**
```bash
# Check export status
curl http://localhost:8000/export/status

# Verify S3 credentials
aws s3 ls s3://client-bucket/ --profile client-profile

# Manual export test
curl -X POST http://localhost:8000/export/run
```

---

**Built with ❤️ for complete data ownership and privacy-first analytics**