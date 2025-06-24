# Tracking Pixel & Demo Site

This directory contains the core analytics tracking pixel and demonstration website. The tracking pixel is a production-ready JavaScript library for comprehensive behavioral analytics, while the demo site provides a testing environment to exercise all tracking capabilities.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Demo Website  │───▶│  tracking.js    │───▶│   FastAPI      │
│   Static HTML   │    │  Tracking Pixel │    │   /collect     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ User Interactions│    │  Event Batching │
│ • Page views    │    │  • Activity-based│
│ • Clicks        │    │  • Intelligent   │
│ • Form submits  │    │  • Performance   │
│ • Scroll depth  │    │  • Optimized     │
│ • Text copy     │    │                 │
└─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
tracking/
├── index.html          # Homepage with scroll tracking demo
├── products.html       # Product catalog with form testing
├── contact.html        # Contact page with form submissions
├── js/
│   └── tracking.js     # Comprehensive analytics tracking pixel
└── README.md          # This file
```

## 🎯 Demo Site Features

### Homepage (`index.html`)
**Purpose**: Comprehensive interaction testing and scroll depth analysis

**Testing Capabilities:**
- **Scroll Tracking**: Long-form content with 2000px+ height for milestone testing
- **Click Events**: Multiple button types (primary CTA, secondary actions, navigation links)
- **Text Selection**: Highlighted copyable content sections for copy event testing
- **File Downloads**: Simulated download links (PDF, images, ZIP files)
- **Page Visibility**: Tab switching and focus/blur event testing

**Content Sections:**
- Navigation with UTM parameter test links
- Call-to-action buttons with different event triggers
- Highlighted text blocks designed for copy testing
- Scroll milestone markers at 25%, 50%, 75%, and 100%
- Gradient background sections for visual scroll progress

### Products Page (`products.html`)
**Purpose**: E-commerce interaction simulation and form testing

**Testing Capabilities:**
- **Product Interactions**: "Add to Cart" and "View Details" button clicks
- **Form Submissions**: Complex multi-field product inquiry form
- **Field Validation**: Required fields, email validation, dropdown selections
- **UTM Tracking**: Campaign parameter testing via navigation links

**Form Fields Tested:**
- Text inputs (name, email, phone)
- Email validation
- Dropdown selections (product choice, budget range)
- Textarea for long-form content
- Form submission with JavaScript prevention for testing

### Contact Page (`contact.html`)
**Purpose**: Lead generation form testing and contact interaction simulation

**Testing Capabilities:**
- **Contact Form**: Standard contact form with validation
- **Information Display**: Contact details for business context
- **Form Validation**: Required field testing and submission handling

## 🔬 Tracking Pixel (`tracking.js`)

### Core Tracking Engine

The tracking pixel is a sophisticated analytics library providing comprehensive behavioral tracking without external dependencies.

**Key Features:**
- **Zero Dependencies**: Pure JavaScript, no external libraries required
- **Privacy-Focused**: Respects Do Not Track, automatic PII redaction
- **Performance Optimized**: Activity-based batching, throttled event processing
- **Cross-Platform**: Works across modern browsers with graceful fallbacks

### Session Management

```javascript
// Unified session management across browser tabs
var getSessionId = function() {
    var currentTime = Date.now();
    var sessionId = localStorage.getItem('_ts_session_id');
    var lastActivity = parseInt(localStorage.getItem('_ts_last_activity') || '0');
    
    // 30-minute session timeout
    var sessionExpired = (currentTime - lastActivity) > config.sessionTimeout;
    
    if (!sessionId || sessionExpired) {
        // Generate new session ID
        sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + 
                    Math.random().toString(36).substring(2, 15);
        localStorage.setItem('_ts_session_id', sessionId);
        localStorage.setItem('_ts_session_start', currentTime.toString());
    }
    
    // Update activity timestamp
    localStorage.setItem('_ts_last_activity', currentTime.toString());
    return sessionId;
};
```

**Session Features:**
- Cross-tab session persistence using localStorage
- 30-minute inactivity timeout (configurable)
- Automatic session renewal on user activity
- Unique visitor ID generation and persistence

### Event Tracking Capabilities

#### 1. Page View Tracking
```javascript
// Comprehensive page view data collection
var trackPageView = function() {
    sendImmediate('pageview', {
        page: {
            title: document.title,
            url: window.location.href,
            path: window.location.pathname,
            referrer: document.referrer || 'direct'
        },
        attribution: getCurrentPageAttribution(),
        browser: getBrowserData()
    });
};
```

**Collected Data:**
- Full page metadata (title, URL, path, referrer)
- UTM campaign parameters (source, medium, campaign, content, term)
- Referrer classification (direct, search, social, referral, internal)
- Browser and device information (screen size, viewport, language, timezone)

#### 2. User Interaction Events
```javascript
// Click tracking with element details
document.addEventListener('click', function(event) {
    var element = event.target;
    var eventData = {
        tagName: element.tagName.toLowerCase(),
        classes: element.className || '',
        id: element.id || '',
        href: element.href || '',
        text: (element.innerText || '').substring(0, 100),
        position: { x: event.clientX, y: event.clientY }
    };
    
    // Detect file downloads
    if (element.href && element.href.match(/\.(pdf|doc|xls|zip|jpg|png|mp4)$/i)) {
        eventData.fileType = element.href.split('.').pop().toLowerCase();
        eventData.isDownload = true;
    }
    
    addToBatch('click', eventData);
});
```

**Interaction Types:**
- **Click Events**: Element details, position, download detection
- **Form Submissions**: Field data with automatic PII redaction
- **Text Selection**: Copy events with text length and preview
- **Scroll Tracking**: Continuous scroll position and milestone achievements
- **Page Visibility**: Focus/blur events with time spent calculations

#### 3. Scroll Depth Analytics
```javascript
var scrollDepthTracking = {
    milestones: [25, 50, 75, 100], // Configurable percentages
    
    trackScroll: function() {
        var scrollPercentage = Math.round((scrollTop / scrollableHeight) * 100);
        
        // Check milestone achievements
        config.scrollMilestones.forEach(function(milestone) {
            if (!this.milestones[milestone] && scrollPercentage >= milestone) {
                this.milestones[milestone] = true;
                
                addToBatch('scroll_depth', {
                    milestone: milestone,
                    timeToMilestone: Date.now() - pageStart,
                    scrollPercentage: scrollPercentage
                });
            }
        });
    }
};
```

**Scroll Features:**
- Milestone tracking (25%, 50%, 75%, 100%)
- Time-to-milestone measurement
- Throttled scroll event processing (100ms intervals)
- Maximum scroll depth tracking

#### 4. Form Analytics
```javascript
// Comprehensive form submission tracking
document.addEventListener('submit', function(event) {
    var form = event.target;
    var formData = {};
    var excludedFields = ['password', 'credit', 'card', 'cvv', 'ssn'];
    
    // Process form fields with PII protection
    for (var i = 0; i < form.elements.length; i++) {
        var element = form.elements[i];
        
        if (isExcludedField(element)) {
            formData[element.name] = '[REDACTED]';
        } else {
            formData[element.name] = element.value;
        }
    }
    
    sendImmediate('form_submit', {
        formId: form.id || 'unknown',
        formAction: form.action,
        formData: formData
    });
});
```

**Form Features:**
- Automatic PII redaction (passwords, credit cards, SSNs)
- Field-level data collection
- Form metadata (ID, action, method)
- Checkbox and radio button state tracking

### Attribution & Campaign Tracking

#### UTM Parameter Processing
```javascript
var getUtmParams = function() {
    var params = getUrlParams();
    return {
        utm_source: params.utm_source || null,
        utm_medium: params.utm_medium || null,
        utm_campaign: params.utm_campaign || null,
        utm_content: params.utm_content || null,
        utm_term: params.utm_term || null
    };
};
```

#### Referrer Classification
```javascript
var classifyReferrer = function(referrer) {
    var hostname = new URL(referrer).hostname.toLowerCase();
    
    // Search engines
    if (hostname.includes('google.')) return { type: 'search', platform: 'google' };
    if (hostname.includes('bing.')) return { type: 'search', platform: 'bing' };
    
    // Social platforms  
    if (hostname.includes('facebook.')) return { type: 'social', platform: 'facebook' };
    if (hostname.includes('twitter.')) return { type: 'social', platform: 'twitter' };
    
    // Internal/external referrals
    if (hostname === window.location.hostname) return { type: 'internal' };
    return { type: 'referral', platform: hostname };
};
```

**Attribution Features:**
- Automatic UTM parameter extraction
- Intelligent referrer classification (search, social, referral, direct)
- Campaign tracking ID support (Google, Facebook, Microsoft, Twitter)
- First-touch attribution preservation

### Performance Optimization

#### Activity-Based Batching
```javascript
var eventBatch = [];
var inactivityTimer = null;

