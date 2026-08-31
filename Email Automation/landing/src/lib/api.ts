import axios from 'axios';

// Compute base URL for API calls
const computeBaseURL = (): string => {
  // Check environment variable first
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // Client-side
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    // Production: point to API domain
    if (origin.includes('wolfassistants.com')) {
      return 'https://api.wolfassistants.com/api/v1';
    }
    // Development
    if (origin.includes(':3000')) {
      return 'http://localhost:8000/api/v1';
    }
  }
  
  // Default fallback
  return 'http://localhost:8000/api/v1';
};

export const api = axios.create({
  baseURL: computeBaseURL(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  validateStatus: (status) => status >= 200 && status < 400,
});

// Add request interceptor for auth tokens (client-side only)
if (typeof window !== 'undefined') {
  api.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );
  
  // Response interceptor for handling 401 errors
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Redirect to login on app domain
        const appUrl = process.env.REACT_APP_APP_URL || 'https://app.wolfassistants.com';
        window.location.href = `${appUrl}/login`;
      }
      return Promise.reject(error);
    }
  );
}
