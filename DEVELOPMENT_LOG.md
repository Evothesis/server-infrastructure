# Evothesis Development Log

## Project Overview
Evothesis is a data-as-a-service analytics platform that captures comprehensive website behavioral data and exports it directly to client S3 buckets. The platform prioritizes complete data ownership, privacy compliance, and vendor independence over traditional dashboard-based analytics.

## Business Model Evolution
**Original Model (Deprecated):** SaaS analytics platform with built-in dashboards
**Current Model:** Data-as-a-service with VM-per-client deployment

- **VM-per-Client Deployment:** Dedicated infrastructure for each client/agency
- **Multi-Site Support:** Single pixel tracks unlimited domains per client
- **Usage-Based Pricing:** Billing based on unique domains detected automatically
- **Complete Data Ownership:** Raw events exported to client S3 buckets
- **No Analytics Lock-in:** Clients build their own dashboards from exported data

## Current Project Status

### ✅ Completed Components

#### Data Collection Platform (Backend)
- **FastAPI backend** with robust event collection at `/collect` endpoint
- **PostgreSQL database** with JSONB event storage (simplified schema)
- **Docker deployment** with nginx reverse proxy
- **Privacy features** including automatic PII redaction and Do Not Track respect
- **Session management** with cross-tab continuity and 30-minute timeout
- **Real-time processing** with sub-second event handling

#### Advanced Tracking Pixel (Frontend)
- **JavaScript tracking library** (`tracking/js/tracking.js`) with comprehensive behavioral analytics
- **Activity-based batching** with 60-second inactivity timeout
- **Advanced tracking capabilities:**
  - Page views with full attribution (UTM parameters, referrer classification)
  - Click tracking with element details and position data
  - Form submission analysis with automatic PII protection
  - Scroll depth milestones (25%, 50%, 75%, 100%)
  - Text selection and copy events
  - Page visibility tracking (focus/blur)
  - Cross-tab session continuity
- **Privacy-first design** with automatic sensitive field redaction

#### Demo Environment
- **Static HTML demo site** (`tracking/`) showcasing tracking capabilities
- **Test pages** for comprehensive interaction testing (forms, clicks, scrolls)
- **Working tracking pixel** integration for live demonstration

#### Marketing Website (GitHub Pages Ready)
- **Professional 5-page marketing site** with clear value proposition
- **Revenue optimization messaging** focused on complete data ownership
- **Transparent pricing** structure with compliance add-ons
- **Contact form** for lead generation (currently placeholder)

### 🔧 Simplified Technical Architecture

#### Revised Backend Stack
- **FastAPI** for API endpoints and event collection
- **PostgreSQL** with JSONB support for raw event storage only
- **Docker Compose** for local development and deployment
- **Nginx** for reverse proxy and static file serving

#### Streamlined Data Flow
```
Browser (tracking.js) → Nginx → FastAPI (/collect) → PostgreSQL (events_log) → S3 Export
```

**Key Architectural Decision:** Removed complex ETL pipeline in favor of raw event export

#### Core Features (Simplified)
- **Raw event collection** with comprehensive behavioral data
- **Privacy compliance** built into core architecture
- **Multi-tenant support** via site_id separation
- **Direct S3 export** for customer data ownership
- **No analytics processing** - clients build their own insights

---

## Development Sessions

### Session 1: Initial Website Creation (June 2025)
**Participants:** User, Claude
**Objective:** Create GitHub Pages marketing website for Evothesis

#### Completed Work
1. **Business Strategy Definition**
2. **Website Architecture & Design** 
3. **Content Strategy**
4. **5-Page Marketing Site Creation**
5. **Messaging Refinements**

### Session 2: Architecture Simplification (June 2025)
**Participants:** User, Claude  
**Objective:** Simplify platform architecture and focus on data-as-a-service MVP

