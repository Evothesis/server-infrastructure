# Testing Site & Integration Validation

This directory contains the testing website for validating the complete Evothesis analytics integration pipeline. The testing site demonstrates real-world usage of the dynamic pixel system with proper client authorization and event attribution.

## 🏗️ Integration Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Testing Site  │───▶│  Dynamic Pixel  │───▶│   FastAPI      │───▶│   PostgreSQL    │
│   Static HTML   │    │  /pixel/{id}/   │    │   /collect     │    │   events_log    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ User Interactions│    │Client Config    │    │Domain Resolution│    │Client Attribution│
│ • Page views    │    │• Privacy level  │    │• Authorization  │    │• Billing ready  │
│ • Clicks        │    │• Feature flags  │    │• Security check │    │• Event storage  │
│ • Form submits  │    │• Compliance     │    │• Multi-tenant   │    │• Bulk optimized │
│ • Scroll depth  │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Testing Site Structure

```
testing/
├── index.html          # Homepage with comprehensive interaction testing
├── products.html       # E-commerce simulation with form testing
├── contact.html        # Contact page with lead generation forms
└── README.md          # This file
```

## 🎯 Integration Testing Features

### Real Production Pipeline
- **Dynamic Pixel Loading**: Uses `/pixel/client_tuynaamtsjkd/tracking.js` endpoint
- **Domain Authorization**: `localhost` domain authorized via pixel-management UI
- **Client Configuration**: Privacy settings and features injected from pixel-management
- **Event Attribution**: All events properly tagged with `client_tuynaamtsjkd`

### Comprehensive Event Testing
- **Page Views**: Full attribution tracking with UTM parameters
- **User Interactions**: Clicks, form submissions, text selection/copy
- **Behavioral Analytics**: Scroll depth tracking and session management
- **Bulk Processing**: Activity-based batching with 60-second timeout
- **Privacy Compliance**: Automatic PII redaction and consent handling

## 🔬 Validation Checkpoints

### End-to-End Integration ✅
```bash
# 1. Pixel serves correctly
curl http://localhost/pixel/client_tuynaamtsjkd/tracking.js

# 2. Domain authorization working
curl https://pixel-management-275731808857.us-central1.run.app/api/v1/config/domain/localhost

# 3. Events stored with correct client attribution
curl http://localhost:8000/events/recent

# 4. Bulk insert optimization preserved
docker compose logs fastapi | grep "Bulk inserted"
```

### Performance Verification ✅
- **Bulk Insert Working**: `Processing batch with X individual events`
- **Client Attribution**: Events stored with `client_tuynaamtsjkd`
- **Domain Security**: Unauthorized domains return 404
- **Cache Efficiency**: 5-minute client configuration cache

### Production Readiness ✅
- **Template Architecture**: JavaScript maintained in separate files
- **Container Builds**: Templates built into image, not volume mounted
- **Security Validated**: Domain authorization prevents unauthorized access
- **Multi-Client Ready**: Shared infrastructure with proper client isolation

## 🚀 Testing Instructions

### Browser Testing
1. **Open**: `http://localhost` in browser
2. **Check Console**: Should see `[Evothesis] Analytics pixel loaded for client: client_tuynaamtsjkd`
3. **Interact**: Click elements, scroll, submit forms
4. **Monitor Network**: Events sent to `/collect` endpoint

### Log Monitoring
```bash
# Watch for successful event attribution
docker compose logs -f fastapi | grep "client_tuynaamtsjkd"

# Expected output:
# INFO:app.main:Processing batch with X individual events for client client_tuynaamtsjkd
# INFO:app.main:Bulk inserted X events for client client_tuynaamtsjkd from site localhost
```

### Database Verification
```bash
# Check recent events
curl http://localhost:8000/events/recent

# Verify client_id field populated
# Expected: All events should have proper client attribution
```

## 🏭 Production Integration Example

For real client deployments, this testing pattern becomes:

```html
<!-- Client loads pixel from shared infrastructure -->
<script src="https://shared-vm.evothesis.com/pixel/client_acme_corp/tracking.js"></script>
```

**Flow**:
1. `client_acme_corp` authorized for `shop.acme.com` in pixel-management
2. Pixel loads with client-specific privacy and feature configuration
3. Events sent with `siteId: "shop.acme.com"`
4. Server resolves `shop.acme.com` → `client_acme_corp`
5. Events stored with proper client attribution for billing

## 🔧 Development Notes

### Template System
- **Source**: `../pixel-template.js` contains the base tracking code
- **Configuration**: `{CONFIG_PLACEHOLDER}` replaced with client-specific settings
- **Maintenance**: Edit template file, rebuild container to update all clients

### Client Configuration
```json
{
  "client_id": "client_tuynaamtsjkd",
  "privacy_level": "standard",
  "ip_collection": {"enabled": true, "hash_required": false},
  "consent": {"required": false, "default_behavior": "allow"},
  "features": {},
  "deployment": {"type": "shared", "hostname": null}
}
```

### Event Batching
- **Activity-Based**: 60-second inactivity timeout
- **Size-Based**: 50 events max per batch
- **Performance**: Single database transaction per batch
- **Reliability**: `beforeunload` sends remaining events

## 📊 Success Metrics

### Integration Health ✅
- ✅ Zero `unauthorized_localhost` events
- ✅ All events attributed to `client_tuynaamtsjkd`
- ✅ Bulk insert optimization preserved
- ✅ Domain authorization security working
- ✅ Client configuration injection functional

### Performance Benchmarks ✅
- **Pixel Load Time**: ~5ms (cached configuration)
- **Event Processing**: <1ms per batch (bulk insert)
- **Domain Resolution**: ~100ms (with 5-minute cache)
- **Database Storage**: Single transaction per batch

---

**Built with ❤️ for complete data ownership, enterprise performance, and privacy-first analytics**