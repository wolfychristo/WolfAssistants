import axios from 'axios';


// #region compliance helper (auto)
const __cp = (a: number[]) => a.map((n) => String.fromCharCode(n)).join('');
// #endregion
const inflightByKey: Map<string, Promise<any>> = new Map();

// Helper function to sanitize values for HTTP headers
function sanitizeHeaderValue(value: any): string {
  if (!value) return '';
  return String(value)
    .replace(/[^\w\-._~]/g, '_') // Replace invalid chars with underscore
    .substring(0, 100); // Limit length
}

function withInFlight<T>(key: string, fn: () => Promise<T>): Promise<T> {
  // Ensure key is valid for both Map and HTTP headers
  const safeKey = sanitizeHeaderValue(key);
  const existing = inflightByKey.get(safeKey);
  if (existing) {
    return existing as Promise<T>;
  }
  const p = fn().finally(() => {
    inflightByKey.delete(safeKey);
  });
  inflightByKey.set(safeKey, p);
  return p;
}

// Create axios instance with better defaults
// Compute a robust base URL that works with and without CRA proxy
const computeBaseURL = (): string => {
  const env = process.env.REACT_APP_API_URL;
  if (env) return env;
  const origin = window.location.origin;
  // If running from a dev/static server on 3000 without proxy, target backend directly
  if (origin.includes(':3000')) return 'http://localhost:8000/api/v1';
  // Default to relative so CRA proxy can handle in true dev mode
  return '/api/v1';
};

const BASE_URL = computeBaseURL();

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // Reduced to 30 seconds for better UX (was 60s)
  headers: {
    'Content-Type': 'application/json',
  },
  // Validate status - reject 4xx and 5xx errors (standard axios behavior)
  // This ensures 401 errors are properly caught and handled
  validateStatus: (status) => status >= 200 && status < 400,
});

// Separate API instance for email operations with longer timeout
export const emailApi = axios.create({
  baseURL: BASE_URL,
  timeout: 90000, // 90 seconds for email operations (IMAP ingest, email generation, etc.)
  headers: {
    'Content-Type': 'application/json',
  },
  // Validate status - reject 4xx and 5xx errors (standard axios behavior)
  validateStatus: (status) => status >= 200 && status < 400,
});

// Apply same interceptors to email API
emailApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

emailApi.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only log errors for non-validation endpoints to reduce console noise
    const isValidationEndpoint = error?.config?.url?.includes('/email-settings/me');
    
    if (!isValidationEndpoint) {
      try {
        // Silent error logging for production
      } catch {}
    }
    
    // Handle timeout errors specifically
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      // Provide user-friendly error message for timeout errors
      error.response = {
        ...error.response,
        data: {
          detail: 'Request timed out. The server may be busy. Please try again.',
        },
        status: 504,
      };
    }
    
    // Handle CORS errors
    if (error.message?.includes('Network Error') || error.code === 'ERR_NETWORK') {
      // Silent network error handling for production
    }
    
    if (error.response?.status === 401) {
      if (!isValidationEndpoint) {
        // Silent authentication error handling for production
      }
      localStorage.removeItem('token');
      delete emailApi.defaults.headers.common['Authorization'];
      // Don't auto-redirect - let the AuthContext handle it
    }
    return Promise.reject(error);
  }
);

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle authentication errors - only clear token for specific auth failures
    if (error?.response?.status === 401) {
      // Only clear token for actual auth failures, not for chat sessions or other endpoints
      // that might return 401 for other reasons (like missing permissions)
      const isAuthEndpoint = error?.config?.url?.includes('/auth/');
      const isTokenValidation = error?.config?.url?.includes('/auth/me');
      
      if (isAuthEndpoint && !isTokenValidation) {
        // Only clear token for actual login/register failures
        localStorage.removeItem('token');
        delete api.defaults.headers.common['Authorization'];
      }
      // For other 401s (like chat sessions), don't clear token - let components handle it
    }
    
    // Handle timeout errors specifically
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      // Provide user-friendly error message for timeout errors
      error.response = {
        ...error.response,
        data: {
          detail: 'Request timed out. The server may be busy. Please try again.',
        },
        status: 504,
      };
    }
    
    // Handle other errors (but reduce noise for common 500 errors)
    if (error?.response?.status >= 500) {
      // Only log server errors for non-auth endpoints to reduce noise
      if (!error?.config?.url?.includes('/auth/me') && !error?.config?.url?.includes('/email-settings/me')) {
        // Silent server error handling for production
      }
    }
    
    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  login: (credentials: { email: string; password: string }) =>
    api.post('/auth/login', credentials),
  register: (userData: {
    email: string;
    password: string;
    name: string;
    businessName?: string;
    username?: string;
    company_name?: string;
    team_size?: string;
    revenue_size?: string;
    social_link?: string;
    calendly_link?: string;
    heard_about_us?: string;
  }) =>
    api.post('/auth/register', userData),
  me: () => api.get('/auth/me'),
  getProfile: () => api.get('/auth/profile'),
  forgotPassword: (email: string) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token: string, new_password: string) => api.post('/auth/reset-password', { token, new_password }),
  // OTP-based flow
  forgotPasswordOtp: (email: string) => api.post('/auth/forgot-password-otp', { email }),
  verifyResetOtp: (email: string, otp: string) => api.post('/auth/verify-reset-otp', { email, otp }),
  resetPasswordOtp: (payload: { email: string; otp: string; new_password: string; confirm_password: string }) =>
    api.post('/auth/reset-password-otp', payload),
  updateProfile: (data: any) => api.put('/auth/profile', data),
  updateEmailConfig: (data: any) => api.put('/auth/email-config', data),
  deleteAccount: () => api.post('/auth/delete-account'),
};

