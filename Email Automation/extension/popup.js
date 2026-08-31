// popup.js - Extension popup UI
document.addEventListener('DOMContentLoaded', async () => {
  const root = document.getElementById('root');
  
  // Get current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  // Fallback platform detection from URL (if content script isn't ready)
  function detectPlatformFromUrl(url) {
    if (!url) return 'unknown';
    
    try {
      const urlObj = new URL(url);
      const hostname = urlObj.hostname;
      const pathname = urlObj.pathname;
      
      if (hostname.includes('linkedin.com')) {
        if (pathname.includes('/in/') && pathname.match(/\/in\/[^\/]+/)) {
          return 'linkedin_profile';
        } else if (pathname.includes('/company/')) {
          return 'linkedin_company';
        }
        return 'linkedin';
      }
      
      if (hostname.includes('google.com') || hostname.includes('maps.google.com')) {
        if (pathname.includes('/maps/') || pathname.includes('/place/') || url.includes('google.com/maps')) {
          return 'google_maps';
        }
      }
      
      if (hostname.includes('instagram.com')) {
        if (pathname.match(/^\/([^\/]+)\/?$/)) {
          return 'instagram_profile';
        }
        return 'instagram';
      }
      
      // Check if it's a special page where content scripts can't run
      if (url.startsWith('chrome://') || 
          url.startsWith('chrome-extension://') || 
          url.startsWith('edge://') ||
          url.startsWith('about:') ||
          url.startsWith('moz-extension://')) {
        return 'unknown';
      }
      
      // Default to website for http/https pages
      if (url.startsWith('http://') || url.startsWith('https://')) {
        return 'website';
      }
      
      return 'unknown';
    } catch (e) {
      return 'unknown';
    }
  }
  
  // Detect platform - try content script first, fallback to URL detection
  let platform = 'unknown';
  
  // Check if we can inject content script (not a special page)
  const canInject = tab.url && 
    !tab.url.startsWith('chrome://') && 
    !tab.url.startsWith('chrome-extension://') &&
    !tab.url.startsWith('edge://') &&
    !tab.url.startsWith('about:') &&
    !tab.url.startsWith('moz-extension://');
  
  if (canInject) {
    try {
      // Try to inject content script if not already loaded
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js']
      }).catch(() => {
        // Script might already be injected, that's okay
      });
      
      // Wait a bit for script to initialize
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Try to send message
      const result = await chrome.tabs.sendMessage(tab.id, { action: 'detectPlatform' });
      if (result && result.platform) {
        platform = result.platform;
      }
    } catch (error) {
      // Content script not ready or failed - use URL fallback
      console.log('Content script not ready, using URL fallback:', error.message);
      platform = detectPlatformFromUrl(tab.url);
    }
  } else {
    // Special page - can't inject content script
    platform = detectPlatformFromUrl(tab.url);
  }
  
  const platformNames = {
    'website': '🌐 Company Website',
    'linkedin_profile': '💼 LinkedIn Profile',
    'linkedin_company': '🏢 LinkedIn Company',
    'google_maps': '📍 Google Maps Business',
    'instagram_profile': '📷 Instagram Profile',
    'unknown': '❓ Unknown Platform'
  };
  
  let scrapedData = null;
  
  // Function to get auth token from web app automatically
  async function getAuthToken() {
    // First, check if we have a cached token (encrypted)
    const stored = await chrome.storage.local.get('authToken');
    if (stored.authToken) {
      // Decrypt the stored token
      try {
        const decrypted = await decryptToken(stored.authToken);
        if (decrypted) {
          return decrypted;
        }
      } catch (error) {
        console.error('Failed to decrypt token, trying as plain text:', error);
        // Fallback: try as plain text for backward compatibility
        return stored.authToken;
      }
    }
    
    // Try to get token from web app's localStorage
    // Check common web app URLs (localhost for dev, and production domain)
    const webAppUrls = [
      'http://localhost:3000',
      'http://localhost:5173', // Vite default
      'https://wolfassistants.com',
      'https://www.wolfassistants.com'
    ];
    
    // Find any open tab with the web app
    const tabs = await chrome.tabs.query({});
    for (const webAppUrl of webAppUrls) {
      const webAppTab = tabs.find(t => t.url && t.url.startsWith(webAppUrl));
      if (webAppTab) {
        try {
          // Inject script to get token from web app's localStorage
          const results = await chrome.scripting.executeScript({
            target: { tabId: webAppTab.id },
            func: () => {
              return localStorage.getItem('token');
            }
          });
          
          if (results && results[0] && results[0].result) {
            const token = results[0].result;
            if (token) {
              // Encrypt and cache the token
              try {
                const encrypted = await encryptToken(token);
                await chrome.storage.local.set({ authToken: encrypted });
              } catch (error) {
                console.error('Failed to encrypt token, storing as plain text:', error);
                // Fallback: store as plain text if encryption fails
                await chrome.storage.local.set({ authToken: token });
              }
              return token;
            }
          }
        } catch (error) {
          console.log('Could not access web app tab:', error);
        }
      }
    }
    
    return null;
  }
  
  function renderUI() {
    root.innerHTML = `
      <div style="padding: 16px;">
        <h2 style="margin: 0 0 8px 0; font-size: 18px; color: #333;">
          ${platformNames[platform] || 'Unknown'}
        </h2>
        <p style="margin: 0 0 16px 0; font-size: 12px; color: #666;">
          Real-time lead scraping & validation
        </p>
        
        ${platform === 'unknown' ? `
          <div style="padding: 20px; text-align: center; color: #999;">
            <p>This platform is not supported yet.</p>
            <p style="font-size: 12px;">Supported: Websites, LinkedIn, Google Maps, Instagram</p>
          </div>
        ` : `
          <button id="scrapeBtn" style="
            width: 100%;
            padding: 12px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 16px;
          ">Scrape ${platformNames[platform]}</button>
          
          <div id="results" style="max-height: 400px; overflow-y: auto;"></div>
        `}
      </div>
    `;
    
    const scrapeBtn = document.getElementById('scrapeBtn');
    if (scrapeBtn) {
      scrapeBtn.addEventListener('click', handleScrape);
    }
  }
  
  async function handleScrape() {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const resultsDiv = document.getElementById('results');
    
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = 'Scraping...';
    resultsDiv.innerHTML = '<p style="text-align: center; color: #666;">Scraping page...</p>';
    
    try {
      // Ensure content script is injected before sending message
      const canInject = tab.url && 
        !tab.url.startsWith('chrome://') && 
        !tab.url.startsWith('chrome-extension://') &&
        !tab.url.startsWith('edge://') &&
        !tab.url.startsWith('about:') &&
        !tab.url.startsWith('moz-extension://');
      
      if (canInject) {
        try {
          // Try to inject content script if not already loaded
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js']
          }).catch(() => {
            // Script might already be injected, that's okay
          });
          
          // Wait for script to initialize
          await new Promise(resolve => setTimeout(resolve, 200));
        } catch (injectError) {
          console.log('Could not inject content script:', injectError);
        }
      }
      
      const result = await chrome.tabs.sendMessage(tab.id, { action: 'scrape' });
      scrapedData = result;
      
      let html = '';
      
      if (result.data && result.data.contacts && result.data.contacts.length > 0) {
        html += `<h3 style="font-size: 14px; margin-bottom: 8px; color: #333;">Contacts Found (${result.data.contacts.length})</h3>`;
        result.data.contacts.forEach((contact, idx) => {
          html += `
            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;">
              ${contact.name ? `<div style="margin-bottom: 4px;"><strong>Name:</strong> ${contact.name}</div>` : ''}
              ${contact.email ? `<div style="margin-bottom: 4px;"><strong>Email:</strong> ${contact.email} ✅</div>` : ''}
              ${contact.phone ? `<div style="margin-bottom: 4px;"><strong>Phone:</strong> ${contact.phone}</div>` : ''}
              ${contact.position ? `<div style="margin-bottom: 4px;"><strong>Position:</strong> ${contact.position}</div>` : ''}
              ${contact.company ? `<div style="margin-bottom: 4px;"><strong>Company:</strong> ${contact.company}</div>` : ''}
            </div>
          `;
        });
      } else if (result.data && result.data.error) {
        html += `<p style="color: red;">Error: ${result.data.error}</p>`;
      } else {
        html += `<p style="color: #999; text-align: center;">No contacts found on this page.</p>`;
      }
      
      if (result.data && result.data.company) {
        html += `<h3 style="font-size: 14px; margin: 16px 0 8px 0; color: #333;">Company Info</h3>`;
        html += `<div style="border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #f9f9f9;">`;
        if (result.data.company.name) html += `<div style="margin-bottom: 4px;"><strong>Name:</strong> ${result.data.company.name}</div>`;
        if (result.data.company.website) {
          html += `<div style="margin-bottom: 4px;"><strong>Website:</strong> <a href="${result.data.company.website}" target="_blank" style="color: #007bff; text-decoration: none;">${result.data.company.website}</a></div>`;
        }
        if (result.data.company.phone) html += `<div style="margin-bottom: 4px;"><strong>Phone:</strong> ${result.data.company.phone}</div>`;
        if (result.data.company.description) {
          html += `<div style="margin-bottom: 4px;"><strong>Description:</strong> ${result.data.company.description.substring(0, 100)}${result.data.company.description.length > 100 ? '...' : ''}</div>`;
        }
        html += `</div>`;
        
        // Show instruction message if website found but no email
        if (result.data.company.message) {
          html += `
            <div style="
              margin-top: 12px;
              padding: 12px;
              background: #fff3cd;
              border: 1px solid #ffc107;
              border-radius: 6px;
              border-left: 4px solid #ff9800;
            ">
              <div style="
                font-size: 13px;
                color: #856404;
                line-height: 1.5;
                font-weight: 500;
                margin-bottom: 8px;
              ">${result.data.company.message}</div>
              ${result.data.company.website ? `
                <a href="${result.data.company.website}" target="_blank" style="
                  display: inline-block;
                  padding: 6px 12px;
                  background: #ff9800;
                  color: white;
                  text-decoration: none;
                  border-radius: 4px;
                  font-size: 12px;
                  font-weight: bold;
                  margin-top: 4px;
                ">Open Website & Scrape</a>
              ` : ''}
            </div>
          `;
        }
      }
      
      if (result.validation) {
        html += `<h3 style="font-size: 14px; margin: 16px 0 8px 0; color: #333;">Website Issues Found</h3>`;
        
        if (result.validation.seo && result.validation.seo.length > 0) {
          html += `<div style="margin-bottom: 12px; padding: 8px; background: #fff3cd; border-radius: 4px; border-left: 3px solid #ffc107;">`;
          html += `<strong style="color: #d32f2f; font-size: 12px;">SEO Issues (${result.validation.seo.length}):</strong>`;
          html += `<ul style="margin: 4px 0 0 0; padding-left: 20px; font-size: 11px; color: #666;">`;
          result.validation.seo.slice(0, 5).forEach(issue => {
            html += `<li style="margin-bottom: 2px;">${issue.message}</li>`;
          });
          html += `</ul></div>`;
        }
        
        if (result.validation.ux_ui && result.validation.ux_ui.length > 0) {
          html += `<div style="margin-bottom: 12px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 3px solid #2196f3;">`;
          html += `<strong style="color: #f57c00; font-size: 12px;">UX/UI Issues (${result.validation.ux_ui.length}):</strong>`;
          html += `<ul style="margin: 4px 0 0 0; padding-left: 20px; font-size: 11px; color: #666;">`;
          result.validation.ux_ui.slice(0, 5).forEach(issue => {
            html += `<li style="margin-bottom: 2px;">${issue.message}</li>`;
          });
          html += `</ul></div>`;
        }
        
        if (result.validation.content && result.validation.content.length > 0) {
          html += `<div style="margin-bottom: 12px; padding: 8px; background: #f3e5f5; border-radius: 4px; border-left: 3px solid #9c27b0;">`;
          html += `<strong style="color: #1976d2; font-size: 12px;">Content Issues (${result.validation.content.length}):</strong>`;
          html += `<ul style="margin: 4px 0 0 0; padding-left: 20px; font-size: 11px; color: #666;">`;
          result.validation.content.slice(0, 5).forEach(issue => {
            html += `<li style="margin-bottom: 2px;">${issue.message}</li>`;
          });
          html += `</ul></div>`;
        }
      }
      
      if (result.data && (result.data.contacts || result.data.company)) {
        html += `
          <button id="addBtn" style="
            width: 100%;
            padding: 12px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            margin-top: 12px;
          ">Add to WolfAssistants</button>
        `;
      }
      
      resultsDiv.innerHTML = html;
      
      const addBtn = document.getElementById('addBtn');
      if (addBtn) {
        addBtn.addEventListener('click', handleAddToContacts);
      }
      
    } catch (error) {
      console.error('Scraping failed:', error);
      document.getElementById('results').innerHTML = `<p style="color: red; text-align: center;">Error: ${error.message}</p>`;
    } finally {
      scrapeBtn.disabled = false;
      scrapeBtn.textContent = `Scrape ${platformNames[platform]}`;
    }
  }
  
  async function handleAddToContacts() {
    if (!scrapedData) return;
    
    const addBtn = document.getElementById('addBtn');
    addBtn.disabled = true;
    addBtn.textContent = 'Adding...';
    
    try {
      // Get auth token automatically from web app
      const token = await getAuthToken();
      
      if (!token) {
        addBtn.disabled = false;
        addBtn.textContent = 'Add to WolfAssistants';
        alert('Please log in to WolfAssistants web app first, then try again.\n\nMake sure you have the web app open in another tab.');
        return;
      }
      
      // Normalize contacts to ensure they have required fields
      // Use current tab URL as fallback
      const fallbackUrl = tab?.url || '';
      
      // Filter out contacts without emails - email is REQUIRED for personalized emails
      const contactsWithEmails = (scrapedData.data.contacts || []).filter(contact => {
        return contact.email && contact.email.trim() && contact.email.includes('@');
      });
      
      if (contactsWithEmails.length === 0) {
        alert('No contacts with email addresses found. Email is required to send personalized emails.\n\nPlease scrape a page that contains email addresses.');
        addBtn.disabled = false;
        addBtn.textContent = 'Add to WolfAssistants';
        return;
      }
      
      const normalizedContacts = contactsWithEmails.map(contact => {
        // Ensure source_url exists (handle linkedin_url, instagram_url, etc.)
        const sourceUrl = contact.source_url || contact.linkedin_url || contact.instagram_url || fallbackUrl;
        // Ensure source_type exists
        const sourceType = contact.source_type || scrapedData.platform || 'unknown';
        
        return {
          email: contact.email.trim().toLowerCase(), // Normalize email
          name: contact.name || null,
          position: contact.position || null,
          company: contact.company || null,
          phone: contact.phone || null,
          address: contact.address || null,
          source_url: sourceUrl,
          source_type: sourceType
        };
      });
      
      let response;
      try {
        response = await fetch('http://localhost:8000/api/v1/extension/scrape-and-add', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            contacts: normalizedContacts,
            company: scrapedData.data.company || null,
            validation: scrapedData.validation || null,
            platform: scrapedData.platform
          })
        });
      } catch (fetchError) {
        // Handle network errors (Failed to fetch, CORS, etc.)
        if (fetchError.message.includes('Failed to fetch') || 
            fetchError.message.includes('NetworkError') ||
            fetchError.message.includes('Network request failed')) {
          throw new Error('Cannot connect to backend. Make sure the backend is running on http://localhost:8000');
        }
        throw fetchError;
      }
      
      // Check if response is ok
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: `;
        try {
          const errorData = await response.json();
          // Handle Pydantic validation errors (422)
          if (response.status === 422 && errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              // Pydantic validation errors are arrays
              const validationErrors = errorData.detail.map(err => {
                const field = err.loc ? err.loc.join('.') : 'unknown';
                return `${field}: ${err.msg || err.message || 'Invalid value'}`;
              }).join('\n');
              errorMessage += `Validation errors:\n${validationErrors}`;
            } else if (typeof errorData.detail === 'string') {
              errorMessage += errorData.detail;
            } else {
              errorMessage += JSON.stringify(errorData.detail);
            }
          } else if (response.status === 500) {
            // Handle 500 errors with more detail
            const detail = errorData.detail || errorData.error || errorData.message || 'Internal server error';
            errorMessage += detail;
            
            // Check if it's a table creation error
            if (detail.includes('scraped_leads') || detail.includes('table') || detail.includes('migration')) {
              errorMessage += '\n\nThe scraped_leads table needs to be created. The system will try to create it automatically on the next attempt.';
            }
          } else {
            errorMessage += errorData.detail || errorData.error || errorData.message || 'Unknown error';
          }
        } catch (e) {
          errorMessage += response.statusText || 'Unknown error';
          if (response.status === 500) {
            errorMessage += '\n\nThis might be a database issue. Please check backend logs.';
          }
        }
        
        if (response.status === 401) {
          // Token expired or invalid - clear stored token
          await chrome.storage.local.remove('authToken');
          errorMessage += '\n\nPlease log in again to the web app and try again.';
        }
        
        throw new Error(errorMessage);
      }
      
      const responseData = await response.json();
      if (responseData.success) {
        const message = `✅ Successfully saved ${responseData.added_count} lead(s) to Scraped Leads!${responseData.skipped_count > 0 ? `\n\nSkipped ${responseData.skipped_count} lead(s) (already exist or missing data).` : ''}\n\nReview and transfer them to Contacts from the Scraped Leads page.`;
        alert(message);
        addBtn.textContent = 'Saved ✓';
        addBtn.style.backgroundColor = '#6c757d';
      } else {
        const errorMsg = responseData.error || responseData.detail || 'Unknown error';
        alert(`Failed to add contacts: ${errorMsg}`);
        addBtn.disabled = false;
        addBtn.textContent = 'Add to WolfAssistants';
      }
    } catch (error) {
      console.error('Failed to add contacts:', error);
      
      // Provide user-friendly error messages
      let errorMsg = error.message || 'Unknown error';
      if (errorMsg.includes('localhost:8000') || 
          errorMsg.includes('Failed to fetch') || 
          errorMsg.includes('NetworkError') ||
          errorMsg.includes('Cannot connect')) {
        errorMsg = 'Cannot connect to backend.\n\nMake sure the backend is running on http://localhost:8000';
      } else if (errorMsg.includes('401') || errorMsg.includes('Unauthorized')) {
        errorMsg = 'Authentication failed. Please log in to WolfAssistants web app again.';
      } else if (errorMsg.includes('422')) {
        errorMsg = 'Validation error: ' + errorMsg;
      }
      
      alert(`Error: ${errorMsg}`);
      addBtn.disabled = false;
      addBtn.textContent = 'Add to WolfAssistants';
    }
  }
  
  renderUI();
});

