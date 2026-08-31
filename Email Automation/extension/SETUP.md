# Extension Setup Guide

## Quick Start

1. **Create Icon Files** (Required)
   - Create 3 PNG files: `icon16.png`, `icon48.png`, `icon128.png`
   - Place them in the `icons/` folder
   - You can use any simple icon (even a placeholder) for testing

2. **Load Extension in Chrome/Edge**
   - Open Chrome/Edge → Extensions (chrome://extensions/)
   - Enable "Developer mode" (toggle in top-right)
   - Click "Load unpacked"
   - Select the `extension` folder
   - Extension icon will appear in toolbar

3. **Get Authentication Token**
   - Log in to WolfAssistants web app
   - Open browser DevTools (F12) → Application/Storage → Local Storage
   - Find the `token` key and copy its value
   - OR: The extension will prompt you for it on first use

4. **Start Backend**
   - Make sure backend is running on `http://localhost:8000`
   - Run: `cd backend && python main.py`

## Usage

1. Navigate to any supported platform:
   - 🌐 Company Website
   - 💼 LinkedIn Profile
   - 🏢 LinkedIn Company
   - 📍 Google Maps Business
   - 📷 Instagram Profile

2. Click the extension icon

3. Click "Scrape [Platform Name]"

4. Review scraped contacts and validation results

5. Click "Add to WolfAssistants" to save with auto-generated research notes

## Supported Platforms

- **Websites**: Scrapes emails, names, titles + validates SEO/UX/Content
- **LinkedIn Profiles**: Extracts profile info, headline, company, position
- **LinkedIn Companies**: Extracts company info, description, industry
- **Google Maps**: Scrapes business name, address, phone, website, rating
- **Instagram**: Extracts profile info, bio, website link

## Features

✅ Real-time scraping (no fake data)
✅ Website validation (SEO, UX/UI, Content issues)
✅ Purpose-aware research notes (based on your profession)
✅ Auto-adds to Contacts page
✅ Multi-platform support

## Troubleshooting

**Extension not working?**
- Make sure backend is running on localhost:8000
- Check browser console for errors (F12)
- Verify authentication token is correct

**No contacts found?**
- Some pages may not have visible contact info
- Try different pages on the same website
- LinkedIn/Instagram may require login

**Validation not showing?**
- Only works on regular websites (not LinkedIn/Instagram)
- Website must be fully loaded before scraping

## API Endpoint

The extension calls: `POST http://localhost:8000/api/v1/extension/scrape-and-add`

Requires:
- Authorization: Bearer [your-token]
- Content-Type: application/json

Payload:
```json
{
  "contacts": [...],
  "company": {...},
  "validation": {...},
  "platform": "website"
}
```

