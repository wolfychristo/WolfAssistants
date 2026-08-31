// content.js - Multi-platform scraper and validator
(function() {
  'use strict';

  // Platform detection
  function detectPlatform() {
    const hostname = window.location.hostname;
    const pathname = window.location.pathname;
    
    if (hostname.includes('linkedin.com')) {
      if (pathname.includes('/in/') && pathname.match(/\/in\/[^\/]+/)) {
        return 'linkedin_profile';
      } else if (pathname.includes('/company/')) {
        return 'linkedin_company';
      }
      return 'linkedin';
    }
    
    if (hostname.includes('google.com') && (pathname.includes('/maps/') || pathname.includes('/place/'))) {
      return 'google_maps';
    }
    
    // Also check for maps.google.com subdomain
    if (hostname.includes('maps.google.com')) {
      return 'google_maps';
    }
    
    if (hostname.includes('instagram.com')) {
      if (pathname.match(/^\/([^\/]+)\/?$/)) {
        return 'instagram_profile';
      }
      return 'instagram';
    }
    
    if (!hostname.includes('linkedin.com') && 
        !hostname.includes('google.com') && 
        !hostname.includes('instagram.com')) {
      return 'website';
    }
    
    return 'unknown';
  }

  // Helper function to validate if a company name is likely real (not a bio/description)
  function isValidCompanyName(companyName) {
    if (!companyName || typeof companyName !== 'string') {
      return false;
    }
    
    const company = companyName.trim();
    const companyLower = company.toLowerCase();
    
    // Must have reasonable length
    if (company.length < 2 || company.length > 100) {
      return false;
    }
    
    // Reject if it contains description/bio keywords
    const bioKeywords = [
      'built', 'user', 'systems', 'genai', 'cv', '10k', '+', 'created',
      'developed', 'designed', 'founded', 'launched', 'helped', 'worked',
      'experience', 'expertise', 'specializing', 'specializing in',
      'focusing on', 'passionate about', 'dedicated to', 'years of',
      'helping', 'enabling', 'empowering', 'transforming', 'revolutionizing'
    ];
    
    for (const keyword of bioKeywords) {
      if (companyLower.includes(keyword)) {
        return false;
      }
    }
    
    // Reject if it contains numbers (like "10k+", "100+", etc.)
    if (/\d+/.test(company)) {
      return false;
    }
    
    // Reject if it's too long and contains common sentence patterns
    if (company.length > 50) {
      const sentencePatterns = [
        /\sand\s/i,  // "and" in middle
        /\swith\s/i,  // "with" in middle
        /\sfor\s/i,   // "for" in middle
        /\sto\s/i     // "to" in middle
      ];
      
      for (const pattern of sentencePatterns) {
        if (pattern.test(company)) {
          return false;
        }
      }
    }
    
    // Reject if it looks like a sentence (starts with lowercase or has multiple verbs)
    if (company[0] === company[0].toLowerCase() && company.length > 20) {
      return false;
    }
    
    // Must contain at least one letter
    if (!/[a-zA-Z]/.test(company)) {
      return false;
    }
    
    return true;
  }
  
  // Helper function to validate if an email is likely real (not randomly generated)
  function isValidEmail(email) {
    if (!email || typeof email !== 'string') {
      return false;
    }
    
    const emailLower = email.toLowerCase().trim();
    
    // Basic email format check
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailPattern.test(emailLower)) {
      return false;
    }
    
    // Reject common fake/test domains
    const fakeDomains = [
      'example.com', 'test.com', 'placeholder.com', 'fake.com',
      'dummy.com', 'sample.com', 'invalid.com', 'noreply.com',
      'no-reply.com', 'linkedin.com', 'facebook.com', 'twitter.com',
      'instagram.com', 'youtube.com'
    ];
    
    const domain = emailLower.split('@')[1];
    if (fakeDomains.includes(domain)) {
      return false;
    }
    
    // Reject if email looks randomly generated
    const localPart = emailLower.split('@')[0];
    
    // Check for random string patterns (long alphanumeric strings)
    if (/^[a-z0-9]{15,}$/i.test(localPart)) {
      // If it's a very long random-looking string, might be fake
      // But allow if it has dots/underscores (like firstname.lastname)
      if (!/[._-]/.test(localPart)) {
        return false;
      }
    }
    
    // Reject if it's just numbers
    if (/^\d+@/.test(emailLower)) {
      return false;
    }
    
    // Reject if it contains "test", "fake", "dummy", "sample" in local part
    const fakeKeywords = ['test', 'fake', 'dummy', 'sample', 'invalid', 'temp', 'tmp'];
    for (const keyword of fakeKeywords) {
      if (localPart.includes(keyword)) {
        return false;
      }
    }
    
    // Reject if it's too short (likely fake)
    if (localPart.length < 3) {
      return false;
    }
    
    return true;
  }

  // Helper function to extract emails from HTML/text
  function extractEmailsFromText(text, sourceUrl, foundEmails, contacts, company) {
    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    const emails = text.match(emailPattern);
    
    if (emails) {
      emails.forEach(email => {
        const emailLower = email.toLowerCase().trim();
        // Use comprehensive email validation
        if (!foundEmails.has(emailLower) && isValidEmail(emailLower)) {
          foundEmails.add(emailLower);
          
          contacts.push({
            email: emailLower,
            name: null,
            position: null,
            company: company,
            phone: null,
            source_url: sourceUrl,
            source_type: 'website'
          });
        }
      });
    }
  }

  // Helper function to scrape a single page
  async function scrapePage(url) {
    try {
      // Convert HTTP to HTTPS if needed
      let fetchUrl = url;
      if (fetchUrl.startsWith('http://') && window.location.protocol === 'https:') {
        fetchUrl = fetchUrl.replace('http://', 'https://');
      }
      
      // Skip if it's HTTP on HTTPS page (mixed content)
      if (window.location.protocol === 'https:' && fetchUrl.startsWith('http://')) {
        return null;
      }
      
      const response = await fetch(fetchUrl, {
        method: 'GET',
        credentials: 'omit',
        mode: 'cors',
        headers: {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
      });
      
      if (response.ok) {
        const html = await response.text();
        return html;
      }
    } catch (error) {
      // Silently fail - CORS or network issues are common
      console.log(`Could not fetch ${url}:`, error.message);
    }
    return null;
  }

  // Find important pages to scrape (Contact, About, etc.)
  function findImportantPages() {
    const importantPages = new Set();
    const baseUrl = window.location.origin;
    const currentPath = window.location.pathname;
    
    // Keywords to look for in links
    const importantKeywords = [
      'contact', 'about', 'team', 'staff', 'people', 'leadership',
      'get-in-touch', 'reach-us', 'connect', 'support', 'help',
      'footer', 'footer-link'
    ];
    
    // Find links in navigation, footer, and main content
    const linkSelectors = [
      'nav a[href]',
      'footer a[href]',
      '[class*="nav"] a[href]',
      '[class*="menu"] a[href]',
      '[class*="footer"] a[href]',
      '[id*="nav"] a[href]',
      '[id*="menu"] a[href]',
      '[id*="footer"] a[href]'
    ];
    
    linkSelectors.forEach(selector => {
      const links = document.querySelectorAll(selector);
      links.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        
        const linkText = (link.textContent || '').toLowerCase().trim();
        const hrefLower = href.toLowerCase();
        
        // Check if link text or href contains important keywords
        const isImportant = importantKeywords.some(keyword => 
          linkText.includes(keyword) || hrefLower.includes(keyword)
        );
        
        if (isImportant) {
          try {
            let fullUrl;
            if (href.startsWith('http://') || href.startsWith('https://')) {
              fullUrl = href;
            } else if (href.startsWith('/')) {
              fullUrl = baseUrl + href;
            } else {
              fullUrl = baseUrl + '/' + href;
            }
            
            // Only add if it's from the same domain
            try {
              const urlObj = new URL(fullUrl);
              if (urlObj.origin === baseUrl && !importantPages.has(fullUrl) && fullUrl !== window.location.href) {
                importantPages.add(fullUrl);
              }
            } catch (e) {
              // Invalid URL, skip
            }
          } catch (e) {
            // Skip invalid URLs
          }
        }
      });
    });
    
    // Also check common paths
    const commonPaths = ['/contact', '/contact-us', '/about', '/about-us', '/team', '/contact.html', '/about.html'];
    commonPaths.forEach(path => {
      const fullUrl = baseUrl + path;
      if (fullUrl !== window.location.href) {
        importantPages.add(fullUrl);
      }
    });
    
    return Array.from(importantPages).slice(0, 5); // Limit to 5 pages to avoid too many requests
  }

  // Website scraper - now async to fetch multiple pages
  async function scrapeWebsite() {
    const contacts = [];
    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    const foundEmails = new Set();
    
    // FIXED: Better company name extraction - try multiple sources
    let company = null;
    
    // Strategy 1: Try meta tags (more reliable)
    const ogSiteName = document.querySelector('meta[property="og:site_name"]');
    if (ogSiteName) {
      company = ogSiteName.getAttribute('content')?.trim();
    }
    
    // Strategy 2: Try application-name meta tag
    if (!company) {
      const appName = document.querySelector('meta[name="application-name"]');
      if (appName) {
        company = appName.getAttribute('content')?.trim();
      }
    }
    
    // Strategy 3: Try structured data (JSON-LD)
    if (!company) {
      const jsonLd = document.querySelector('script[type="application/ld+json"]');
      if (jsonLd) {
        try {
          const data = JSON.parse(jsonLd.textContent);
          if (data.organization && data.organization.name) {
            company = data.organization.name;
          } else if (data.name && typeof data.name === 'string') {
            company = data.name;
          }
        } catch (e) {
          // JSON parse failed, continue
        }
      }
    }
    
    // Strategy 4: Parse page title more carefully (last part after | or -)
    if (!company) {
      const title = document.querySelector('title');
      if (title && title.textContent) {
        const titleText = title.textContent.trim();
        // Try to get the last part after | or - (usually the company name)
        if (titleText.includes('|')) {
          const parts = titleText.split('|');
          company = parts[parts.length - 1].trim();
        } else if (titleText.includes(' - ')) {
          const parts = titleText.split(' - ');
          company = parts[parts.length - 1].trim();
        } else if (titleText.includes(' – ')) {
          const parts = titleText.split(' – ');
          company = parts[parts.length - 1].trim();
        } else {
          // If no separator, use first part but validate it's not too long
          company = titleText.split('|')[0].trim();
          if (company.length > 60) {
            company = null;  // Too long, probably not a company name
          }
        }
      }
    }
    
    // Strategy 5: Fallback to hostname (last resort)
    if (!company || company.length > 100) {
      company = window.location.hostname.replace('www.', '').split('.')[0];
      // Capitalize first letter
      company = company.charAt(0).toUpperCase() + company.slice(1);
    }
    
    // First, scrape the current page
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );
    
    let node;
    while (node = walker.nextNode()) {
      const text = node.textContent;
      const emails = text.match(emailPattern);
      if (emails) {
        emails.forEach(email => {
          const emailLower = email.toLowerCase().trim();
          // Use comprehensive email validation
          if (!foundEmails.has(emailLower) && isValidEmail(emailLower)) {
            foundEmails.add(emailLower);
            
            let parent = node.parentElement;
            let name = null;
            let title = null;
            
            // IMPROVED: Better name extraction with multiple strategies
            const container = parent.closest('div, section, article, li, td, p, address, footer, header');
            if (container) {
              // Strategy 1: Look for name patterns in nearby text
              // Check text before and after email in the same container
              const containerText = container.textContent || '';
              const emailIndex = containerText.toLowerCase().indexOf(emailLower);
              if (emailIndex > 0) {
                // Look for name patterns before email (common: "Contact: John Doe <email>")
                const beforeEmail = containerText.substring(Math.max(0, emailIndex - 100), emailIndex);
                const namePatterns = [
                  /(?:contact|name|from|by|author)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})/i,
                  /([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*<|$)/,  // "John Doe <" or "John Doe"
                  /([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*\(|$)/,  // "John Doe (" 
                ];
                
                for (const pattern of namePatterns) {
                  const match = beforeEmail.match(pattern);
                  if (match && match[1]) {
                    const potentialName = match[1].trim();
                    if (potentialName.split(' ').length >= 2 && potentialName.split(' ').length <= 3 && 
                        potentialName.length < 50 && !potentialName.includes('@')) {
                      name = potentialName;
                      break;
                    }
                  }
                }
              }
              
              // Strategy 2: Look for structured name elements (existing logic, improved)
              if (!name) {
                const nameSelectors = [
                  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                  'strong', 'b',
                  '.name', '[class*="name"]', '[class*="Name"]',
                  '[itemprop="name"]', '[data-name]',
                  '.contact-name', '.person-name', '.author-name'
                ];
                for (const selector of nameSelectors) {
                  const nameEl = container.querySelector(selector);
                  if (nameEl && nameEl.textContent.trim()) {
                    const nameText = nameEl.textContent.trim();
                    // Validate: 2-3 words, no email, reasonable length, looks like a name
                    const words = nameText.split(/\s+/);
                    if (words.length >= 2 && words.length <= 3 && 
                        !nameText.includes('@') && 
                        nameText.length < 50 &&
                        words.every(w => w.length > 1)) {  // Each word should be > 1 char
                      name = nameText;
                      break;
                    }
                  }
                }
              }
              
              // Strategy 3: Try to extract from email if no name found
              if (!name && emailLower.includes('@')) {
                const emailLocal = emailLower.split('@')[0];
                // If email is like "john.doe@company.com", try to extract name
                if (emailLocal.includes('.')) {
                  const parts = emailLocal.split('.');
                  if (parts.length === 2 && parts[0].length > 2 && parts[1].length > 2) {
                    // Capitalize: "john.doe" -> "John Doe"
                    name = parts[0].charAt(0).toUpperCase() + parts[0].slice(1) + ' ' +
                           parts[1].charAt(0).toUpperCase() + parts[1].slice(1);
                  }
                }
              }
              
              // Extract position/title (existing logic)
              const titleSelectors = [
                '.title', '.position', '.role', '.job-title',
                '[class*="title"]', '[class*="position"]', '[class*="role"]',
                '[itemprop="jobTitle"]', '[data-position]'
              ];
              for (const selector of titleSelectors) {
                const titleEl = container.querySelector(selector);
                if (titleEl && titleEl.textContent.trim()) {
                  title = titleEl.textContent.trim();
                  break;
                }
              }
            }
            
            contacts.push({
              email: emailLower,
              name: name,
              position: title,
              company: company,
              phone: null,
              notes: null,  // Will be generated later
              source_url: window.location.href,
              source_type: 'website'
            });
          }
        });
      }
    }
    
    // Find and scrape important pages
    const importantPages = findImportantPages();
    if (importantPages.length > 0) {
      // Scrape important pages in parallel (with limit)
      const scrapePromises = importantPages.slice(0, 5).map(async (pageUrl) => {
        const html = await scrapePage(pageUrl);
        if (html) {
          extractEmailsFromText(html, pageUrl, foundEmails, contacts, company);
        }
      });
      
      // Wait for all pages to be scraped (with timeout)
      await Promise.allSettled(scrapePromises);
    }
    
    // Use the same company extraction logic for companyInfo
    let companyName = company;  // Use the company we extracted above
    
    const companyInfo = {
      name: companyName,
      domain: window.location.hostname.replace('www.', ''),
      website: window.location.origin,
      description: document.querySelector('meta[name="description"]')?.getAttribute('content') || null,
      phone: null,
      email: null
    };
    
    const phonePattern = /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/;
    const phoneMatch = document.body.textContent.match(phonePattern);
    if (phoneMatch) {
      companyInfo.phone = phoneMatch[0];
    }
    
    const emailMatch = document.body.textContent.match(emailPattern);
    if (emailMatch) {
      companyInfo.email = emailMatch[0].toLowerCase();
    }
    
    // Generate basic notes for each contact
    contacts.forEach(contact => {
      if (!contact.notes) {
        contact.notes = generateContactNotes(contact, companyInfo);
      }
    });
    
    return { contacts, company: companyInfo };
  }

  // Generate structured notes for a contact
  function generateContactNotes(contact, companyInfo = null) {
    const notes = [];
    
    // Basic info
    if (contact.position) {
      notes.push(`Position: ${contact.position}`);
    }
    if (contact.company) {
      notes.push(`Company: ${contact.company}`);
    } else if (companyInfo && companyInfo.name) {
      notes.push(`Company: ${companyInfo.name}`);
    }
    if (contact.phone) {
      notes.push(`Phone: ${contact.phone}`);
    }
    if (contact.address) {
      notes.push(`Address: ${contact.address}`);
    }
    
    // Source info
    notes.push(`Source: ${contact.source_type}`);
    notes.push(`URL: ${contact.source_url}`);
    
    // Company info if available
    if (companyInfo) {
      if (companyInfo.description) {
        notes.push(`\nCompany Description: ${companyInfo.description.substring(0, 200)}`);
      }
      if (companyInfo.website) {
        notes.push(`Company Website: ${companyInfo.website}`);
      }
    }
    
    return notes.join('\n');
  }

  // Website validator
  function validateWebsite() {
    const issues = { seo: [], ux_ui: [], content: [] };
    
    const title = document.querySelector('title');
    if (!title || !title.textContent.trim()) {
      issues.seo.push({
        type: 'missing_title',
        severity: 'critical',
        message: 'Missing or empty <title> tag',
        impact: 'Poor SEO - search engines won\'t display proper title'
      });
    } else {
      const titleLen = title.textContent.trim().length;
      if (titleLen < 30) {
        issues.seo.push({
          type: 'title_too_short',
          severity: 'medium',
          message: `Title tag too short (${titleLen} chars, recommended 50-60)`,
          impact: 'May not fully describe page in search results'
        });
      } else if (titleLen > 60) {
        issues.seo.push({
          type: 'title_too_long',
          severity: 'low',
          message: `Title tag too long (${titleLen} chars, recommended 50-60)`,
          impact: 'May be truncated in search results'
        });
      }
    }
    
    const metaDesc = document.querySelector('meta[name="description"]');
    if (!metaDesc || !metaDesc.getAttribute('content')?.trim()) {
      issues.seo.push({
        type: 'missing_meta_description',
        severity: 'critical',
        message: 'Missing meta description',
        impact: 'Poor SEO - search engines won\'t show description in results'
      });
    } else {
      const descLen = metaDesc.getAttribute('content').length;
      if (descLen < 120) {
        issues.seo.push({
          type: 'meta_desc_too_short',
          severity: 'medium',
          message: `Meta description too short (${descLen} chars, recommended 150-160)`,
          impact: 'May not fully describe page in search results'
        });
      } else if (descLen > 160) {
        issues.seo.push({
          type: 'meta_desc_too_long',
          severity: 'low',
          message: `Meta description too long (${descLen} chars, recommended 150-160)`,
          impact: 'May be truncated in search results'
        });
      }
    }
    
    const h1Tags = document.querySelectorAll('h1');
    if (h1Tags.length === 0) {
      issues.seo.push({
        type: 'missing_h1',
        severity: 'critical',
        message: 'No H1 heading found',
        impact: 'Poor SEO - H1 is important for page structure'
      });
    } else if (h1Tags.length > 1) {
      issues.seo.push({
        type: 'multiple_h1',
        severity: 'medium',
        message: `Multiple H1 tags found (${h1Tags.length})`,
        impact: 'Should have only one H1 per page for SEO'
      });
    }
    
    const h2Tags = document.querySelectorAll('h2');
    if (h2Tags.length === 0) {
      issues.seo.push({
        type: 'missing_h2',
        severity: 'medium',
        message: 'No H2 headings found',
        impact: 'Poor content structure - H2s help organize content'
      });
    }
    
    const images = document.querySelectorAll('img');
    const imagesWithoutAlt = Array.from(images).filter(img => !img.getAttribute('alt'));
    if (imagesWithoutAlt.length > 0) {
      issues.seo.push({
        type: 'missing_alt_text',
        severity: 'medium',
        message: `${imagesWithoutAlt.length} images missing alt text`,
        impact: 'Poor SEO and accessibility - images need alt text'
      });
    }
    
    const viewport = document.querySelector('meta[name="viewport"]');
    if (!viewport) {
      issues.ux_ui.push({
        type: 'missing_viewport',
        severity: 'critical',
        message: 'Missing viewport meta tag',
        impact: 'Website may not be mobile-responsive'
      });
    }
    
    const nav = document.querySelector('nav');
    if (!nav) {
      const links = document.querySelectorAll('a[href]');
      if (links.length < 3) {
        issues.ux_ui.push({
          type: 'poor_navigation',
          severity: 'medium',
          message: 'Limited navigation structure found',
          impact: 'Users may have difficulty finding content'
        });
      }
    }
    
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
      const inputs = form.querySelectorAll('input, textarea, select');
      const labels = form.querySelectorAll('label');
      if (inputs.length > labels.length) {
        issues.ux_ui.push({
          type: 'form_missing_labels',
          severity: 'medium',
          message: 'Form inputs missing labels',
          impact: 'Poor accessibility and UX'
        });
        break;
      }
    }
    
    const buttons = document.querySelectorAll('button, a');
    const ctaKeywords = ['sign up', 'get started', 'contact', 'buy', 'order', 'subscribe', 'download'];
    const hasCta = Array.from(buttons).some(btn => 
      ctaKeywords.some(keyword => btn.textContent.toLowerCase().includes(keyword))
    );
    if (!hasCta) {
      issues.ux_ui.push({
        type: 'missing_cta',
        severity: 'medium',
        message: 'No clear call-to-action found',
        impact: 'Users may not know what action to take'
      });
    }
    
    const textContent = document.body.textContent || '';
    const wordCount = textContent.split(/\s+/).filter(w => w.length > 0).length;
    if (wordCount < 300) {
      issues.content.push({
        type: 'thin_content',
        severity: 'medium',
        message: `Page has very little content (${wordCount} words)`,
        impact: 'Poor SEO - search engines prefer substantial content'
      });
    }
    
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    if (headings.length < 2) {
      issues.content.push({
        type: 'poor_content_structure',
        severity: 'medium',
        message: 'Content lacks proper heading structure',
        impact: 'Poor readability and SEO'
      });
    }
    
    return issues;
  }

  // LinkedIn Profile Scraper
  async function scrapeLinkedInProfile() {
    const profile = {
      name: null,
      headline: null,
      company: null,
      position: null,
      location: null,
      email: null,
      phone: null,
      notes: null,  // Will be generated at the end
      source_url: window.location.href,
      source_type: 'linkedin_profile'
    };
    
    const nameSelectors = [
      'h1.text-heading-xlarge',
      'h1[class*="text-heading"]',
      '.pv-text-details__left-panel h1',
      'h1'
    ];
    
    for (const selector of nameSelectors) {
      const nameEl = document.querySelector(selector);
      if (nameEl && nameEl.textContent.trim()) {
        profile.name = nameEl.textContent.trim();
        break;
      }
    }
    
    const headlineSelectors = [
      '.text-body-medium.break-words',
      '[class*="headline"]',
      '.pv-text-details__left-panel .text-body-medium'
    ];
    
    for (const selector of headlineSelectors) {
      const headlineEl = document.querySelector(selector);
      if (headlineEl && headlineEl.textContent.trim()) {
        profile.headline = headlineEl.textContent.trim();
        
        // FIXED: Only extract position/company from headline if it's a clear "Position at CompanyName" pattern
        // AND the company part looks like a real company (not a bio/description)
        const headlineText = profile.headline;
        
        // Check for "Position at CompanyName" pattern
        if (headlineText.includes(' at ')) {
          const parts = headlineText.split(' at ');
          if (parts.length === 2) {
            const potentialCompany = parts[1].trim();
            
            // Validate using comprehensive company validation
            if (isValidCompanyName(potentialCompany)) {
              profile.position = parts[0].trim();
              profile.company = potentialCompany;
            } else {
              // It's likely a description/bio, not a company - just store position
              profile.position = parts[0].trim();
              // Don't set company - will extract from experience section below
            }
          }
        } else if (headlineText.includes(' | ')) {
          // Similar validation for pipe separator
          const parts = headlineText.split(' | ');
          if (parts.length === 2) {
            const potentialCompany = parts[1].trim();
            // Validate using comprehensive company validation
            if (isValidCompanyName(potentialCompany)) {
              profile.position = parts[0].trim();
              profile.company = potentialCompany;
            } else {
              profile.position = parts[0].trim();
            }
          }
        }
        break;
      }
    }
    
    // FIXED: Extract company from LinkedIn Experience Section (Primary method)
    // LinkedIn shows current company in experience section, not in headline
    const experienceSelectors = [
      '.pvs-list__outer-container [data-view-name="profile-component-entity"]',
      '.experience-section .pv-entity__summary-info',
      '[data-section="experience"] .pv-entity__summary-info',
      '.pv-profile-section.experience-section .pv-entity__summary-info-v2',
      '.pv-profile-section__card-item-v2 .pv-entity__summary-info'
    ];
    
    for (const selector of experienceSelectors) {
      const experienceEl = document.querySelector(selector);
      if (experienceEl) {
        // Look for company name - it's usually in a link to /company/ or in a span
        const companyLink = experienceEl.querySelector('a[href*="/company/"]');
        if (companyLink) {
          const companyText = companyLink.textContent.trim();
          // Validate using comprehensive company validation
          if (isValidCompanyName(companyText)) {
            profile.company = companyText;
            // Also try to get position from same section if not already set
            if (!profile.position) {
              const positionEl = experienceEl.querySelector('.t-16.t-black.t-bold, .mr1.t-bold span, h3 span[aria-hidden="true"]');
              if (positionEl) {
                profile.position = positionEl.textContent.trim();
              }
            }
            break;
          }
        } else {
          // Fallback: Look for company text in experience section
          const companyTextEl = experienceEl.querySelector('span[aria-hidden="true"], .t-14.t-normal span, .pv-entity__secondary-title');
          if (companyTextEl) {
            const companyText = companyTextEl.textContent.trim();
            // Validate using comprehensive company validation
            if (isValidCompanyName(companyText)) {
              if (!profile.company) {
                profile.company = companyText;
              }
              // Also try to get position
              if (!profile.position) {
                const positionEl = experienceEl.querySelector('.t-16.t-black.t-bold, h3 span[aria-hidden="true"]');
                if (positionEl) {
                  profile.position = positionEl.textContent.trim();
                }
              }
              break;
            }
          }
        }
      }
    }
    
    // ALTERNATIVE: Look for company in profile summary area (if experience section didn't work)
    if (!profile.company) {
      const companySelectors = [
        '.pv-text-details__left-panel a[href*="/company/"]',
        '.text-body-medium a[href*="/company/"]',
        '[data-control-name="background_details_company"]',
        'a[href*="/company/"][class*="link"]'
      ];
      
      for (const selector of companySelectors) {
        const companyEl = document.querySelector(selector);
        if (companyEl) {
          const companyText = companyEl.textContent.trim();
          // Validate using comprehensive company validation
          if (isValidCompanyName(companyText)) {
            profile.company = companyText;
            break;
          }
        }
      }
    }
    
    const locationSelectors = [
      '.text-body-small.inline.t-black--light.break-words',
      '[class*="location"]',
      '.pv-text-details__left-panel .text-body-small'
    ];
    
    for (const selector of locationSelectors) {
      const locationEl = document.querySelector(selector);
      if (locationEl && locationEl.textContent.trim() && !locationEl.textContent.includes('connections')) {
        profile.location = locationEl.textContent.trim();
        break;
      }
    }
    
    const contactSection = document.querySelector('[data-section="contactInfo"]');
    if (contactSection) {
      const emailEl = contactSection.querySelector('a[href^="mailto:"]');
      if (emailEl) {
        const email = emailEl.getAttribute('href').replace('mailto:', '').trim();
        // Validate email before setting it
        if (isValidEmail(email)) {
          profile.email = email.toLowerCase();
        }
      }
      
      const phoneEl = contactSection.querySelector('a[href^="tel:"]');
      if (phoneEl) {
        profile.phone = phoneEl.getAttribute('href').replace('tel:', '');
      }
    }
    
    // If email not found, try checking the contact-info overlay URL
    if (!profile.email) {
      const urlMatch = window.location.pathname.match(/\/in\/([^\/]+)/);
      if (urlMatch) {
        const username = urlMatch[1];
        const contactInfoUrl = `https://www.linkedin.com/in/${username}/overlay/contact-info/`;
        
        // First, try to find and click contact info button/link if it exists
        const contactInfoButton = document.querySelector(
          'a[href*="overlay/contact-info"], ' +
          'button[aria-label*="contact"], ' +
          'a[href*="contact-info"], ' +
          'button[data-control-name="contact_info"], ' +
          '.pv-contact-info__contact-type, ' +
          'a[href*="/in/' + username + '/overlay/contact-info"]'
        );
        
        // Try to extract email from any visible contact info elements on the page
        const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
        const pageText = document.body.textContent || '';
        const emailMatches = pageText.match(emailPattern);
        if (emailMatches) {
          // Filter using comprehensive email validation
          const validEmails = emailMatches.filter(email => isValidEmail(email));
          if (validEmails.length > 0) {
            profile.email = validEmails[0].toLowerCase().trim();
          }
        }
        
        // Try to fetch the overlay URL directly (may work if user is logged in and has access)
        if (!profile.email) {
          try {
            const response = await fetch(contactInfoUrl, {
              method: 'GET',
              credentials: 'include',
              headers: {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'X-Requested-With': 'XMLHttpRequest'
              }
            });
            
            if (response.ok) {
              const html = await response.text();
              const parser = new DOMParser();
              const doc = parser.parseFromString(html, 'text/html');
              
              // Look for email in the overlay content
              const emailEl = doc.querySelector('a[href^="mailto:"]');
              if (emailEl) {
                const email = emailEl.getAttribute('href').replace('mailto:', '').trim();
                // Validate email before setting it
                if (isValidEmail(email)) {
                  profile.email = email.toLowerCase();
                }
              } else {
                // Try regex on the HTML content
                const emailMatches = html.match(emailPattern);
                if (emailMatches) {
                  // Filter using comprehensive email validation
                  const validEmails = emailMatches.filter(email => isValidEmail(email));
                  if (validEmails.length > 0) {
                    profile.email = validEmails[0].toLowerCase().trim();
                  }
                }
              }
              
              // Also check for phone in overlay
              const phoneEl = doc.querySelector('a[href^="tel:"]');
              if (phoneEl && !profile.phone) {
                profile.phone = phoneEl.getAttribute('href').replace('tel:', '').trim();
              }
            }
          } catch (fetchError) {
            // Fetch might fail due to CORS, authentication, or network - that's okay, we tried
            console.log('Could not fetch contact-info overlay (this is normal if not connected or no access):', fetchError.message);
          }
        }
      }
    }
    
    // Final validation: If company doesn't pass validation, set to null (will show as "Not Found")
    if (profile.company && !isValidCompanyName(profile.company)) {
      profile.company = null;
    }
    
    // Final validation: If email doesn't pass validation, set to null
    if (profile.email && !isValidEmail(profile.email)) {
      profile.email = null;
    }
    
    // Generate structured notes for LinkedIn profile
    profile.notes = generateLinkedInNotes(profile);
    
    return { contacts: [profile], company: null };
  }

  // Generate structured notes for LinkedIn profile
  function generateLinkedInNotes(profile) {
    const notes = [];
    
    // Basic profile info
    if (profile.headline) {
      notes.push(`Headline: ${profile.headline}`);
    }
    if (profile.position) {
      notes.push(`Position: ${profile.position}`);
    }
    if (profile.company) {
      notes.push(`Company: ${profile.company}`);
    } else {
      notes.push(`Company: Not Found`);
    }
    if (profile.location) {
      notes.push(`Location: ${profile.location}`);
    }
    
    // Contact info
    if (profile.phone) {
      notes.push(`Phone: ${profile.phone}`);
    }
    
    // Source info
    notes.push(`Source: LinkedIn Profile`);
    notes.push(`Profile URL: ${profile.source_url}`);
    
    // Additional context
    notes.push(`\nScraped from: ${window.location.href}`);
    notes.push(`Date: ${new Date().toISOString().split('T')[0]}`);
    
    return notes.join('\n');
  }

  // LinkedIn Company Scraper
  function scrapeLinkedInCompany() {
    const company = {
      name: null,
      description: null,
      website: null,
      industry: null,
      company_size: null,
      location: null,
      linkedin_url: window.location.href,
      source_type: 'linkedin_company'
    };
    
    const nameEl = document.querySelector('h1.org-top-card-summary__title, h1[class*="company-name"]');
    if (nameEl) {
      company.name = nameEl.textContent.trim();
    }
    
    const descEl = document.querySelector('.org-about-us-organization-description__text, [class*="description"]');
    if (descEl) {
      company.description = descEl.textContent.trim();
    }
    
    const websiteEl = document.querySelector('a[data-control-name="website"]');
    if (websiteEl) {
      company.website = websiteEl.getAttribute('href');
    }
    
    const infoItems = document.querySelectorAll('.org-top-card-summary-info-list__info-item');
    infoItems.forEach(item => {
      const text = item.textContent.trim();
      if (text.includes('employees') || text.match(/\d+-\d+/)) {
        company.company_size = text;
      } else if (!company.industry) {
        company.industry = text;
      }
    });
    
    return { contacts: [], company: company };
  }

  // Google Maps Scraper
  async function scrapeGoogleMaps() {
    const business = {
      name: null,
      address: null,
      phone: null,
      website: null,
      rating: null,
      reviews_count: null,
      category: null,
      hours: null,
      email: null,
      source_url: window.location.href,
      source_type: 'google_maps'
    };
    
    // Wait a bit for Google Maps to fully load
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Try multiple selectors for business name (Google Maps UI changes frequently)
    const nameSelectors = [
      'h1[data-attrid="title"]',
      'h1.DUwDvf',
      'h1[class*="title"]',
      'h1[class*="Title"]',
      'h1.qrShPb',
      'h1.x3AX1-LfntMc-header-title-title',
      'h1[data-value]',
      'h1',
      '[data-value][role="heading"]'
    ];
    
    for (const selector of nameSelectors) {
      const nameEl = document.querySelector(selector);
      if (nameEl && nameEl.textContent.trim()) {
        business.name = nameEl.textContent.trim();
        break;
      }
    }
    
    // Try multiple selectors for address
    const addressSelectors = [
      '[data-item-id="address"]',
      'button[data-item-id="address"]',
      'button[data-value*="address"]',
      '[data-value*="address"]',
      'button[aria-label*="Address"]',
      '[aria-label*="Address"]',
      '.Io6YTe[data-value]',
      'button[jsaction*="address"]'
    ];
    
    for (const selector of addressSelectors) {
      const addressEl = document.querySelector(selector);
      if (addressEl && addressEl.textContent.trim() && addressEl.textContent.length > 10) {
        business.address = addressEl.textContent.trim();
        break;
      }
    }
    
    // Try multiple selectors for phone
    const phoneSelectors = [
      '[data-item-id^="phone"]',
      'button[data-item-id^="phone"]',
      'button[data-value*="phone"]',
      '[data-value*="phone"]',
      'button[aria-label*="Phone"]',
      '[aria-label*="Phone"]',
      'a[href^="tel:"]',
      'button[jsaction*="phone"]'
    ];
    
    for (const selector of phoneSelectors) {
      const phoneEl = document.querySelector(selector);
      if (phoneEl) {
        const phoneText = phoneEl.textContent.trim() || phoneEl.getAttribute('href')?.replace('tel:', '');
        if (phoneText && phoneText.length > 5) {
          business.phone = phoneText;
          break;
        }
      }
    }
    
    // Try multiple selectors for website
    const websiteSelectors = [
      'a[data-item-id="authority"]',
      'a[href*="http"][data-value]',
      'button[data-item-id="authority"]',
      'a[aria-label*="Website"]',
      'button[aria-label*="Website"]',
      'a[href^="http"]:not([href*="google.com"])'
    ];
    
    for (const selector of websiteSelectors) {
      const websiteEl = document.querySelector(selector);
      if (websiteEl) {
        const href = websiteEl.getAttribute('href') || websiteEl.getAttribute('data-value');
        if (href && href.startsWith('http')) {
          business.website = href;
          break;
        }
      }
    }
    
    // Try to find rating
    const ratingSelectors = [
      '[data-value]',
      '.F7nice',
      '[aria-label*="rating"]',
      '[aria-label*="stars"]',
      '.MW4etd',
      '[class*="rating"]'
    ];
    
    for (const selector of ratingSelectors) {
      const ratingEl = document.querySelector(selector);
      if (ratingEl) {
        const ratingText = ratingEl.textContent.trim() || ratingEl.getAttribute('aria-label') || '';
        const ratingMatch = ratingText.match(/(\d+\.?\d*)/);
        if (ratingMatch) {
          const rating = parseFloat(ratingMatch[1]);
          if (rating >= 1 && rating <= 5) {
            business.rating = rating;
            break;
          }
        }
      }
    }
    
    // Try to find category
    const categoryEl = document.querySelector('[data-value][class*="category"], button[data-value*="category"], [aria-label*="category"]');
    if (categoryEl) {
      business.category = categoryEl.textContent.trim();
    }
    
    // If we have a website, try to scrape email from it
    if (business.website && !business.email) {
      try {
        // Convert HTTP to HTTPS to avoid mixed content errors
        let websiteUrl = business.website;
        if (websiteUrl.startsWith('http://')) {
          websiteUrl = websiteUrl.replace('http://', 'https://');
        }
        
        // Only try to fetch if we're on HTTPS or if URL is HTTPS
        const isHttpsPage = window.location.protocol === 'https:';
        const isHttpsUrl = websiteUrl.startsWith('https://');
        
        if (isHttpsPage && !isHttpsUrl) {
          // Skip HTTP websites on HTTPS pages to avoid mixed content errors
          console.log('Skipping HTTP website fetch on HTTPS page to avoid mixed content error');
        } else {
          // Fetch the website and look for email
          try {
            const response = await fetch(websiteUrl, {
              method: 'GET',
              credentials: 'omit',
              mode: 'cors',
              headers: {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
              }
            });
            
            if (response.ok) {
              const html = await response.text();
              const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
              const emailMatches = html.match(emailPattern);
              if (emailMatches) {
                // Filter using comprehensive email validation
                const validEmails = emailMatches.filter(email => isValidEmail(email));
                // Prefer contact/sales/hello emails
                const preferredEmails = validEmails.filter(e => {
                  const eLower = e.toLowerCase();
                  return eLower.includes('contact') || 
                         eLower.includes('hello') || 
                         eLower.includes('sales') ||
                         eLower.includes('info');
                });
                if (preferredEmails.length > 0) {
                  business.email = preferredEmails[0].toLowerCase().trim();
                } else if (validEmails.length > 0) {
                  business.email = validEmails[0].toLowerCase().trim();
                }
              }
            }
          } catch (fetchError) {
            // Website fetch might fail due to CORS, mixed content, or network - that's okay
            // Silently fail - we'll try to find email on the current page instead
            console.log('Could not fetch business website for email (this is normal):', fetchError.message);
          }
        }
      } catch (error) {
        // General error handling
        console.log('Error processing website URL:', error.message);
      }
    }
    
    // If still no email, try searching the current Google Maps page
    if (!business.email) {
      const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
      const pageText = document.body.textContent || '';
      const emailMatches = pageText.match(emailPattern);
      if (emailMatches) {
        // Filter using comprehensive email validation
        const validEmails = emailMatches.filter(email => isValidEmail(email));
        if (validEmails.length > 0) {
          business.email = validEmails[0].toLowerCase().trim();
        }
      }
    }
    
    // Only return contact if we have at least name or email
    const contacts = [];
    if (business.name || business.email) {
      contacts.push({
        name: business.name || 'Business Contact',
        company: business.name,
        phone: business.phone,
        email: business.email,
        position: null,
        address: business.address,
        source_url: business.source_url,
        source_type: 'google_maps'
      });
    }
    
    // Add instruction message if website found but no email
    if (business.website && !business.email) {
      business.message = `📧 Email not found on Google Maps. To find the email, open the website (${business.website}) and use the extension to scrape it.`;
    }
    
    return {
      contacts: contacts,
      company: business
    };
  }

  // Instagram Profile Scraper
  function scrapeInstagramProfile() {
    const profile = {
      username: null,
      name: null,
      bio: null,
      website: null,
      followers: null,
      following: null,
      posts_count: null,
      email: null,
      phone: null,
      source_url: window.location.href,
      source_type: 'instagram_profile'
    };
    
    const urlMatch = window.location.pathname.match(/\/([^\/]+)\/?$/);
    if (urlMatch) {
      profile.username = urlMatch[1];
    }
    
    const nameEl = document.querySelector('h1, h2, [class*="username"]');
    if (nameEl) {
      profile.name = nameEl.textContent.trim();
    }
    
    const bioEl = document.querySelector('[class*="bio"], [class*="Biography"]');
    if (bioEl) {
      profile.bio = bioEl.textContent.trim();
    }
    
    const websiteEl = document.querySelector('a[href^="http"]');
    if (websiteEl && !websiteEl.href.includes('instagram.com')) {
      profile.website = websiteEl.href;
    }
    
    return { contacts: [profile], company: null };
  }

  // Message listener
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'detectPlatform') {
      sendResponse({ platform: detectPlatform() });
      return true;
    }
    
    if (request.action === 'scrape') {
      (async () => {
        const platform = detectPlatform();
        let result = { platform, data: null, validation: null };
        
        try {
          switch(platform) {
            case 'website':
              result.data = await scrapeWebsite();
              result.validation = validateWebsite();
              break;
            case 'linkedin_profile':
              result.data = await scrapeLinkedInProfile();
              break;
            case 'linkedin_company':
              result.data = scrapeLinkedInCompany();
              break;
            case 'google_maps':
              result.data = await scrapeGoogleMaps();
              break;
            case 'instagram_profile':
              result.data = scrapeInstagramProfile();
              break;
            default:
              result.data = { error: 'Platform not supported' };
          }
        } catch (error) {
          result.data = { error: error.message };
        }
        
        sendResponse(result);
      })();
      return true; // Keep channel open for async response
    }
    
    return false;
  });
})();