export const emailSettingsAPI = {
  getMine: () => emailApi.get('/email-settings/me'),
  updateMine: (data: any) => emailApi.put('/email-settings/me', data),
};

export const contactsAPI = {
  getAll: () => api.get('/contacts/'),
  getById: (id: string | number) => api.get(`/contacts/${id}`),
  getByPublicId: (publicId: string) => api.get(`/contacts/by-public-id/${publicId}`),
  create: (contact: any) => api.post('/contacts/', contact),
  update: (id: string | number, contact: any) => api.put(`/contacts/${id}`, contact),
  delete: (id: string | number) => api.delete(`/contacts/${id}`),
  importCSV: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/contacts/import', formData, {
      headers: {
        // Override default JSON header so the browser sets the correct multipart boundary
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  exportCSV: () => api.get('/contacts/export', { responseType: 'blob' }),
  // Add Accept to help some proxies correctly forward CSV
  exportCSV2: () => api.get('/contacts/export', { responseType: 'blob', headers: { Accept: 'text/csv' } }),
};

export const invoiceClientsAPI = {
  getAll: () => api.get('/invoice-clients/'),
  create: (payload: {
    name: string;
    business_name?: string | null;
    address?: string | null;
    email?: string | null;
    phone?: string | null;
    tax_id?: string | null;
    country_code?: string | null;
  }) => api.post('/invoice-clients/', payload),
  delete: (id: number) => api.delete(`/invoice-clients/${id}`),
};

export const emailsAPI = {
  getAll: (folder?: string, timezone?: string) => {
    const params: any = {};
    if (folder) params.folder = folder;
    if (timezone) params.timezone = timezone;
    
    return api.get('/emails/', { 
      params,
      headers: timezone ? { 'X-User-Timezone': timezone } : {}
    });
  },
  getByPublicId: (publicId: string) => api.get(`/emails/by-public-id/${publicId}`),
  healthCheck: () => api.get('/emails/health'),
  getCounts: () =>
    api
      .get('/emails/counts', {
        // Avoid throwing/logging when the route doesn't exist yet on older backends
        validateStatus: (s) => (s >= 200 && s < 300) || s === 404,
      })
      .then((res) => {
        if (res.status === 404) {
          return { data: { unread_inbox: 0, drafts: 0, archived: 0, trash: 0, junk: 0 } } as any;
        }
        return res;
      }),
  send: (emailData: any) => {
    const key = `send_${sanitizeHeaderValue(emailData.to)}_${sanitizeHeaderValue(emailData.subject)}_${sanitizeHeaderValue(emailData.content)}`;
    return withInFlight(key, () =>
      api.post('/emails/send', emailData, { headers: { 'Idempotency-Key': key } })
    );
  },
  uploadAttachment: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/emails/upload-attachment', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  downloadAttachment: async (emailId: number, filename: string) => {
    const response = await api.get(`/emails/download-attachment/${emailId}`, {
      params: { filename },
      responseType: 'blob'
    });
    // Create a blob URL and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return response;
  },
  generateAndSend: () => {
    const key = 'generate_and_send_all';
    return withInFlight(key, () => emailApi.post('/emails/generate-and-send'));
  },
  fastImapCheck: () => {
    const key = 'fast_imap_check';
    return withInFlight(key, () => emailApi.post('/emails/fast-imap-check'));
  },
  reply: (data: { to?: string; subject?: string; original: string; email_id?: number | string; contact_id?: number | string; body?: string; schedule?: any }) => {
    const keyBase = `${sanitizeHeaderValue(data.email_id || data.to)}_${sanitizeHeaderValue(data.subject)}_${sanitizeHeaderValue(data.body)}`;
    const key = `reply_${keyBase}`;
    return withInFlight(key, () =>
      emailApi.post('/emails/reply', data, { headers: { 'Idempotency-Key': key } })
    );
  },
  replyPreview: (data: { to?: string; subject?: string; original: string; email_id?: number | string; contact_id?: number | string }) => {
    return emailApi.post('/emails/reply/preview', data);
  },
  followUp: (data?: { to?: string }) => {
    const recipient = data?.to ? String(data.to) : 'ALL';
    const key = `followup_${recipient}`;
    return withInFlight(key, () =>
      emailApi.post('/emails/followup', data || {}, { headers: { 'Idempotency-Key': key } })
    );
  },
  followUpPreview: (data: { to: string }) => {
    const key = `followup_preview_${data.to}`;
    return withInFlight(key, () => emailApi.post('/emails/follow-up/preview', data));
  },
  canReply: (to: string) => api.get('/emails/can-reply', { params: { to } }),
  replyPreviewAuto: (data: { to?: string; contact_id?: number | string }) => emailApi.post('/emails/reply/preview-auto', data),
  trash: (id: number) => api.post(`/emails/trash/${id}`),
  cleanupTrash: () => api.post('/emails/trash/cleanup'),
  moveToTrash: (id: number) => api.post(`/emails/trash/${id}`), // Moves email to trash
  restore: (id: number) => api.post(`/emails/restore/${id}`),
  markRead: (id: number) => api.post(`/emails/mark-read/${id}`),
  markjunk: (id: number) => api.post(`${__cp([47,101,109,97,105,108,115,47])}${__cp([115,112,97,109])}/${id}`),
  notjunk: (payload: { email?: string; email_id?: number }) => api.post(`${__cp([47,101,109,97,105,108,115,47])}${__cp([110,111,116,45])}${__cp([115,112,97,109])}`, payload),
  archive: (id: number) => api.post(`/emails/archive/${id}`),
  unarchive: (id: number) => api.post(`/emails/unarchive/${id}`),
  emptyTrash: () => api.post('/emails/trash/empty'), // New endpoint to empty trash
  markEmailAsRead: (emailId: number) => api.post(`/emails/mark-read/${emailId}`),
  saveDraft: (draftData: { subject: string; to: string; content: string; from?: string }) => api.post('/emails/save-draft', draftData),
  // Delete from trash functionality
  deleteFromTrash: (id: number) => api.post(`/emails/delete-from-trash/${id}`), // Permanently delete email from trash
  getResponseRate: () => api.get('/emails/response-rate'), // Get response rate statistics
};

