(function() {
  // Configuration
  var config = {
    endpoint: '/collect',  // Relative URL since nginx proxies to FastAPI
    sessionTimeout: 30 * 60 * 1000, // 30 minutes
    trackClicks: true,
    trackForms: true,
    trackPageViews: true,
    trackScrollDepth: true,
    trackTextSelection: true,
    trackPageVisibility: true,
    sampleRate: 100, // Track 100% of visitors
    
    // Activity-based batching configuration
    inactivityTimeout: 60 * 1000, // Send batch after 1 minute of inactivity
    maxBatchSize: 50,
    batchOnExit: true,
    
    // Scroll tracking configuration
    scrollMilestones: [25, 50, 75, 100],
    scrollThrottle: 100 // ms
  };

  // Auto-detect site ID from hostname
  var getSiteId = function() {
    var hostname = window.location.hostname;
    var cleanHostname = hostname.replace(/^(www\.|m\.|mobile\.)/, '');
    return cleanHostname.replace(/\./g, '-');
  };

  config.siteId = getSiteId();

  // Generate unified session ID (shared across tabs)
  var getSessionId = function() {
    var currentTime = Date.now();
    var sessionId = localStorage.getItem('_ts_session_id');
    var sessionStart = parseInt(localStorage.getItem('_ts_session_start') || '0');
    var lastActivity = parseInt(localStorage.getItem('_ts_last_activity') || '0');
    
    // Check if session has expired
    var sessionExpired = (currentTime - lastActivity) > config.sessionTimeout;
    
    if (!sessionId || sessionExpired) {
      // Create new session
      sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + 
                  Math.random().toString(36).substring(2, 15);
      localStorage.setItem('_ts_session_id', sessionId);
      localStorage.setItem('_ts_session_start', currentTime.toString());
      
      console.log('[Tracking] New session created:', sessionId);
    }
    
    // Update last activity time
    localStorage.setItem('_ts_last_activity', currentTime.toString());
    
    return sessionId;
  };

  // Generate visitor ID
  var getVisitorId = function() {
    var visitorId = localStorage.getItem('_ts_visitor_id');
    if (!visitorId) {
      visitorId = 'vis_' + Math.random().toString(36).substring(2, 15) + 
                  Math.random().toString(36).substring(2, 15);
      localStorage.setItem('_ts_visitor_id', visitorId);
    }
    return visitorId;
  };

  // Parse URL parameters
  var getUrlParams = function(url) {
    var params = {};
    try {
      var urlObj = new URL(url || window.location.href);
      urlObj.searchParams.forEach(function(value, key) {
        params[key.toLowerCase()] = value;
      });
    } catch (e) {
      // Fallback for older browsers
      var queryString = (url || window.location.search).split('?')[1] || '';
      var pairs = queryString.split('&');
      for (var i = 0; i < pairs.length; i++) {
        var pair = pairs[i].split('=');
        if (pair.length === 2) {
          params[decodeURIComponent(pair[0]).toLowerCase()] = decodeURIComponent(pair[1]);
        }
      }
    }
    return params;
  };

  // Extract UTM parameters
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

  // Extract campaign tracking parameters
  var getCampaignParams = function() {
    var params = getUrlParams();
    return {
      // Google
      gclid: params.gclid || null,
      gclsrc: params.gclsrc || null,
      
      // Facebook
      fbclid: params.fbclid || null,
      
      // Microsoft/Bing
      msclkid: params.msclkid || null,
      
      // Other platforms
      twclid: params.twclid || null,
      ttclid: params.ttclid || null
    };
  };

  // Simplified referrer classification
  var classifyReferrer = function(referrer) {
    if (!referrer) return { type: 'direct', platform: null };
    
    try {
      var hostname = new URL(referrer).hostname.toLowerCase();
      
      // Major search engines
      if (hostname.includes('google.')) return { type: 'search', platform: 'google' };
      if (hostname.includes('bing.')) return { type: 'search', platform: 'bing' };
      if (hostname.includes('yahoo.')) return { type: 'search', platform: 'yahoo' };
      if (hostname.includes('duckduckgo.')) return { type: 'search', platform: 'duckduckgo' };
      
      // Major social platforms
      if (hostname.includes('facebook.') || hostname.includes('fb.')) return { type: 'social', platform: 'facebook' };
      if (hostname.includes('twitter.') || hostname === 't.co') return { type: 'social', platform: 'twitter' };
      if (hostname.includes('linkedin.')) return { type: 'social', platform: 'linkedin' };
      if (hostname.includes('youtube.') || hostname === 'youtu.be') return { type: 'social', platform: 'youtube' };
      if (hostname.includes('instagram.')) return { type: 'social', platform: 'instagram' };
      if (hostname.includes('tiktok.')) return { type: 'social', platform: 'tiktok' };
      if (hostname.includes('reddit.')) return { type: 'social', platform: 'reddit' };
      if (hostname.includes('pinterest.')) return { type: 'social', platform: 'pinterest' };
      
      // Same domain (internal)
      if (hostname === window.location.hostname) return { type: 'internal', platform: hostname };
      
      // Everything else is referral
      return { type: 'referral', platform: hostname };
    } catch (e) {
      return { type: 'unknown', platform: null };
    }
  };

  // Get current page attribution (simplified)
  var getCurrentPageAttribution = function() {
    var utmParams = getUtmParams();
    var campaignParams = getCampaignParams();
    var referrer = document.referrer;
    var referrerData = classifyReferrer(referrer);
    
    return {
      utmParams: utmParams,
      campaignParams: campaignParams,
      referrer: referrer,
      referrerType: referrerData.type,
      referrerPlatform: referrerData.platform
    };
  };

  // Get browser/device data
  var getBrowserData = function() {
    return {
      userAgent: navigator.userAgent,
      language: navigator.language || navigator.browserLanguage || 'unknown',
      screenWidth: window.screen ? window.screen.width : 0,
      screenHeight: window.screen ? window.screen.height : 0,
      viewportWidth: window.innerWidth || 0,
      viewportHeight: window.innerHeight || 0,
      devicePixelRatio: window.devicePixelRatio || 1,
      timezone: Intl.DateTimeFormat ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'unknown'
    };
  };

  // Activity-based event batching system
  var eventBatch = [];
  var inactivityTimer = null;
  var lastActivityTime = Date.now();

  // Activity detection and timer management
  var activityManager = {
    recordActivity: function() {
      lastActivityTime = Date.now();
      this.resetInactivityTimer();
    },
    
    resetInactivityTimer: function() {
      if (inactivityTimer) {
        clearTimeout(inactivityTimer);
      }
      
      if (eventBatch.length > 0) {
        inactivityTimer = setTimeout(function() {
          console.log('[Tracking] Sending batch due to 1 minute inactivity');
          sendBatch();
        }, config.inactivityTimeout);
      }
    },
    
    initActivityListeners: function() {
      var self = this;
      
      // Mouse and keyboard activity
      document.addEventListener('mousemove', function() { self.recordActivity(); }, { passive: true });
      document.addEventListener('mousedown', function() { self.recordActivity(); }, { passive: true });
      document.addEventListener('keydown', function() { self.recordActivity(); }, { passive: true });
      document.addEventListener('scroll', function() { self.recordActivity(); }, { passive: true });
      document.addEventListener('touchstart', function() { self.recordActivity(); }, { passive: true });
      
      // Window focus/blur
      window.addEventListener('focus', function() { self.recordActivity(); });
      document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
          self.recordActivity();
        }
      });
    }
  };

  // Send batched events
  var sendBatch = function() {
    if (eventBatch.length === 0) return;
    
    var payload = {
      eventType: 'batch',
      timestamp: new Date().toISOString(),
      sessionId: getSessionId(),
      visitorId: getVisitorId(),
      siteId: config.siteId,
      batchMetadata: {
        eventCount: eventBatch.length,
        batchStartTime: eventBatch.length > 0 ? eventBatch[0].timestamp : null,
        batchEndTime: eventBatch.length > 0 ? eventBatch[eventBatch.length - 1].timestamp : null,
        activityDuration: lastActivityTime - (eventBatch.length > 0 ? new Date(eventBatch[0].timestamp).getTime() : lastActivityTime),
        sentOnExit: false
      },
      events: eventBatch
    };
    
    console.log('[Tracking] Sending batch:', eventBatch.length + ' events');
    
    sendData(payload);
    
    // Clear batch and timer
    eventBatch = [];
    if (inactivityTimer) {
      clearTimeout(inactivityTimer);
      inactivityTimer = null;
    }
  };

  // Add event to batch
  var addToBatch = function(eventType, eventData) {
    var event = {
      eventType: eventType,
      timestamp: new Date().toISOString(),
      eventData: eventData || {}
    };
    
    eventBatch.push(event);
    
    // Record activity for user interactions
    var userActivityEvents = ['click', 'scroll', 'scroll_depth', 'form_submit', 'text_copy'];
    if (userActivityEvents.indexOf(eventType) !== -1) {
      activityManager.recordActivity();
    }
    
    // Send batch if it reaches max size
    if (eventBatch.length >= config.maxBatchSize) {
      console.log('[Tracking] Sending batch due to max size reached');
      sendBatch();
    }
  };

  // Send data to server
  var sendData = function(payload) {
    try {
      if (window.fetch) {
        fetch(config.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload),
          keepalive: true
        }).then(function(response) {
          if (!response.ok) {
            console.error('[Tracking] Server error:', response.status);
          }
        }).catch(function(error) {
          console.error('[Tracking] Fetch error:', error);
        });
      } else {
        // Fallback for older browsers
        var xhr = new XMLHttpRequest();
        xhr.open('POST', config.endpoint, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify(payload));
      }
    } catch(e) {
      console.error('[Tracking] Error sending data:', e);
    }
  };

  // Send immediate event
  var sendImmediate = function(eventType, eventData) {
    var payload = {
      eventType: eventType,
      timestamp: new Date().toISOString(),
      sessionId: getSessionId(),
      visitorId: getVisitorId(),
      siteId: config.siteId,
      url: window.location.href,
      path: window.location.pathname,
      eventData: eventData || {}
    };
    
    // Add rich data for pageview events
    if (eventType === 'pageview') {
      payload.attribution = getCurrentPageAttribution();
      payload.browser = getBrowserData();
      payload.page = {
        title: document.title,
        url: window.location.href,
        path: window.location.pathname,
        referrer: document.referrer || 'direct',
        queryParams: window.location.search,
        hash: window.location.hash
      };
    }
    
    console.log('[Tracking] Sending immediate:', eventType);
    sendData(payload);
  };

  // Track page view
  var trackPageView = function() {
    if (config.trackPageViews) {
      sessionStorage.setItem('_ts_page_start', Date.now().toString());
      sendImmediate('pageview');
    }
  };

  // Track clicks
  var trackClicks = function() {
    if (config.trackClicks) {
      document.addEventListener('click', function(event) {
        var element = event.target;
        var tagName = element.tagName.toLowerCase();
        
        var eventData = {
          tagName: tagName,
          classes: element.className || '',
          id: element.id || '',
          href: element.href || '',
          text: (element.innerText || element.textContent || '').substring(0, 100),
          position: {
            x: event.clientX,
            y: event.clientY
          }
        };

        // Check for file downloads
        if (element.href && element.href.match(/\.(pdf|doc|docx|xls|xlsx|zip|rar|jpg|jpeg|png|gif|mp4|mp3)$/i)) {
          eventData.fileType = element.href.split('.').pop().toLowerCase();
          eventData.isDownload = true;
        }
        
        addToBatch('click', eventData);
      });
    }
  };

  // Track text selection and copy
  var trackTextSelection = function() {
    if (config.trackTextSelection) {
      document.addEventListener('copy', function(event) {
        var selectedText = window.getSelection().toString();
        if (selectedText.length > 10) {
          addToBatch('text_copy', {
            textLength: selectedText.length,
            textPreview: selectedText.substring(0, 100)
          });
        }
      });
    }
  };

  // Track page visibility changes
  var trackPageVisibility = function() {
    if (config.trackPageVisibility) {
      var lastVisibilityChange = Date.now();
      
      document.addEventListener('visibilitychange', function() {
        var now = Date.now();
        var timeSpent = now - lastVisibilityChange;
        
        addToBatch('page_visibility', {
          hidden: document.hidden,
          timeSpent: timeSpent
        });
        
        lastVisibilityChange = now;
      });
    }
  };

  // Track forms
  var trackForms = function() {
    if (config.trackForms) {
      document.addEventListener('submit', function(event) {
        var form = event.target;
        var formData = {};
        var excludedFields = ['password', 'credit', 'card', 'cvv', 'ssn', 'social'];
        
        for (var i = 0; i < form.elements.length; i++) {
          var element = form.elements[i];
          
          if (!element.name || ['input', 'textarea', 'select'].indexOf(element.tagName.toLowerCase()) === -1) {
            continue;
          }
          
          var isExcluded = false;
          for (var j = 0; j < excludedFields.length; j++) {
            var term = excludedFields[j];
            if (element.name.toLowerCase().indexOf(term) !== -1 || 
                (element.id && element.id.toLowerCase().indexOf(term) !== -1)) {
              isExcluded = true;
              break;
            }
          }
          
          if (isExcluded) {
            formData[element.name] = '[REDACTED]';
          } else {
            if (element.type === 'checkbox' || element.type === 'radio') {
              if (element.checked) {
                formData[element.name] = element.value;
              }
            } else {
              formData[element.name] = element.value;
            }
          }
        }
        
        sendImmediate('form_submit', {
          formId: form.id || 'unknown',
          formAction: form.action || window.location.href,
          formMethod: form.method || 'get',
          formData: formData
        });
      });
    }
  };

  // Scroll depth tracking
  var scrollDepthTracking = {
    maxScroll: 0,
    milestones: {},
    lastScrollTime: 0,
    
    init: function() {
      if (!config.trackScrollDepth) return;
      
      var self = this;
      
      // Initialize milestones
      config.scrollMilestones.forEach(function(milestone) {
        self.milestones[milestone] = false;
      });
      
      // Throttled scroll handler
      var throttledScroll = this.throttle(function() {
        self.trackScroll();
      }, config.scrollThrottle);
      
      window.addEventListener('scroll', throttledScroll, { passive: true });
      
      // Track initial position
      setTimeout(function() {
        self.trackScroll();
      }, 1000);
    },
    
    trackScroll: function() {
      var scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
      var windowHeight = window.innerHeight || document.documentElement.clientHeight || 0;
      var documentHeight = Math.max(
        document.body.scrollHeight || 0,
        document.body.offsetHeight || 0,
        document.documentElement.clientHeight || 0,
        document.documentElement.scrollHeight || 0,
        document.documentElement.offsetHeight || 0
      );
      
      var scrollableHeight = documentHeight - windowHeight;
      var scrollPercentage = scrollableHeight > 0 ? Math.round((scrollTop / scrollableHeight) * 100) : 100;
      scrollPercentage = Math.min(100, Math.max(0, scrollPercentage));
      
      // Update max scroll
      if (scrollPercentage > this.maxScroll) {
        this.maxScroll = scrollPercentage;
        
        // Send scroll progress update (throttled)
        var currentTime = Date.now();
        if (currentTime - this.lastScrollTime > 2000) {
          addToBatch('scroll', {
            scrollPercentage: scrollPercentage,
            scrollTop: scrollTop,
            documentHeight: documentHeight,
            windowHeight: windowHeight
          });
          this.lastScrollTime = currentTime;
        }
      }
      
      // Check milestones
      var self = this;
      config.scrollMilestones.forEach(function(milestone) {
        if (!self.milestones[milestone] && scrollPercentage >= milestone) {
          self.milestones[milestone] = true;
          
          var pageStart = parseInt(sessionStorage.getItem('_ts_page_start') || Date.now());
          var timeToMilestone = Date.now() - pageStart;
          
          addToBatch('scroll_depth', {
            milestone: milestone,
            timeToMilestone: timeToMilestone,
            scrollPercentage: scrollPercentage
          });
          
          console.log('[Tracking] Scroll milestone reached:', milestone + '%');
        }
      });
    },
    
    throttle: function(func, limit) {
      var inThrottle;
      return function() {
        var args = arguments;
        var context = this;
        if (!inThrottle) {
          func.apply(context, args);
          inThrottle = true;
          setTimeout(function() { inThrottle = false; }, limit);
        }
      };
    }
  };

  // Track page exit
  var trackExit = function() {
    window.addEventListener('beforeunload', function() {
      var startTime = parseInt(sessionStorage.getItem('_ts_page_start') || Date.now());
      var timeSpent = Date.now() - startTime;
      
      // Send any remaining batched events
      if (eventBatch.length > 0) {
        var batchPayload = {
          eventType: 'batch',
          timestamp: new Date().toISOString(),
          sessionId: getSessionId(),
          visitorId: getVisitorId(),
          siteId: config.siteId,
          batchMetadata: {
            eventCount: eventBatch.length,
            sentOnExit: true
          },
          events: eventBatch
        };
        
        if (navigator.sendBeacon) {
          navigator.sendBeacon(config.endpoint, JSON.stringify(batchPayload));
        }
      }
      
      // Send page exit event
      var exitData = {
        eventType: 'page_exit',
        timestamp: new Date().toISOString(),
        sessionId: getSessionId(),
        visitorId: getVisitorId(),
        siteId: config.siteId,
        url: window.location.href,
        path: window.location.pathname,
        eventData: { timeSpent: timeSpent }
      };
      
      if (navigator.sendBeacon) {
        navigator.sendBeacon(config.endpoint, JSON.stringify(exitData));
      }
    });
  };

  // Initialize tracking
  var init = function() {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      console.warn('[Tracking] Browser environment not detected');
      return;
    }
    
    if (!window.localStorage || !window.sessionStorage) {
      console.warn('[Tracking] Browser does not support localStorage or sessionStorage');
      return;
    }
    
    if (navigator.doNotTrack === '1' || window.doNotTrack === '1') {
      console.info('[Tracking] Respecting Do Not Track setting');
      return;
    }
    
    try {
      console.log('[Tracking] Initializing analytics...');
      console.log('[Tracking] Session ID:', getSessionId());
      console.log('[Tracking] Visitor ID:', getVisitorId());
      console.log('[Tracking] Site ID:', config.siteId);
      
      // Initialize all tracking
      activityManager.initActivityListeners();
      scrollDepthTracking.init();
      
      trackPageView();
      trackClicks();
      trackTextSelection();
      trackPageVisibility();
      trackForms();
      trackExit();
      
      console.log('[Tracking] Analytics initialized successfully');
    } catch (error) {
      console.error('[Tracking] Error during initialization:', error);
    }
  };

  // Run initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();