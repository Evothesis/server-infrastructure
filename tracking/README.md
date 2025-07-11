# Tracking Pixel - Client-Attributed JavaScript Library

**High-performance analytics pixel with domain authorization and bulk event processing**

## 🚀 Overview

Client-specific JavaScript tracking library integrating with pixel-management for domain authorization and bulk event collection.

### Key Features
- **Client Attribution**: Automatic client resolution via domain authorization
- **Bulk Event Processing**: Intelligent batching for 50-100x performance improvement
- **Privacy Compliance**: Client-specific privacy settings (GDPR/HIPAA)
- **Domain Security**: Unauthorized domains blocked at pixel-management level

## 📁 File Structure

```
tracking/
├── js/
│   └── tracking.js         # Main tracking library
├── testing/
│   ├── index.html         # Demo integration site
│   ├── README.md          # Testing documentation
│   └── integration-test.js # Automated testing
└── README.md              # This documentation
```

## 🔧 Integration

### Client-Specific Pixel Loading
```html
<!-- Production integration (client-specific URL) -->
<script src="https://client-vm.evothesis.com/pixel/client_acme_corp/tracking.js"></script>

<!-- Development integration (shared testing) -->
<script src="http://localhost/pixel/client_test/tracking.js"></script>
```

### Manual Initialization
```javascript
// Advanced integration with custom configuration
window.EvothesisConfig = {
  client_id: 'client_acme_corp',
  endpoint: 'https://client-vm.evothesis.com/collect',
  batch_size: 20,
  flush_interval: 5000,
  privacy_mode: 'gdpr'  // 'standard', 'gdpr', 'hipaa'
};

// Load tracking script
const script = document.createElement('script');
script.src = '/js/tracking.js';
document.head.appendChild(script);
```

## ⚡ Performance Features

### Intelligent Event Batching
```javascript
// Automatic batching - events collected and sent together
evothesis.track('click', {element: 'button1'});      // Queued
evothesis.track('scroll', {depth: 25});              // Queued  
evothesis.track('form_focus', {field: 'email'});     // Queued
// ... all sent together in single request after 5s or 20 events
```

### Bulk Processing Flow
1. Events queued in memory with intelligent batching
2. Periodic flush (5s timeout) or size-based flush (20 events)
3. Single POST to `/collect` with `eventType: "batch"`
4. Server processes entire batch in single database transaction
5. 50-100x performance improvement vs. individual requests

## 📊 Event Types

### Core Events (Automatic)
```javascript
// Page views - automatically tracked
{
  eventType: 'pageview',
  page_data: {
    url: 'https://shop.acme.com/products',
    title: 'Product Catalog',
    referrer: 'https://google.com/search'
  }
}

// Form interactions - automatically tracked
{
  eventType: 'form_focus',
  event_data: {
    form_id: 'checkout_form',
    field: 'email',
    field_type: 'email'
  }
}
```

### Custom Events (Manual)
```javascript
// E-commerce tracking
evothesis.track('purchase', {
  order_id: 'ORD-12345',
  value: 299.99,
  currency: 'USD',
  items: [
    {product_id: 'PROD-001', quantity: 2, price: 149.99}
  ]
});

// User engagement
evothesis.track('video_play', {
  video_id: 'demo_video',
  duration: 180,
  quality: '1080p'
});

// Custom business events
evothesis.track('feature_used', {
  feature: 'advanced_search',
  user_tier: 'premium',
  usage_count: 15
});
```

## 🔒 Privacy & Compliance

### Automatic Privacy Protection
```javascript
// PII redaction (automatic)
{
  eventType: 'form_submit',
  event_data: {
    form_id: 'contact_form',
    fields: ['name', 'email', 'message'],  // Field names only
    // Values automatically filtered for PII
  }
}

// IP handling (client-specific)
// Standard: Full IP collected
// GDPR: IP automatically hashed before storage  
// HIPAA: Enhanced audit logging
```