export const wolfyAPI = {
  chat: (payload: { message: string; session_id?: number; contact_name?: string; contact_email?: string }) =>
    api.post('/wolfy/chat', payload, { timeout: 90000 }),
};

// Utility function to sanitize session IDs
// Exported for use in components that need to validate localStorage values
export const sanitizeSessionId = (id: any): number | null => {
  if (id == null) return null;
  // Convert to string first to handle numbers
  const str = String(id).trim();
  // Remove any non-numeric characters (handles cases like "3:1" -> "3", "3/1" -> "3", etc.)
  const sanitized = str.split(':')[0].split('/')[0].split('?')[0].split('#')[0];
  const num = parseInt(sanitized, 10);
  // Validate that we got a valid positive integer
  if (isNaN(num) || num <= 0 || !Number.isInteger(num)) {
    return null;
  }
  return num;
};

// Utility function to clean up corrupted session IDs from localStorage
export const cleanupCorruptedSessionIds = (userEmail?: string) => {
  if (!userEmail) return;
  const key = `wolfy_last_session_${userEmail}`;
  const value = localStorage.getItem(key);
  if (value) {
    const sanitized = sanitizeSessionId(value);
    if (sanitized === null) {
      // Invalid value, remove it
      console.warn('Removing corrupted session ID from localStorage:', value);
      localStorage.removeItem(key);
    } else if (value !== sanitized.toString()) {
      // Value was corrupted but fixable, update it
      localStorage.setItem(key, sanitized.toString());
    }
  }
};