var activityManager = {
    recordActivity: function() {
        lastActivityTime = Date.now();
        this.resetInactivityTimer();
    },
    
    resetInactivityTimer: function() {
        if (inactivityTimer) clearTimeout(inactivityTimer);
        
        if (eventBatch.length > 0) {
            inactivityTimer = setTimeout(function() {
                sendBatch(); // Send after 1 minute of inactivity
            }, config.inactivityTimeout);
        }
    }
};
```

**Batching Features:**
- Intelligent event grouping based on user activity
- 60-second inactivity timeout (configurable)
- Maximum batch size protection (50 events default)
- Automatic batch sending on page exit

#### Browser Compatibility
```javascript
// Modern fetch with XMLHttpRequest fallback
var sendData = function(payload) {
    if (window.fetch) {
        fetch(config.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true // Ensures delivery during page unload
        });
    } else {
        // Fallback for older browsers
        var xhr = new XMLHttpRequest();
        xhr.open('POST', config.endpoint, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify(payload));
    }
};
```

## ⚙️ Configuration

### Tracking Configuration
```javascript
var config = {
    endpoint: '/collect',
    sessionTimeout: 30 * 60 * 1000,     // 30 minutes
    inactivityTimeout: 60 * 1000,       // 1 minute batch timeout
    maxBatchSize: 50,                   // Events per batch
    scrollMilestones: [25, 50, 75, 100], // Scroll tracking percentages
    
    // Feature toggles
    trackClicks: true,
    trackForms: true,
    trackPageViews: true,
    trackScrollDepth: true,
    trackTextSelection: true,
    trackPageVisibility: true,
    
    sampleRate: 100  // Track 100% of visitors
};
```

### Site ID Detection
```javascript
// Automatic site identification from hostname
var getSiteId = function() {
    var hostname = window.location.hostname;
    var cleanHostname = hostname.replace(/^(www\.|m\.|mobile\.)/, '');
    return cleanHostname.replace(/\./g, '-');
};
```

## 🧪 Testing Workflows

### Manual Testing Procedures

**Important**: Use a real web browser for testing, as command-line tools like `curl` or PowerShell's `Invoke-WebRequest` do not execute JavaScript and will not trigger the tracking pixel.

**1. Basic Page View Testing**
```bash
# 1. Visit homepage in browser: http://localhost
# 2. Check console logs for tracking initialization
# 3. Verify event collection
curl http://localhost:8000/events/recent
```

**2. Interaction Testing**
```bash
# Test sequence:
1. Click navigation links
2. Click CTA buttons 
3. Select and copy text content
4. Submit forms with various data
5. Scroll through entire page
6. Switch browser tabs (visibility tracking)