#### Major Architectural Changes
1. **Removed Analytics Processing**
   - Deleted `database/02_analytics.sql` (analytics tables)
   - Deleted `database/03_etl_procedures.sql` (ETL stored procedures)
   - Deleted `api/app/etl.py` (ETL API endpoints)
   - Deleted `tests/etl_test.py` (ETL testing)

2. **Simplified Data Pipeline**
   - **Before:** Raw Events → ETL Pipeline → Analytics Tables → Dashboards
   - **After:** Raw Events → S3 Export → Client Analytics

3. **Business Model Pivot**
   - **From:** SaaS analytics platform with dashboards
   - **To:** Data-as-a-service with complete client ownership

#### Technical Debt Resolution
- **Clean Container Startup:** Fixed FastAPI imports after ETL module removal
- **Verified Data Collection:** Confirmed event collection and storage working correctly
- **Database Schema Cleanup:** Simplified to single `events_log` table
- **Removed Complexity:** Eliminated ETL processing pipeline entirely

#### System Verification Results
- ✅ **Event Collection**: Working (`/collect` endpoint storing events successfully)
- ✅ **Database Storage**: 20+ events stored with proper JSONB structure
- ✅ **Demo Site**: Serving with functional tracking pixel
- ✅ **Container Health**: All services running cleanly

---

## Current Architecture Details

### Database Schema (Simplified)
```sql
-- Single table for raw event storage
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
    exported_at TIMESTAMPTZ  -- For S3 export tracking
);
```

### API Endpoints (Current)
- `POST /collect` - Primary event collection
- `GET /health` - System health check
- `GET /events/count` - Event count monitoring
- `GET /events/recent` - Recent events (debugging)

### Multi-Site Architecture
- **Site Detection:** Automatic via hostname in tracking pixel
- **Data Separation:** All sites mixed with `site_id` field
- **Client Flexibility:** Easy parsing by domain on client side
- **Billing Integration:** Unique domain counting for usage-based pricing

---

## Immediate Next Steps & Development Plan

### 🚀 Priority 1: S3 Export Pipeline (In Progress)

#### Technical Implementation
1. **S3 Client Integration**
   - Add boto3 dependency to `requirements.txt`
   - Create `api/app/s3_export.py` module
   - Environment-based S3 configuration per client

2. **Export Functionality**
   - Configurable export schedule (hourly default)
   - Multiple format support (JSON, CSV, Parquet)
   - Dual export (client bucket + backup bucket)
   - Export status tracking with `exported_at` field

3. **Client Configuration System**
   ```python
   # Per-client environment variables
   CLIENT_S3_BUCKET = "client-analytics-bucket"
   CLIENT_S3_ACCESS_KEY = "client-provided"
   CLIENT_S3_SECRET_KEY = "client-provided" 
   BACKUP_S3_BUCKET = "evothesis-backup-bucket"
   EXPORT_SCHEDULE = "hourly"
   EXPORT_FORMAT = "json"
   ```

4. **Export API Endpoints**
   - `POST /export/run` - Manual export trigger
   - `GET /export/status` - Export pipeline status
   - `GET /export/config` - Client configuration

#### Business Logic Implementation
- **Auto-Discovery:** New domains trigger billing adjustments
- **Usage Tracking:** Event volume monitoring for metering
- **Retention Management:** Configurable data retention (client lifetime default)
- **Export Verification:** Success tracking for service delivery confirmation

### 📈 Priority 2: Marketing Website Deployment

#### Immediate Tasks
1. **GitHub Pages Deployment**
   - Create public repository
   - Upload marketing site files
   - Configure custom domain (optional)
   - Test all page functionality

2. **Contact Form Integration**
   - Choose service (Netlify Forms, Formspree, or Formspark)
   - Update form action and method
   - Configure email notifications
   - Test submission workflow

3. **Analytics Integration (Dogfooding)**
   - Deploy SecurePixel on marketing site
   - Configure S3 export for marketing data
   - Monitor visitor behavior and conversions

### 🔧 Priority 3: Production Readiness

