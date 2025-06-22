# Analytics Platform - Single VM Migration

A self-hosted analytics platform migrated from AWS serverless architecture to a single-VM Docker deployment. Built for privacy-focused web analytics with comprehensive event tracking and real-time data processing.

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Nginx    │    │   FastAPI   │    │ PostgreSQL  │
│ (Port 80)   │───▶│ (Port 8000) │───▶│ (Port 5432) │
│ Web Server  │    │    API      │    │  Database   │
└─────────────┘    └─────────────┘    └─────────────┘
       │
       ▼
┌─────────────┐
│ Demo Site   │
│ tracking.js │
│ Pixel       │
└─────────────┘
```

### Components

- **Nginx**: Reverse proxy serving static demo site and routing API requests
- **FastAPI**: Event collection API with real-time processing and health checks
- **PostgreSQL**: Primary database with JSONB support for flexible event storage
- **Tracking Pixel**: JavaScript library for comprehensive behavioral tracking

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- 8GB+ RAM recommended
- Ports 80, 5432, 8000 available

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd server-infrastructure
   ```

2. **Start the platform**
   ```bash
   docker-compose up -d
   ```

3. **Verify installation**
   ```bash
   # Check all services are running
   docker-compose ps
   
   # Check API health
   curl http://localhost:8000/health
   
   # Visit demo site
   open http://localhost
   ```

### Development Setup

For development with hot reload:

```bash
# Start with logs visible
docker-compose up

# Or run in background
docker-compose up -d && docker-compose logs -f
```

The FastAPI application will automatically reload when you modify files in `api/app/`.

## 📊 Features

### Event Tracking
- **Page Views**: Full attribution tracking with UTM parameters and referrer classification
- **User Interactions**: Clicks, form submissions, text selection/copy, file downloads
- **Behavioral Analytics**: Scroll depth tracking (25%/50%/75%/100% milestones)
- **Session Management**: Cross-tab session persistence with 30-minute timeout
- **Page Visibility**: Focus/blur tracking and time-on-page measurement

### Data Collection
- **Activity-Based Batching**: Intelligent event grouping with 60-second inactivity timeout
- **Real-Time Processing**: Immediate storage of critical events (pageviews, form submissions)
- **Privacy-Focused**: Automatic redaction of sensitive form fields (passwords, credit card info)
- **Browser Compatibility**: Support for modern browsers with graceful fallbacks

### Analytics Infrastructure
- **Flexible Schema**: JSONB storage for event data with extracted core fields for performance
- **Multi-Tenant**: Site-based data separation with automatic site ID detection
- **Real-Time APIs**: Live event counts and recent activity endpoints
- **Time-Series Data**: Optimized for time-based queries and reporting

## 🗄️ Database Schema

### Raw Event Storage
- **`events_log`**: Primary table storing all raw events as JSONB with extracted core fields
- **Indexing**: Optimized for time-series queries, session lookup, and site filtering

### Analytics Tables (Processed Data)
- **`user_sessions`**: Aggregated session data with attribution and device information
- **`pageviews`**: Individual page visits with timing and referrer data
- **`user_events`**: Structured interaction events (clicks, scrolls, form submissions)
- **`form_submissions`**: Dedicated form analytics with field-level insights
- **`daily_site_metrics`**: Pre-aggregated daily statistics for dashboard performance

See [database/README.md](database/README.md) for detailed schema documentation.

## 📡 API Endpoints

### Event Collection
```bash
POST /collect          # Primary event collection endpoint
OPTIONS /collect       # CORS preflight handling
```

### Monitoring & Analytics
```bash
GET /health           # Health check with database connectivity test
GET /events/count     # Total event count
GET /events/recent    # Recent events (debugging)
```

### Example Usage
```javascript
// Events are automatically sent by the tracking pixel
// Manual event sending:
fetch('/collect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    eventType: 'custom_event',
    sessionId: 'sess_abc123',
    visitorId: 'vis_xyz789',
    siteId: 'example-com',
    eventData: { action: 'button_click' }
  })
});
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/postgres` | PostgreSQL connection string |
| `ENVIRONMENT` | `development` | Application environment |

### Tracking Pixel Configuration

Edit `tracking/js/tracking.js` to customize tracking behavior:

```javascript
var config = {
  sessionTimeout: 30 * 60 * 1000,     // 30 minutes
  inactivityTimeout: 60 * 1000,       // 1 minute
  maxBatchSize: 50,                   // Events per batch
  scrollMilestones: [25, 50, 75, 100], // Scroll tracking percentages
  trackClicks: true,
  trackForms: true,
  trackScrollDepth: true,
  trackTextSelection: true,
  trackPageVisibility: true
};
```

## 🚢 Deployment

### Production Deployment

1. **Server Requirements**
   - Ubuntu 20.04+ or CentOS 8+
   - 4GB+ RAM, 20GB+ storage
   - Docker and Docker Compose installed