# Verify events collected:
curl http://localhost:8000/events/recent
```

**3. Form Submission Testing**
```bash
# Test both forms:
1. Products page inquiry form
2. Contact page submission form

# Verify form data (check PII redaction):
curl http://localhost:8000/events/recent | jq '.events[] | select(.event_type=="form_submit")'
```

**4. Attribution Testing**
```bash
# Test UTM parameters:
http://localhost/products.html?utm_source=google&utm_medium=cpc&utm_campaign=test

# Test referrer classification:
# - Direct navigation
# - Social media referrers
# - Search engine referrers
```

### Automated Testing Integration

**JavaScript Console Testing**
```javascript
// Check tracking configuration
console.log(config);

// Check session information
console.log('Session ID:', localStorage.getItem('_ts_session_id'));
console.log('Visitor ID:', localStorage.getItem('_ts_visitor_id'));

// Manually trigger events
addToBatch('test_event', { test: true });
sendBatch();
```

**Browser Developer Tools**
```javascript
// Monitor network requests
// Filter by: /collect
// Check request payloads and response codes

// Check localStorage
localStorage.getItem('_ts_session_id');
localStorage.getItem('_ts_visitor_id');
localStorage.getItem('_ts_last_activity');
```

## 🔒 Privacy & Compliance

### Data Protection Features

**Automatic PII Redaction:**
```javascript
var excludedFields = ['password', 'credit', 'card', 'cvv', 'ssn', 'social'];