#### Infrastructure Preparation
1. **VM Deployment Templates**
   - Docker Compose production configuration
   - Client onboarding automation scripts
   - Environment configuration templates
   - Health monitoring setup

2. **Security Hardening**
   - S3 credential encryption at rest
   - TLS configuration for all endpoints
   - Container security scanning
   - Network access restrictions

3. **Monitoring & Alerting**
   - Export pipeline monitoring
   - Event collection rate tracking
   - S3 upload success/failure alerts
   - System resource monitoring

---

## Technical Decisions & Rationale

### Why Remove Analytics Processing?

1. **Faster Time-to-Market:** Eliminates complex ETL development
2. **Client Flexibility:** Raw data allows custom analytics approaches
3. **Reduced Complexity:** Fewer failure points and maintenance overhead
4. **Data Ownership:** Complete client control over data processing
5. **Business Model Alignment:** Focuses on data export, not analytics dashboards

### Why VM-per-Client?

1. **Data Isolation:** Complete client data separation
2. **Compliance:** Easier GDPR/HIPAA compliance with isolated infrastructure
3. **Customization:** Per-client configuration and scaling
4. **Billing Simplicity:** Clear usage attribution per client
5. **Enterprise Appeal:** Dedicated infrastructure for premium pricing

### Why S3 Export Focus?

1. **Data Ownership:** Clients control their data completely
2. **Integration Flexibility:** Compatible with any analytics platform
3. **Vendor Independence:** No lock-in to Evothesis analytics
4. **Scalability:** S3 handles unlimited data volume
5. **Cost Efficiency:** No expensive analytics infrastructure

---

## Business Model Implementation

### Pricing Strategy
- **Small Business:** $199/month (1M pageviews, unlimited domains)
- **Growth Business:** $499/month (10M pageviews, unlimited domains)  
- **Enterprise:** $999/month (100M pageviews, unlimited domains)
- **Overages:** $10 per 100K additional pageviews
- **HIPAA Compliance:** +$1,500/month with BAA

### Auto-Billing Logic
```python
# Domain discovery triggers billing adjustment
def handle_new_domain(site_id, client_id):
    if site_id not in client_domains[client_id]:
        client_domains[client_id].append(site_id)
        trigger_billing_webhook(client_id, new_domain=site_id)
        
# Usage monitoring for overage billing
def calculate_monthly_usage(client_id, month):
    total_pageviews = count_pageviews(client_id, month)
    plan_limit = get_client_plan_limit(client_id)
    if total_pageviews > plan_limit:
        overage = total_pageviews - plan_limit
        overage_charge = (overage / 100000) * 10  # $10 per 100K
        trigger_overage_billing(client_id, overage_charge)
```

### Client Onboarding Process
1. **VM Provisioning:** Automated client VM deployment
2. **S3 Configuration:** Client provides bucket credentials
3. **Pixel Deployment:** Client adds tracking script to websites
4. **Domain Discovery:** System automatically detects tracked domains
5. **Export Verification:** Confirm S3 exports are successful
6. **Billing Activation:** Start usage monitoring and billing

---

## Success Metrics & KPIs

### Technical Metrics
- **Event Collection Rate:** Events per second per VM
- **S3 Export Success Rate:** Percentage of successful exports
- **System Uptime:** 99.9% availability target
- **Data Processing Latency:** Export delay from event collection

### Business Metrics  
- **Client Acquisition:** New VM deployments per month
- **Domain Growth:** Average domains per client over time
- **Revenue per Client:** Monthly recurring revenue trends
- **Data Export Volume:** Total data exported to client buckets

### Product Metrics
- **Pixel Integration Success:** Percentage of successful pixel deployments
- **Multi-Domain Usage:** Clients using multiple domains (agency indicator)
- **Export Format Preferences:** JSON vs CSV vs Parquet adoption
- **Retention Rate:** Client churn and contract renewal rates

---

## Risk Assessment & Mitigation