### Client-Specific Privacy Settings
```javascript
// Retrieved from pixel-management during pixel load
const clientConfig = {
  privacy_level: 'gdpr',
  ip_collection: {
    enabled: true,
    hash_required: true,
    salt: 'client_specific_salt'
  },
  consent: {
    required: true,
    default_behavior: 'opt_out'
  }
};
```

## 🔧 Domain Authorization

### Security Flow
1. Pixel loads from client-specific URL: `/pixel/{client_id}/tracking.js`
2. Server validates requesting domain against pixel-management
3. Domain authorization: `GET /api/v1/config/domain/{domain}`
4. Authorized domains get client configuration, unauthorized get 404
5. All events auto-attributed to authorized client

### Authorization Testing
```bash
# Test authorized domain
curl https://pixel-management-url.run.app/api/v1/config/domain/shop.acme.com
# Response: {"client_id": "client_acme_corp", "privacy_level": "gdpr", ...}

# Test unauthorized domain  
curl https://pixel-management-url.run.app/api/v1/config/domain/evil-site.com
# Response: 404 Not Found

# Verify pixel serving
curl http://localhost/pixel/client_acme_corp/tracking.js
# Should include client-specific configuration
```

## 🧪 Testing & Development

### Local Development Setup
```bash
# Start development environment
cd server-infrastructure
docker compose --env-file .env.development up -d

# Access test site
open http://localhost

# Monitor event collection
docker compose logs -f fastapi | grep "Bulk inserted"
```

### Integration Testing
```bash
# Test single event
curl -X POST http://localhost:8000/collect \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "test_single",
    "sessionId": "test_session",
    "siteId": "localhost"
  }'

# Test batch processing
curl -X POST http://localhost:8000/collect \
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
curl http://localhost:8000/events/recent | jq '.[] | {eventType, client_id, siteId}'
```

### Browser Testing
1. Open `http://localhost` in browser
2. Check console: `[Evothesis] Analytics pixel loaded for client: client_test`
3. Interact with page (click, scroll, forms)
4. Monitor Network tab for `/collect` requests
5. Verify bulk batching in requests

## 📈 Performance Monitoring

### Client-Side Metrics
```javascript
// Access tracking statistics
console.log(evothesis.getStats());
// Output:
{
  events_queued: 15,
  events_sent: 45,
  batches_sent: 3,
  avg_batch_size: 15,
  last_flush: '2025-07-11T12:30:00Z'
}
```

### Server-Side Verification
```bash
# Monitor successful client attribution
docker compose logs fastapi | grep "client_test"

# Expected output:
# INFO:app.main:Processing batch with 3 individual events for client client_test
# INFO:app.main:Bulk inserted 4 events for client client_test from site localhost

# Verify bulk processing efficiency
docker compose logs fastapi | grep "Bulk inserted" | tail -10
```

## 🚀 Production Deployment

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

## 🔍 Troubleshooting

### Common Issues

**Events Not Being Collected**
```bash
# Check domain authorization
curl $PIXEL_MANAGEMENT_URL/api/v1/config/domain/your-domain.com

# Verify pixel accessibility
curl http://your-vm/pixel/your_client_id/tracking.js

# Check browser console for errors
```

**No Client Attribution**
```bash
# Verify pixel-management connectivity
docker compose logs fastapi | grep "pixel-management"

# Check domain in pixel-management system
# Ensure domain is added to client in admin interface

# Verify client_id in events
curl http://localhost:8000/events/recent | jq '.[] | select(.client_id == null)'
```

**Poor Performance**  
```bash
# Verify bulk batching
docker compose logs fastapi | grep "Processing batch"

# Check batch sizes (should be 5+ events)
docker compose logs fastapi | grep "batch with" | grep -o "with [0-9]*" | sort | uniq -c

# Monitor for individual event processing (should be minimal)
docker compose logs fastapi | grep -v "batch" | grep "Processing.*event"
```

---

**Built for enterprise-scale tracking with complete client attribution and privacy compliance**