2. **Security Configuration**
   ```bash
   # Update CORS origins in api/app/main.py
   allow_origins=["https://yourdomain.com"]
   
   # Configure reverse proxy (Nginx/Apache) for SSL termination
   # Set up firewall rules (ports 80, 443 only)
   ```

3. **Production Environment**
   ```bash
   # Use production docker-compose override
   cp docker-compose.prod.yml docker-compose.override.yml
   
   # Set production environment variables
   export DATABASE_URL="postgresql://user:pass@localhost:5432/analytics"
   export ENVIRONMENT="production"
   
   # Deploy
   docker-compose up -d
   ```

### Scaling Considerations

- **Database**: Use managed PostgreSQL (AWS RDS, Google Cloud SQL) for high traffic
- **Load Balancing**: Multiple FastAPI containers behind load balancer
- **CDN**: Serve tracking pixel from CDN for global performance
- **Monitoring**: Add Prometheus/Grafana for operational metrics

## 🔍 Monitoring

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database connectivity
docker-compose exec postgres pg_isready -U postgres

# Container status
docker-compose ps
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f fastapi
docker-compose logs -f postgres
docker-compose logs -f nginx
```

### Performance Monitoring
```bash
# Database queries
docker-compose exec postgres psql -U postgres -c "
  SELECT query, calls, total_time, mean_time 
  FROM pg_stat_statements 
  ORDER BY total_time DESC LIMIT 10;"

# Event collection rate
curl http://localhost:8000/events/count
```

## 🧪 Testing

### Test Data Generation

Visit the demo site at `http://localhost` and interact with:
- Navigation between pages
- Form submissions
- Button clicks and link clicks
- Text selection and copying
- Scroll through long pages
- Tab switching (page visibility)

### Manual Testing
```bash
# Send test event
curl -X POST http://localhost:8000/collect \
  -H "Content-Type: application/json" \
  -d '{"eventType":"test","siteId":"localhost","sessionId":"test_session"}'

# Check event was stored
curl http://localhost:8000/events/recent
```

## 📈 Migration from AWS

This platform replaces the following AWS services:

| AWS Service | Local Equivalent | Migration Notes |
|-------------|------------------|-----------------|
| Lambda | FastAPI containers | Event processing logic preserved |
| DynamoDB | PostgreSQL | JSONB provides similar flexibility |
| S3 | Local storage | Static assets served by Nginx |
| CloudFront | Nginx + optional CDN | Cache headers configured |
| API Gateway | Nginx reverse proxy | CORS and routing handled |

### Data Migration

If migrating from existing AWS setup:
1. Export DynamoDB data to JSON
2. Transform to PostgreSQL format using provided ETL scripts
3. Bulk import via `COPY` commands
4. Update tracking pixels to point to new endpoints

## 🔒 Privacy & Compliance

### Data Protection
- **No PII Collection**: Visitor IDs are randomly generated, not tied to personal information
- **Sensitive Data Redaction**: Automatic filtering of password fields, credit card info, SSNs
- **Session Isolation**: Each session gets unique ID, no cross-session tracking
- **Data Retention**: Configurable retention policies with automatic cleanup

### GDPR Compliance
- **Do Not Track**: Respects browser DNT headers
- **Data Portability**: JSON export capabilities for user data requests
- **Right to Deletion**: Visitor ID-based data removal procedures
- **Consent Management**: Integration points for consent management platforms

## 🛠️ Development

### Local Development
```bash
# Install development dependencies
cd api && pip install -r requirements.txt

# Run tests
pytest

# Format code
black api/app/
isort api/app/

# Database migrations
cd api && alembic upgrade head
```

### Adding New Event Types

1. **Update tracking pixel** (`tracking/js/tracking.js`)
2. **Add API processing** (`api/app/main.py`)
3. **Create analytics table** if needed (`database/`)
4. **Update ETL pipeline** for new event type

### Database Changes

1. **Create migration** in `database/` directory with incremental number
2. **Test migration** on development data
3. **Update documentation** in database README
4. **Deploy** with `docker-compose down -v && docker-compose up -d`

## 📚 Documentation

- [Database Schema](database/README.md) - Detailed database documentation
- [API Reference](api/README.md) - FastAPI endpoint documentation
- [Tracking Pixel](tracking/README.md) - JavaScript library documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/analytics-dashboard`)
3. Commit changes (`git commit -am 'Add analytics dashboard'`)
4. Push to branch (`git push origin feature/analytics-dashboard`)
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
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

**Database connection failed**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Test connection manually
docker-compose exec postgres psql -U postgres -d postgres
```

**Events not being tracked**
```bash
# Check browser console for errors
# Verify tracking.js is loading
curl http://localhost/js/tracking.js

# Check API endpoint
curl http://localhost:8000/health
```

### Getting Help

1. Check the [Issues](https://github.com/your-repo/issues) for similar problems
2. Review logs: `docker-compose logs -f`
3. Create detailed issue with logs and reproduction steps
4. For urgent issues: [Contact information]

---

**Built with ❤️ for privacy-focused analytics**