### Technical Risks
1. **S3 Export Failures**
   - **Mitigation:** Retry logic, dead letter queues, client alerts
2. **VM Resource Limits**
   - **Mitigation:** Auto-scaling, resource monitoring, capacity planning
3. **Data Loss**
   - **Mitigation:** Dual exports, backup retention, transaction logging

### Business Risks
1. **Client Data Portability Demands**
   - **Mitigation:** This is a feature, not a risk - complete export capability
2. **Compliance Violations**
   - **Mitigation:** Privacy-by-design, automatic PII redaction, audit trails
3. **Competitive Pressure**
   - **Mitigation:** Data ownership differentiation, privacy-first positioning

### Operational Risks
1. **Client Onboarding Complexity**
   - **Mitigation:** Automation scripts, clear documentation, support processes
2. **S3 Credential Management**
   - **Mitigation:** Encrypted storage, credential rotation, access auditing

---

## Future Roadmap (Post-MVP)

### Phase 2: Enhanced Export Features
- **Real-time Streaming:** WebSocket/Kinesis integration for instant data
- **Advanced Filtering:** Client-configurable export filters and transformations
- **Multi-Format Exports:** Simultaneous export in multiple formats
- **Data Warehouse Integration:** Direct BigQuery, Snowflake, Redshift connectors

### Phase 3: Enterprise Features
- **Global VM Distribution:** Regional deployments for latency optimization
- **Advanced Security:** SOC 2 Type II, additional compliance certifications
- **Custom Analytics:** Optional pre-built dashboard service
- **API Access:** Direct data access APIs for client applications

### Phase 4: Platform Expansion
- **Mobile SDK:** Native iOS/Android tracking SDKs
- **Server-Side Tracking:** Backend event collection for complete user journeys
- **Attribution Modeling:** Advanced attribution across all touchpoints
- **Predictive Analytics:** Optional ML-powered insights service

---

## Notes for Future Development

### Context Preservation
- **Project Vision:** Privacy-first data collection with complete client ownership
- **Business Focus:** Data export service, not analytics platform
- **Technical Approach:** Simple, robust architecture prioritizing data delivery
- **Current Stage:** S3 export pipeline development for MVP completion

### Ongoing Principles
- **Privacy-First:** Every feature must respect user privacy by design
- **Data Ownership:** Client data belongs to client, not platform
- **Technical Excellence:** Sub-second processing, reliable exports, enterprise scale
- **Compliance Focus:** GDPR built-in, HIPAA available, regulation-ready architecture
- **Business Enablement:** All features should enable client business growth

### Development Guidelines
- **No Shortcuts:** Prioritize maintainable, high-quality code over quick fixes
- **Privacy by Design:** Consider privacy implications of every feature
- **Client Value First:** Features must provide clear client business value
- **Documentation Driven:** Update docs with every architectural change
- **Test Everything:** Comprehensive testing for data integrity and export reliability

### Success Criteria for MVP Completion
- **S3 Export Working:** Reliable hourly exports to client buckets
- **Multi-Format Support:** JSON, CSV, and Parquet export options
- **Domain Auto-Discovery:** Automatic billing adjustment for new domains
- **Export Monitoring:** Clear visibility into export success/failure
- **Client Onboarding:** Streamlined VM deployment and configuration
- **Marketing Site Live:** Professional website with functional contact form

### Key Learnings from Architecture Simplification
1. **Complexity Kills Velocity:** Removing ETL pipeline accelerated development significantly
2. **Client Ownership Wins:** Data export model is more compelling than dashboard SaaS
3. **Privacy as Differentiator:** GDPR compliance attracts privacy-conscious clients
4. **Multi-Site Value:** Agency model with unlimited domains per VM is powerful
5. **Raw Data Flexibility:** Clients prefer raw events over processed analytics

---

*Last Updated: June 26, 2025*
*Current Phase: S3 Export Pipeline Development*
*Next Milestone: MVP Launch with Full Data Export Capability*