// Field name checking
var isExcludedField = function(element) {
    return excludedFields.some(function(term) {
        return element.name.toLowerCase().indexOf(term) !== -1 ||
               (element.id && element.id.toLowerCase().indexOf(term) !== -1);
    });
};
```

**Do Not Track Respect:**
```javascript
// Check for Do Not Track preference
if (navigator.doNotTrack === '1' || window.doNotTrack === '1') {
    console.info('[Tracking] Respecting Do Not Track setting');
    return; // Exit without initializing tracking
}
```

**Anonymous Tracking:**
- Visitor IDs are randomly generated, not tied to personal information
- Session IDs are ephemeral and reset after timeout
- No cross-site tracking capabilities
- No fingerprinting techniques used

### GDPR Compliance Features

**Consent Integration Points:**
```javascript
// Example consent management integration
if (typeof window.gtag !== 'undefined') {
    // Integration with Google Consent Mode
    gtag('consent', 'update', {
        'analytics_storage': 'granted'
    });
}

// Custom consent check
if (window.userConsent && !window.userConsent.analytics) {
    console.info('[Tracking] Analytics consent not granted');
    return;
}
```

## 🚨 Troubleshooting

### Common Issues

**Tracking Not Working:**
```javascript
// Check console for errors
// Look for: "[Tracking] Analytics initialized successfully"

// Verify browser storage support
if (!window.localStorage || !window.sessionStorage) {
    console.warn('[Tracking] Browser storage not supported');
}

// Check endpoint accessibility  
fetch('/collect', { method: 'HEAD' })
    .then(response => console.log('Endpoint status:', response.status));
```

**Events Not Being Sent:**
```javascript
// Check batch status
console.log('Current batch size:', eventBatch.length);
console.log('Last activity:', new Date(lastActivityTime));

// Force batch send
sendBatch();

// Check network connectivity
navigator.onLine; // true/false
```

**Session Issues:**
```javascript
// Clear session data for testing
localStorage.removeItem('_ts_session_id');
localStorage.removeItem('_ts_visitor_id');
localStorage.removeItem('_ts_last_activity');

// Reinitialize tracking
location.reload();
```

### Debug Mode

**Enable Verbose Logging:**
```javascript
// Add to tracking.js config
var config = {
    debug: true,  // Enable debug logging
    // ... other config
};

// Or via browser console
window.trackingDebug = true;
```

**Performance Monitoring:**
```javascript
// Monitor event processing time
console.time('batch-processing');
sendBatch();
console.timeEnd('batch-processing');

// Check memory usage
console.log('Event batch memory:', JSON.stringify(eventBatch).length, 'bytes');
```

## 🚀 Integration Guide

### Adding to Existing Websites

**Basic Integration:**
```html
<!-- Add before closing </body> tag -->
<script src="/js/tracking.js"></script>
```

**Custom Configuration:**
```html
<script>
window.analyticsConfig = {
    endpoint: 'https://analytics.yourdomain.com/collect',
    siteId: 'your-site-id',
    trackScrollDepth: true,
    scrollMilestones: [10, 25, 50, 75, 90, 100],
    sessionTimeout: 45 * 60 * 1000, // 45 minutes
    maxBatchSize: 25 // Smaller batches for lower traffic sites
};
</script>
<script src="/js/tracking.js"></script>
```

**WordPress Integration:**
```php
// Add to functions.php
function add_analytics_tracking() {
    if (!is_admin()) {
        wp_enqueue_script(
            'analytics-tracking',
            get_template_directory_uri() . '/js/tracking.js',
            array(),
            '1.0',
            true // Load in footer
        );
    }
}
add_action('wp_enqueue_scripts', 'add_analytics_tracking');
```

**React/SPA Integration:**
```javascript
// For single-page applications
import { useEffect } from 'react';