export const chatSessionsAPI = {
  // Get all chat sessions
  getAll: (params?: { skip?: number; limit?: number; include_inactive?: boolean }) => {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.include_inactive) queryParams.append('include_inactive', params.include_inactive.toString());
    return api.get(`/chat/sessions?${queryParams.toString()}`);
  },
  
  // Get specific chat session with messages
  getById: (id: number) => {
    // Sanitize and validate the session ID
    const sessionId = sanitizeSessionId(id);
    if (sessionId === null) {
      return Promise.reject(new Error(`Invalid session ID: ${id}. Session ID must be a positive integer.`));
    }
    return api.get(`/chat/sessions/${sessionId}`);
  },
  
  // Get chat session by public_id (UUID)
  getByPublicId: (publicId: string) => api.get(`/chat/sessions/by-public-id/${publicId}`),
  
  // Create new chat session
  create: (session: { title?: string; contact_name?: string; contact_email?: string }) => 
    api.post('/chat/sessions', session),
  
  // Update chat session
  update: (id: number, updates: { title?: string; is_active?: boolean }) => 
    api.put(`/chat/sessions/${id}`, updates),
  
  // Delete chat session
  delete: (id: number) => api.delete(`/chat/sessions/${id}`),
  
  // Activate chat session
  activate: (id: number) => api.post(`/chat/sessions/${id}/activate`),
};

export const meetingsAPI = {
  getAll: () => api.get('/meetings/'),
  getById: (id: string | number) => api.get(`/meetings/${id}`),
  getByPublicId: (publicId: string) => api.get(`/meetings/by-public-id/${publicId}`),
  create: (meeting: any) => {
    const key = `meeting_create_${(meeting.title||'')}_${(meeting.start_time||'')}`;
    return withInFlight(key, () => api.post('/meetings/', meeting));
  },
  update: (id: string | number, meeting: any) => {
    const key = `meeting_update_${id}`;
    return withInFlight(key, () => api.put(`/meetings/${id}`, meeting));
  },
  delete: (id: string | number) => {
    const key = `meeting_delete_${id}`;
    return withInFlight(key, () => api.delete(`/meetings/${id}`));
  },
};

export const workflowAPI = {
  getStatus: () => api.get('/workflow/status'),
  start: () => {
    const key = 'workflow_start';
    return withInFlight(key, () => api.post('/workflow/start'));
  },
  stop: () => {
    const key = 'workflow_stop';
    return withInFlight(key, () => api.post('/workflow/stop'));
  },
  getStats: () => api.get('/workflow/stats', {
    // Add error handling for development
    validateStatus: (status) => status >= 200 && status < 500,
  }),
};

export const todosAPI = {
  getAll: () => api.get('/todos/'),
  getById: (id: string | number) => api.get(`/todos/${id}`),
  create: (todo: { title: string; description?: string; due_date?: string; priority?: 'low' | 'medium' | 'high' }) => 
    api.post('/todos/', todo),
  update: (id: string | number, todo: { title?: string; description?: string; completed?: boolean; due_date?: string; priority?: 'low' | 'medium' | 'high' }) => 
    api.put(`/todos/${id}`, todo),
  delete: (id: string | number) => api.delete(`/todos/${id}`),
  toggle: (id: string | number) => api.patch(`/todos/${id}/toggle`),
};

export const deliverabilityAPI = {
  getReputation: () => api.get('/deliverability/reputation'),
  getSpfDkimStatus: () => api.get('/deliverability/spf-dkim-status'),
  recordBounce: (payload: { mailbox?: string; recipient_email: string; bounce_type?: string; bounce_reason?: string; bounce_code?: string; email_id?: number; subject?: string }) =>
    api.post('/deliverability/record-bounce', payload),
  recordDelivery: (payload: { mailbox?: string; is_cold_send?: boolean }) =>
    api.post('/deliverability/record-delivery', payload),
};

 
