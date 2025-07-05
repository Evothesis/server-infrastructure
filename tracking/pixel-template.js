(function() {
    // Evothesis Analytics Pixel - Dynamically Generated
    // Configuration injected from server
    const config = {CONFIG_PLACEHOLDER};
    
    // Privacy compliance check
    if (config.consent && config.consent.required && !hasUserConsent()) {
        console.log('[Evothesis] Consent required - tracking blocked');
        return;
    }
    
    // Respect Do Not Track
    if (navigator.doNotTrack === '1' || window.doNotTrack === '1') {
        console.log('[Evothesis] Do Not Track enabled - respecting user preference');
        return;
    }
    
    // Core tracking configuration
    var trackingConfig = {
        apiEndpoint: config.apiEndpoint || '/collect',
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        batchTimeout: 60 * 1000, // 1 minute inactivity
        maxBatchSize: 50,
        privacyLevel: config.privacy_level || 'standard'
    };
    
    // Session management
    var sessionManager = {
        getSessionId: function() {
            var currentTime = Date.now();
            var sessionId = localStorage.getItem('_evothesis_session_id');
            var lastActivity = parseInt(localStorage.getItem('_evothesis_last_activity') || '0');
            
            // Check session timeout
            var sessionExpired = (currentTime - lastActivity) > trackingConfig.sessionTimeout;
            
            if (!sessionId || sessionExpired) {
                sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + 
                           Math.random().toString(36).substring(2, 15);
                localStorage.setItem('_evothesis_session_id', sessionId);
                localStorage.setItem('_evothesis_session_start', currentTime.toString());
            }
            
            localStorage.setItem('_evothesis_last_activity', currentTime.toString());
            return sessionId;
        },
        
        getVisitorId: function() {
            var visitorId = localStorage.getItem('_evothesis_visitor_id');
            if (!visitorId) {
                visitorId = 'vis_' + Math.random().toString(36).substring(2, 15) + 
                           Math.random().toString(36).substring(2, 15);
                localStorage.setItem('_evothesis_visitor_id', visitorId);
            }
            return visitorId;
        }
    };
    
    // Event batching system
    var eventBatcher = {
        batch: [],
        batchTimer: null,
        
        addEvent: function(eventType, eventData) {
            var event = {
                eventType: eventType,
                eventData: eventData || {},
                timestamp: new Date().toISOString()
            };
            
            this.batch.push(event);
            
            // Send immediately if batch is full
            if (this.batch.length >= trackingConfig.maxBatchSize) {
                this.sendBatch();
                return;
            }
            
            // Reset timer
            if (this.batchTimer) {
                clearTimeout(this.batchTimer);
            }
            
            // Set new timer
            this.batchTimer = setTimeout(() => {
                this.sendBatch();
            }, trackingConfig.batchTimeout);
        },
        
        sendBatch: function() {
            if (this.batch.length === 0) return;
            
            var batchData = {
                eventType: 'batch',
                sessionId: sessionManager.getSessionId(),
                visitorId: sessionManager.getVisitorId(),
                siteId: window.location.hostname,
                timestamp: new Date().toISOString(),
                events: this.batch.slice(), // Copy the batch
                privacy_level: config.privacy_level,
                page: {
                    title: document.title,
                    url: window.location.href,
                    path: window.location.pathname,
                    referrer: document.referrer || 'direct'
                }
            };
            
            // Apply privacy filters based on configuration
            if (config.privacy_level === 'gdpr' || config.privacy_level === 'hipaa') {
                batchData = this.applyPrivacyFilters(batchData);
            }
            
            this.sendToAPI(batchData);
            
            // Clear batch
            this.batch = [];
            if (this.batchTimer) {
                clearTimeout(this.batchTimer);
                this.batchTimer = null;
            }
        },
        
        applyPrivacyFilters: function(data) {
            // Remove or hash sensitive data based on privacy level
            if (config.ip_collection && !config.ip_collection.enabled) {
                // IP collection disabled - will be handled server-side
            }
            
            // Filter PII from event data
            data.events = data.events.map(function(event) {
                if (event.eventData && typeof event.eventData === 'object') {
                    var filtered = {};
                    for (var key in event.eventData) {
                        // Skip fields that might contain PII
                        if (!key.match(/(email|phone|ssn|credit|password|social)/i)) {
                            filtered[key] = event.eventData[key];
                        }
                    }
                    event.eventData = filtered;
                }
                return event;
            });
            
            return data;
        },
        
        sendToAPI: function(data) {
            // Use sendBeacon if available (better for page unload)
            if (navigator.sendBeacon) {
                navigator.sendBeacon(trackingConfig.apiEndpoint, JSON.stringify(data));
            } else {
                // Fallback to fetch
                fetch(trackingConfig.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data),
                    keepalive: true
                }).catch(function(error) {
                    console.warn('[Evothesis] Failed to send tracking data:', error);
                });
            }
        }
    };
    
    // Tracking functions
    var tracker = {
        trackPageView: function() {
            eventBatcher.addEvent('pageview', {
                page: {
                    title: document.title,
                    url: window.location.href,
                    path: window.location.pathname
                },
                attribution: this.getAttribution()
            });
        },
        
        getAttribution: function() {
            var params = new URLSearchParams(window.location.search);
            return {
                utm_source: params.get('utm_source'),
                utm_medium: params.get('utm_medium'),
                utm_campaign: params.get('utm_campaign'),
                utm_content: params.get('utm_content'),
                utm_term: params.get('utm_term'),
                referrer: document.referrer || 'direct'
            };
        }
    };
    
    // Initialize tracking based on enabled features
    if (config.features && config.features.page_tracking !== false) {
        // Track initial page view
        tracker.trackPageView();
        
        // Track click events
        if (config.features.click_tracking !== false) {
            document.addEventListener('click', function(event) {
                eventBatcher.addEvent('click', {
                    element: event.target.tagName.toLowerCase(),
                    id: event.target.id || null,
                    classes: event.target.className || null,
                    text: (event.target.innerText || '').substring(0, 100)
                });
            });
        }
        
        // Track scroll events
        if (config.features.scroll_tracking === true) {
            var scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    var scrollPercentage = Math.round(
                        (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
                    );
                    eventBatcher.addEvent('scroll', {
                        scroll_percentage: scrollPercentage
                    });
                }, 250);
            });
        }
        
        // Track form interactions
        if (config.features.form_tracking === true) {
            document.addEventListener('focus', function(event) {
                if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                    eventBatcher.addEvent('form_focus', {
                        field: event.target.name || event.target.id || 'unknown',
                        type: event.target.type || 'text'
                    });
                }
            }, true);
        }
    }
    
    // Send any remaining events before page unload
    window.addEventListener('beforeunload', function() {
        eventBatcher.sendBatch();
    });
    
    // Consent helper function
    function hasUserConsent() {
        // Check common consent management platforms
        if (typeof window.gtag !== 'undefined') {
            // Google Consent Mode
            return window.gtag('consent', 'query', 'analytics_storage') === 'granted';
        }
        
        // Check for basic consent cookie
        return document.cookie.indexOf('evothesis_consent=true') !== -1;
    }
    
    console.log('[Evothesis] Analytics pixel loaded for client:', config.client_id);
})();