const AnalyticsProvider = ({ children }) => {
    useEffect(() => {
        // Load tracking script
        const script = document.createElement('script');
        script.src = '/js/tracking.js';
        script.async = true;
        document.body.appendChild(script);

        // Handle route changes
        const handleRouteChange = () => {
            if (window.trackPageView) {
                window.trackPageView();
            }
        };

        // Listen for route changes (adjust for your router)
        window.addEventListener('popstate', handleRouteChange);
        
        return () => {
            window.removeEventListener('popstate', handleRouteChange);
        };
    }, []);

    return children;
};
```

### E-commerce Tracking Extensions

**Purchase Tracking:**
```javascript
// Extend tracking.js for e-commerce events
var trackPurchase = function(orderData) {
    sendImmediate('purchase', {
        orderId: orderData.id,
        revenue: orderData.total,
        currency: orderData.currency || 'USD',
        items: orderData.items.map(function(item) {
            return {
                sku: item.sku,
                name: item.name,
                category: item.category,
                quantity: item.quantity,
                price: item.price
            };
        })
    });
};

// Cart events
var trackAddToCart = function(item) {
    addToBatch('add_to_cart', {
        sku: item.sku,
        name: item.name,
        price: item.price,
        quantity: item.quantity || 1
    });
};

// Usage example
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('add-to-cart-btn')) {
        var sku = event.target.dataset.sku;
        var name = event.target.dataset.name;
        var price = parseFloat(event.target.dataset.price);
        
        trackAddToCart({ sku: sku, name: name, price: price });
    }
});
```

## 📊 Analytics Data Structure

### Event Payload Format

**Standard Event Structure:**
```json
{
  "eventType": "pageview",
  "timestamp": "2025-06-22T12:00:00.123Z",
  "sessionId": "sess_abc123def456",
  "visitorId": "vis_xyz789uvw012",
  "siteId": "example-com",
  "url": "https://example.com/products",
  "path": "/products",
  "eventData": {
    "page": {
      "title": "Products - Example Site",
      "referrer": "https://google.com/search?q=example",
      "queryParams": "?utm_source=google&utm_medium=cpc"
    },
    "attribution": {
      "utmParams": {
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "summer_sale"
      },
      "referrerType": "search",
      "referrerPlatform": "google"
    },
    "browser": {
      "userAgent": "Mozilla/5.0...",
      "language": "en-US",
      "screenWidth": 1920,
      "screenHeight": 1080,
      "viewportWidth": 1200,
      "viewportHeight": 800,
      "timezone": "America/New_York"
    }
  }
}
```

**Batch Event Structure:**
```json
{
  "eventType": "batch",
  "timestamp": "2025-06-22T12:05:00.456Z",
  "sessionId": "sess_abc123def456",
  "visitorId": "vis_xyz789uvw012",
  "siteId": "example-com",
  "batchMetadata": {
    "eventCount": 15,
    "batchStartTime": "2025-06-22T12:01:00.123Z",
    "batchEndTime": "2025-06-22T12:04:59.789Z",
    "activityDuration": 239000,
    "sentOnExit": false
  },
  "events": [
    {
      "eventType": "click",
      "timestamp": "2025-06-22T12:01:15.234Z",
      "eventData": {
        "tagName": "button",
        "classes": "btn btn-primary",
        "id": "add-to-cart",
        "text": "Add to Cart",
        "position": { "x": 450, "y": 300 }
      }
    },
    {
      "eventType": "scroll_depth",
      "timestamp": "2025-06-22T12:02:30.567Z",
      "eventData": {
        "milestone": 50,
        "timeToMilestone": 75333,
        "scrollPercentage": 52
      }
    }
  ]
}
```

### Form Submission Data
```json
{
  "eventType": "form_submit",
  "timestamp": "2025-06-22T12:03:45.890Z",
  "sessionId": "sess_abc123def456",
  "eventData": {
    "formId": "contact-form",
    "formAction": "/submit-contact",
    "formMethod": "post",
    "formData": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "555-1234",
      "password": "[REDACTED]",
      "message": "Interested in your products"
    }
  }
}
```

## 🎛️ Advanced Configuration

### Custom Event Types

**Define Custom Events:**
```javascript
// Add to tracking.js or separate config file
var customEventTypes = {
    video_play: {
        immediate: true, // Send immediately, don't batch
        data: ['videoId', 'videoTitle', 'position']
    },
    document_download: {
        immediate: true,
        data: ['filename', 'fileType', 'fileSize']
    },
    search_performed: {
        immediate: false, // Can be batched
        data: ['query', 'resultCount', 'filters']
    }
};

// Custom event tracking functions
var trackVideoPlay = function(videoId, title, position) {
    var eventData = {
        videoId: videoId,
        videoTitle: title,
        position: position || 0
    };
    
    if (customEventTypes.video_play.immediate) {
        sendImmediate('video_play', eventData);
    } else {
        addToBatch('video_play', eventData);
    }
};

