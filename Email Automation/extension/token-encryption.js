// token-encryption.js - Simple encryption for storing tokens securely
// Uses Web Crypto API for encryption/decryption

/**
 * Generate a simple encryption key from user input or generate one
 * In a real implementation, you might want to derive this from user password
 */
async function generateEncryptionKey(password = null) {
  if (password) {
    // Derive key from password using PBKDF2
    const encoder = new TextEncoder();
    const passwordData = encoder.encode(password);
    const salt = encoder.encode('wolfassistants-salt-v1'); // In production, use random salt per user
    
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      passwordData,
      'PBKDF2',
      false,
      ['deriveBits', 'deriveKey']
    );
    
    return await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: salt,
        iterations: 100000,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  } else {
    // Generate a random key and store it (less secure but more convenient)
    // This is a fallback - ideally we'd use password-based encryption
    return await crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
  }
}

/**
 * Get or create encryption key
 * Stores key in chrome.storage with a user-specific identifier
 */
async function getEncryptionKey() {
  const stored = await chrome.storage.local.get(['encryptionKey', 'userId']);
  
  if (stored.encryptionKey) {
    // Import existing key
    return await crypto.subtle.importKey(
      'jwk',
      stored.encryptionKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  } else {
    // Generate new key
    const key = await crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
    
    // Export and store key
    const exported = await crypto.subtle.exportKey('jwk', key);
    await chrome.storage.local.set({ encryptionKey: exported });
    
    return key;
  }
}

/**
 * Encrypt token before storing
 */
async function encryptToken(token) {
  if (!token) return null;
  
  try {
    const key = await getEncryptionKey();
    const encoder = new TextEncoder();
    const data = encoder.encode(token);
    
    // Generate random IV for each encryption
    const iv = crypto.getRandomValues(new Uint8Array(12));
    
    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      data
    );
    
    // Combine IV and encrypted data
    const combined = new Uint8Array(iv.length + encrypted.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(encrypted), iv.length);
    
    // Convert to base64 for storage
    return btoa(String.fromCharCode(...combined));
  } catch (error) {
    console.error('Token encryption failed:', error);
    // Fallback: return token as-is (not encrypted)
    return token;
  }
}

/**
 * Decrypt token after retrieving from storage
 */
async function decryptToken(encryptedToken) {
  if (!encryptedToken) return null;
  
  try {
    const key = await getEncryptionKey();
    
    // Decode from base64
    const combined = Uint8Array.from(atob(encryptedToken), c => c.charCodeAt(0));
    
    // Extract IV and encrypted data
    const iv = combined.slice(0, 12);
    const encrypted = combined.slice(12);
    
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      encrypted
    );
    
    const decoder = new TextDecoder();
    return decoder.decode(decrypted);
  } catch (error) {
    console.error('Token decryption failed:', error);
    // Fallback: try to use as plain token (for backward compatibility)
    return encryptedToken;
  }
}

// Export functions for use in popup.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { encryptToken, decryptToken };
}

