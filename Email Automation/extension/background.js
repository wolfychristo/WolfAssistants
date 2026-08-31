// background.js - Service worker
chrome.runtime.onInstalled.addListener(() => {
  console.log('WolfAssistants Lead Scraper installed');
});

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'log') {
    console.log('[Extension]', request.message);
  }
  return true;
});