// Usage
document.addEventListener('play', function(event) {
    if (event.target.tagName === 'VIDEO') {
        trackVideoPlay(
            event.target.id || 'unknown',
            event.target.title || 'untitled',
            event.target.currentTime
        );
    }
});
```

### Performance Monitoring Integration

**Core Web Vitals Tracking:**
```javascript
// Add performance tracking to tracking.js
var trackWebVitals = function() {
    if ('PerformanceObserver' in window) {
        // Largest Contentful Paint
        new PerformanceObserver(function(list) {
            for (var entry of list.getEntries()) {
                addToBatch('web_vital', {
                    metric: 'LCP',
                    value: entry.startTime,
                    element: entry.element ? entry.element.tagName : null
                });
            }
        }).observe({ entryTypes: ['largest-contentful-paint'] });

        // First Input Delay
        new PerformanceObserver(function(list) {
            for (var entry of list.getEntries()) {
                addToBatch('web_vital', {
                    metric: 'FID',
                    value: entry.processingStart - entry.startTime,
                    eventType: entry.name
                });
            }
        }).observe({ entryTypes: ['first-input'] });

        // Cumulative Layout Shift
        new PerformanceObserver(function(list) {
            var clsValue = 0;
            for (var entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                }
            }
            if (clsValue > 0) {
                addToBatch('web_vital', {
                    metric: 'CLS',
                    value: clsValue
                });
            }
        }).observe({ entryTypes: ['layout-shift'] });
    }
};
```

### A/B Testing Integration

**Experiment Tracking:**
```javascript
// A/B test variant tracking
var trackExperiment = function(experimentId, variantId, userId) {
    sendImmediate('experiment_view', {
        experimentId: experimentId,
        variantId: variantId,
        userId: userId || getVisitorId()
    });
};

// Conversion tracking for experiments
var trackExperimentConversion = function(experimentId, conversionType) {
    sendImmediate('experiment_conversion', {
        experimentId: experimentId,
        conversionType: conversionType,
        timestamp: new Date().toISOString()
    });
};

// Example usage with a simple A/B test
var runButtonColorTest = function() {
    var variants = ['red', 'blue', 'green'];
    var selectedVariant = variants[Math.floor(Math.random() * variants.length)];
    
    // Apply variant
    var button = document.getElementById('cta-button');
    if (button) {
        button.className += ' variant-' + selectedVariant;
        trackExperiment('button_color_test', selectedVariant);
        
        // Track conversion on button click
        button.addEventListener('click', function() {
            trackExperimentConversion('button_color_test', 'button_click');
        });
    }
};
```

## 🔧 Development & Customization

### Code Structure Overview

**Main Components:**
```javascript
// Configuration and utilities
var config = { /* tracking configuration */ };
var getSessionId = function() { /* session management */ };
var getVisitorId = function() { /* visitor identification */ };

// Attribution and browser detection
var getUtmParams = function() { /* UTM parameter extraction */ };
var classifyReferrer = function() { /* referrer classification */ };
var getBrowserData = function() { /* device/browser info */ };

// Event batching and sending
var eventBatch = [];
var addToBatch = function() { /* batch management */ };
var sendBatch = function() { /* network transmission */ };

// Activity monitoring
var activityManager = { /* user activity detection */ };

// Event type handlers
var trackPageView = function() { /* page view tracking */ };
var trackClicks = function() { /* click event setup */ };
var trackForms = function() { /* form submission setup */ };
var scrollDepthTracking = { /* scroll tracking */ };
```

### Adding New Tracking Features

**Step 1: Define the Feature**
```javascript
// Add to config
var config = {
    // existing config...
    trackModalInteractions: true, // New feature toggle
    modalEvents: ['open', 'close', 'submit'] // Feature configuration
};
```

**Step 2: Implement Event Handlers**
```javascript
var trackModals = function() {
    if (!config.trackModalInteractions) return;
    
    document.addEventListener('click', function(event) {
        var target = event.target;
        
        // Modal trigger detection
        if (target.dataset.toggle === 'modal') {
            addToBatch('modal_open', {
                modalId: target.dataset.target || 'unknown',
                triggerElement: target.tagName.toLowerCase(),
                triggerText: target.innerText || target.value || ''
            });
        }
        
        // Modal close detection
        if (target.classList.contains('modal-close') || target.dataset.dismiss === 'modal') {
            addToBatch('modal_close', {
                modalId: getActiveModalId(),
                closeMethod: target.dataset.dismiss ? 'button' : 'overlay'
            });
        }
    });
    
    // Modal form submissions
    document.addEventListener('submit', function(event) {
        var form = event.target;
        var modal = form.closest('.modal');
        
        if (modal) {
            addToBatch('modal_submit', {
                modalId: modal.id || 'unknown',
                formId: form.id || 'unknown',
                formAction: form.action || window.location.href
            });
        }
    });
};
```

**Step 3: Initialize in Main Function**
```javascript
var init = function() {
    // existing initialization...
    trackModals(); // Add new feature
    // rest of initialization...
};
```

### Testing New Features

**Unit Testing Framework:**
```javascript
// Simple testing framework for tracking features
var TrackingTests = {
    tests: {},
    results: [],
    
    addTest: function(name, testFunction) {
        this.tests[name] = testFunction;
    },
    
    runTest: function(name) {
        try {
            var result = this.tests[name]();
            this.results.push({ name: name, passed: result, error: null });
            console.log('✅ Test passed:', name);
            return result;
        } catch (error) {
            this.results.push({ name: name, passed: false, error: error.message });
            console.error('❌ Test failed:', name, error.message);
            return false;
        }
    },
    
    runAll: function() {
        console.log('🧪 Running tracking tests...');
        for (var testName in this.tests) {
            this.runTest(testName);
        }
        
        var passed = this.results.filter(function(r) { return r.passed; }).length;
        var total = this.results.length;
        console.log(`📊 Tests completed: ${passed}/${total} passed`);
        
        return this.results;
    }
};

// Example tests
TrackingTests.addTest('session_id_generation', function() {
    var sessionId = getSessionId();
    return sessionId && sessionId.startsWith('sess_') && sessionId.length > 10;
});

TrackingTests.addTest('visitor_id_persistence', function() {
    var visitorId1 = getVisitorId();
    var visitorId2 = getVisitorId();
    return visitorId1 === visitorId2;
});

TrackingTests.addTest('utm_parameter_extraction', function() {
    var testUrl = 'https://example.com?utm_source=test&utm_medium=email';
    var params = getUrlParams(testUrl);
    return params.utm_source === 'test' && params.utm_medium === 'email';
});

// Run tests in browser console
// TrackingTests.runAll();
```

## 📚 Best Practices

### Implementation Guidelines

**1. Privacy-First Approach**
- Always respect Do Not Track preferences
- Implement automatic PII redaction
- Use minimal data collection
- Provide clear opt-out mechanisms

**2. Performance Optimization**
- Use event batching to reduce network requests
- Implement activity-based sending logic
- Throttle high-frequency events (scroll, mousemove)
- Use passive event listeners where possible

**3. Error Handling**
- Never block page functionality due to tracking errors
- Implement graceful fallbacks for unsupported browsers
- Log errors for debugging but don't expose to users
- Use try-catch blocks around all tracking code

**4. Data Quality**
- Validate data before sending
- Use consistent naming conventions
- Implement data sanitization
- Provide fallback values for missing data

### Production Deployment Checklist

**Pre-Deployment:**
- [ ] Test all tracking features on staging environment
- [ ] Verify PII redaction is working correctly
- [ ] Check performance impact with browser profiling
- [ ] Validate event data structure matches backend expectations
- [ ] Test with Do Not Track enabled
- [ ] Verify CORS configuration for production domains

**Configuration Review:**
- [ ] Update endpoint URL for production
- [ ] Set appropriate batch sizes for expected traffic
- [ ] Configure session timeout for your use case
- [ ] Review scroll milestones for your content
- [ ] Set appropriate sample rate if needed

**Monitoring Setup:**
- [ ] Set up alerts for high error rates
- [ ] Monitor event collection volume
- [ ] Track page load performance impact
- [ ] Set up regular data quality checks

---

**For additional documentation:**
- Main project: [../README.md](../README.md)
- Backend API: [../api/README.md](../api/README.md)
- Database schema: [../database/README.md](../database/README.md)
- ETL testing: [../tests/etl_test.py](../tests/etl_test.py)