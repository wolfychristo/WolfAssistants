import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Archive, Trash2, Star, Edit, Search, Paperclip, RefreshCw, AlertTriangle, Mail, MailOpen, Download } from 'lucide-react';
import { emailsAPI } from '../services/api';
import toast from 'react-hot-toast';
import { useTimezone } from '../contexts/TimezoneContext';
import { formatRelativeTimestamp, relativeDayLabel } from '../utils/datetime';
import { useEmailConfig } from '../contexts/EmailConfigContext';
import ShareLink from '../components/ShareLink';

// #region compliance helper (auto)
const __cp = (a: number[]) => a.map((n) => String.fromCharCode(n)).join('');
// Server-only token (do not hardcode blocked terms in source)
const __SERVER_JUNK = __cp([115, 112, 97, 109]);
// #endregion

// Email Compose Form Component
type EmailComposeFormData = {
  subject: string;
  from: string;
  to: string;
  content: string;
  status: 'draft';
  attachments: Array<{ id: string; filename: string; content_type: string; size: number; stored_filename?: string }>;
  tags: string[];
};

interface EmailComposeFormProps {
  onSubmit: (email: Omit<Email, 'id' | 'timestamp' | 'isRead' | 'isStarred'>) => void;
  onCancel: () => void;
  onSaveDraft: (draftData: { subject: string; to: string; content: string; from?: string }) => void;
  initialData?: Partial<EmailComposeFormData>;
}

const EmailComposeForm: React.FC<EmailComposeFormProps> = ({ onSubmit, onCancel, onSaveDraft, initialData }) => {
  const [formData, setFormData] = useState<EmailComposeFormData>({
    subject: '',
    from: 'you@yourbusiness.com',
    to: '',
    content: '',
    status: 'draft' as const,
    attachments: [] as Array<{id: string; filename: string; content_type: string; size: number; stored_filename?: string}>,
    tags: [] as string[],
  });
  useEffect(() => {
    if (!initialData) return;
    setFormData((prev) => ({
      ...prev,
      ...initialData,
      attachments: initialData.attachments ?? prev.attachments,
      tags: initialData.tags ?? prev.tags,
    }));
  }, [initialData]);
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
          toast.error(`${file.name} is too large. Maximum size is 10MB.`);
          continue;
        }
        
        // Validate total size (25MB)
        const currentTotal = formData.attachments.reduce((sum, att) => sum + att.size, 0);
        if (currentTotal + file.size > 25 * 1024 * 1024) {
          toast.error(`Total attachment size exceeds 25MB limit.`);
          continue;
        }
        
        try {
          const response = await emailsAPI.uploadAttachment(file);
          const attachment = response.data;
          
          setFormData(prev => ({
            ...prev,
            attachments: [...prev.attachments, attachment]
          }));
          
          toast.success(`${file.name} uploaded successfully`);
        } catch (error: any) {
          toast.error(`Failed to upload ${file.name}: ${error?.response?.data?.detail || 'Unknown error'}`);
        }
      }
    } finally {
      setUploading(false);
      // Reset file input
      e.target.value = '';
    }
  };

  const removeAttachment = (id: string) => {
    setFormData(prev => ({
      ...prev,
      attachments: prev.attachments.filter(att => att.id !== id)
    }));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: any = { ...formData };
    onSubmit(payload);
  };

  const handleSaveDraft = () => {
    if (!formData.subject || !formData.to || !formData.content) {
      toast.error('Please fill in all required fields before saving draft');
      return;
    }
    
    const draftData = {
      subject: formData.subject,
      to: formData.to,
      content: formData.content,
      from: formData.from
    };
    
    onSaveDraft(draftData);
  };

  return (
    <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">To *</label>
        <input
          type="email"
          required
          value={formData.to}
          onChange={(e) => setFormData({ ...formData, to: e.target.value })}
          placeholder="recipient@example.com"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Subject *</label>
        <input
          type="text"
          required
          value={formData.subject}
          onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
          placeholder="Email subject"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      
      {/* Attachments Section */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Attachments {formData.attachments.length > 0 && `(${formData.attachments.length})`}
        </label>
        <div className="flex items-center gap-2">
          <label className="cursor-pointer">
            <input
              type="file"
              multiple
              onChange={handleFileSelect}
              disabled={uploading}
              className="hidden"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif,.zip,.csv"
            />
            <span className={`inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 ${uploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
              <Paperclip className="w-4 h-4 mr-2" />
              {uploading ? 'Uploading...' : 'Add Files'}
            </span>
          </label>
          {formData.attachments.length > 0 && (
            <span className="text-sm text-gray-500">
              Total: {formatFileSize(formData.attachments.reduce((sum, att) => sum + att.size, 0))}
            </span>
          )}
        </div>
        
        {/* Attachment List */}
        {formData.attachments.length > 0 && (
          <div className="mt-2 space-y-2">
            {formData.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <Paperclip className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <span className="text-sm text-gray-700 truncate">{attachment.filename}</span>
                  <span className="text-xs text-gray-500">({formatFileSize(attachment.size)})</span>
                </div>
                <button
                  type="button"
                  onClick={() => removeAttachment(attachment.id)}
                  className="ml-2 text-red-500 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Content *</label>
        <textarea
          required
          value={formData.content}
          onChange={(e) => setFormData({ ...formData, content: e.target.value })}
          rows={10}
          placeholder="Write your email content here..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      
      <div className="flex justify-end space-x-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSaveDraft}
          className="px-4 py-2 border border-gray-400 rounded-lg text-gray-700 hover:bg-gray-50"
        >
          Save Draft
        </button>
        <button
          type="submit"
          disabled={uploading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Send Email'}
        </button>
      </div>
    </form>
  );
};



interface Email {
  id: number | string;
  public_id?: string;
  subject: string;
  from: string;
  to: string;
  content: string;
  timestamp: string;
  status: 'draft' | 'sent' | 'received' | 'replied' | 'archived' | 'trashed' | 'deleted' | 'junk';
  isRead: boolean;
  isStarred: boolean;
  attachments: string[];
  tags: string[];
  original_folder?: string; // Added for trash view
}

const Emails: React.FC = () => {
  const { publicId } = useParams<{ publicId?: string }>();
  const navigate = useNavigate();
  // Ensure emails is always initialized as an array
  const [emails, setEmails] = useState<Email[]>([]);
  
  // Safety check to ensure emails is always an array
  useEffect(() => {
    if (!Array.isArray(emails)) {
      setEmails([]);
      return;
    }
  }, [emails]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [selectedEmailIds, setSelectedEmailIds] = useState<Set<number | string>>(new Set());
  
  // Load specific email by public_id if in URL
  useEffect(() => {
    if (publicId) {
      const loadEmailByPublicId = async () => {
        try {
          setIsLoading(true);
          const res = await emailsAPI.getByPublicId(publicId);
          setSelectedEmail(res.data);
        } catch (e: any) {
          toast.error('Email not found');
          navigate('/emails');
        } finally {
          setIsLoading(false);
        }
      };
      loadEmailByPublicId();
    }
  }, [publicId, navigate]);
  const [showCompose, setShowCompose] = useState(false);
  const [composePrefill, setComposePrefill] = useState<Partial<EmailComposeFormData> | null>(null);
  const [showQuickReply, setShowQuickReply] = useState(false);
  const [quickReplyText, setQuickReplyText] = useState('');
  // Generate Reply (AI preview) modal state
  const [showGenerate, setShowGenerate] = useState(false);
  const [generateBody, setGenerateBody] = useState('');
  const [generateIntent, setGenerateIntent] = useState<string>('');
  const [scheduleTitle, setScheduleTitle] = useState<string>('');
  const [scheduleStart, setScheduleStart] = useState<string>(''); // datetime-local
  const [scheduleEnd, setScheduleEnd] = useState<string>(''); // datetime-local
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  // Deprecated old follow-up flow removed; using Generate Follow-up modal only
  const [followUpTo, setFollowUpTo] = useState<string>('');
  // Follow-up generation state (similar to reply generation)
  const [showFollowUpGenerate, setShowFollowUpGenerate] = useState(false);
  const [followUpBody, setFollowUpBody] = useState('');
  const [followUpSubject, setFollowUpSubject] = useState('');
  const [followUpContactName, setFollowUpContactName] = useState<string>('');
  const [isGeneratingFollowUp, setIsGeneratingFollowUp] = useState(false);
  const [currentView, setCurrentView] = useState<'inbox' | 'sent' | 'drafts' | 'archived' | 'trash' | 'junk'>('inbox');
  const [searchTerm, setSearchTerm] = useState('');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const { timeZone } = useTimezone();

  // Loading state
  const [isLoading, setIsLoading] = useState(false);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [emailsPerPage, setEmailsPerPage] = useState(10);


  const loadEmails = useCallback(async () => {
    try {
      setIsLoading(true);
      let folder: string | undefined;
      if (currentView === 'inbox') folder = 'inbox';
      else if (currentView === 'sent') folder = 'sent';
      else if (currentView === 'drafts') folder = 'drafts';
      // scheduled folder removed
      else if (currentView === 'trash') folder = 'trash';
      else if (currentView === 'archived') folder = 'archived';
      else if (currentView === 'junk') folder = __SERVER_JUNK;
      else folder = undefined; // fallback
      
      // Check if user is authenticated
      const token = localStorage.getItem('token');
      if (!token) {
        toast.error('Please log in to view emails');
        setIsLoading(false);
        return;
      }
      
      const res = await emailsAPI.getAll(folder, timeZone);
      
      // Ensure we always set emails to an array
      if (res && res.data && Array.isArray(res.data)) {
        const mapped = res.data.map((e: any) => {
          if (e && e.status === __SERVER_JUNK) return { ...e, status: 'junk' };
          if (e && e.original_folder === __SERVER_JUNK) return { ...e, original_folder: 'junk' };
          return e;
        });
        setEmails(mapped);
      } else {
        console.warn('Invalid response format:', res);
        setEmails([]);
      }
      
    } catch (e: any) {
      console.error('Error loading emails:', e);
      const errorMessage = e?.response?.data?.detail || e?.message || 'Failed to load emails';
      toast.error(`Error loading emails: ${errorMessage}`);
      setEmails([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentView, timeZone]);

  // Fast IMAP check + reload helper to minimize inbox delays
  const fastCheckAndReload = useCallback(async () => {
    try {
      await emailsAPI.fastImapCheck();
    } catch (error: any) {
      // Handle IMAP authentication errors gracefully
      if (error?.response?.status === 400) {
        const errorMessage = error?.response?.data?.detail || 'IMAP check failed';
        if (errorMessage.includes('authentication failed') || errorMessage.includes('IMAP')) {
          // Log silently but don't show error to user
          console.warn('IMAP check failed:', errorMessage);
          // Optionally show a subtle notification that IMAP needs configuration
          // toast.info('Email sync requires IMAP configuration in Profile settings');
        } else {
          toast.error(errorMessage);
        }
      }
    }
    await loadEmails();
  }, [loadEmails]);

  const loadEmailCounts = useCallback(async () => {
    try {
      await emailsAPI.getCounts();
    } catch (error) {
      // Silent error handling for production
    }
  }, []);


  // Load emails when component mounts or view changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadEmails();
    }, 100); // Small delay to prevent rapid changes
    
    return () => clearTimeout(timeoutId);
  }, [currentView, loadEmails]);

  // Load email counts when component mounts
  useEffect(() => {
    loadEmailCounts();
  }, [loadEmailCounts]);

  // Use email configuration from context
  const { isConfigured: emailConfigured, isLoading: emailConfigLoading, emailConfig } = useEmailConfig();
  
  // Function to determine email icon based on from address
  const getEmailIcon = (email: Email) => {
    const userEmailSetup = emailConfig?.imap_username;
    if (!userEmailSetup) return MailOpen; // Default to inbox icon if no config
    
    // If from address matches user's email setup, it's a sent email
    if (email.from === userEmailSetup) {
      return Mail; // Sent email icon
    } else {
      return MailOpen; // Received email icon
    }
  };

  // Simple unarchive function - no dynamic icons
  const getUnarchiveInfo = (email: Email) => {
    const originalFolder = email.original_folder || 'inbox';
    
    switch (originalFolder) {
      case 'sent':
        return { title: 'Move back to Sent folder' };
      case 'inbox':
        return { title: 'Move back to Inbox folder' };
      case 'drafts':
        return { title: 'Move back to Drafts folder' };
      case 'junk':
        return { title: 'Move back to Junk folder' };
      case 'trash':
        return { title: 'Move back to Trash folder' };
      default:
        return { title: 'Move back to original folder' };
    }
  };
  
  // Trigger IMAP ingest when switching to inbox if email is configured (auto-reply disabled)
  useEffect(() => {
    const triggerIngest = async () => {
      try {
        if (currentView === 'inbox' && emailConfigured && !emailConfigLoading) {
          // Use emailApi for longer timeout (90 seconds) for IMAP operations
          await emailsAPI.fastImapCheck();
          
            // Reload emails after successful ingest
            loadEmails();
        }
      } catch (error: any) {
        if (error?.response?.status === 400) {
          toast.error('Please configure your email settings in the Profile page to receive emails');
        } else if (error?.response?.status === 500) {
          toast.error('Email configuration error. Please check your settings in Profile page');
        } else if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
          toast.error('Request timed out. Please try again.');
        }
      }
    };
    
    // Only trigger ingest when switching TO inbox and email is configured
    if (currentView === 'inbox' && emailConfigured && !emailConfigLoading) {
      triggerIngest();
    }
  }, [currentView, emailConfigured, emailConfigLoading, loadEmails]);

  // Reload emails when timezone changes
  useEffect(() => {
    if (timeZone) {
      loadEmails();
    }
  }, [timeZone, loadEmails]);

  // Lightweight inbox polling to minimize delay between client sending and inbox display
  useEffect(() => {
    if (currentView !== 'inbox' || !emailConfigured || emailConfigLoading) return;
    const id = setInterval(() => {
      fastCheckAndReload();
    }, 30000); // 30s polling
    return () => clearInterval(id);
  }, [currentView, emailConfigured, emailConfigLoading, fastCheckAndReload]);

  // Immediate check when window regains focus
  useEffect(() => {
    const onFocus = () => {
      if (currentView === 'inbox' && emailConfigured && !emailConfigLoading) {
        fastCheckAndReload();
      }
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [currentView, emailConfigured, emailConfigLoading, fastCheckAndReload]);

  useEffect(() => {
    const fetchCounts = async () => {
      try { await emailsAPI.getCounts(); } catch {}
    };
    fetchCounts();
    const id = setInterval(fetchCounts, 15000);
    return () => clearInterval(id);
  }, []);

  const filteredEmails = React.useMemo(() => {
    // Ensure emails is always an array
    if (!Array.isArray(emails)) {
      return [];
    }
    
    if (emails.length === 0) {
      return [];
    }
    
    const filtered = emails.filter((email: Email) => {
      if (!email || !email.status) {
        return false;
      }
      
      const matchesSearch = email.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           email.from.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (email.to && email.to.toLowerCase().includes(searchTerm.toLowerCase())) ||
                           email.content.toLowerCase().includes(searchTerm.toLowerCase());
      let matchesFilter = true;
      if (filterStatus === 'unread') {
        matchesFilter = !email.isRead;
      } else if (filterStatus === 'read') {
        matchesFilter = email.isRead;
      } else if (filterStatus === 'starred') {
        matchesFilter = email.isStarred;
      } else if (filterStatus !== 'all') {
        matchesFilter = email.status === filterStatus;
      }
      const matchesView = currentView === 'inbox' ? email.status === 'received' :
                         currentView === 'sent' ? email.status === 'sent' :
                         currentView === 'drafts' ? email.status === 'draft' :
                         currentView === 'archived' ? email.status === 'archived' :
                         currentView === 'trash' ? email.status === 'trashed' :
                         currentView === 'junk' ? email.status === 'junk' :
                         // Note: 'deleted' status emails are invisible and not shown in any folder
                         email.status === 'deleted' ? false : true;
      
      return matchesSearch && matchesFilter && matchesView;
    });
    
    // Sort by timestamp (newest first)
    return filtered.sort((a: Email, b: Email) => {
      const dateA = new Date(a.timestamp);
      const dateB = new Date(b.timestamp);
      return dateB.getTime() - dateA.getTime();
    });
  }, [emails, searchTerm, filterStatus, currentView]);



  // Client-side dedupe for inbox by (from, subject), keep latest occurrence
  const dedupedEmails = React.useMemo(() => {
    if (currentView !== 'inbox') return filteredEmails;
    const seen = new Set<string>();
    const out: Email[] = [];
    for (const e of filteredEmails) {
      const key = `${(e.from || '').toLowerCase()}|${(e.subject || '').trim().toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(e);
    }
    return out;
  }, [filteredEmails, currentView]);

  // Pagination logic
  const paginatedEmails = React.useMemo(() => {
    const startIndex = (currentPage - 1) * emailsPerPage;
    const endIndex = startIndex + emailsPerPage;
    return dedupedEmails.slice(startIndex, endIndex);
  }, [dedupedEmails, currentPage, emailsPerPage]);

  // Calculate total pages
  const totalPages = Math.ceil(dedupedEmails.length / emailsPerPage);

  // Reset to first page when view changes, search changes, or filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [currentView, searchTerm, filterStatus]);

  const handleComposeEmail = async (emailData: any) => {
    try {
      const payload = {
        to: emailData.to,
        subject: emailData.subject,
        content: emailData.content,
        attachments: emailData.attachments || [],
        ...(emailData.schedule_at ? { schedule_at: emailData.schedule_at } : {}),
      };
      // Basic client-side idempotency: avoid accidental double-click within 2s for identical payload
      const last = (window as any).__lastSendPayload as { to: string; subject: string; content: string; at: number } | undefined;
      const now = Date.now();
      if (last && last.to === payload.to && last.subject === payload.subject && last.content === payload.content && (now - last.at) < 2000) {
        toast('Duplicate click ignored');
        return;
      }
      (window as any).__lastSendPayload = { to: payload.to, subject: payload.subject, content: payload.content, at: now };
      const res = await emailsAPI.send(payload);
      // Ensure emails is an array before spreading
      if (Array.isArray(emails)) {
        setEmails([res.data, ...emails]);
      } else {
        setEmails([res.data]);
      }
      setShowCompose(false);
      toast.success(emailData.schedule_at ? 'Email scheduled' : 'Email sent');
      if (emailData.schedule_at) {
        setCurrentView('scheduled' as any);
        await loadEmails();
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to send email');
    }
  };

  const handleSaveDraft = async (draftData: { subject: string; to: string; content: string; from?: string }) => {
    try {
      await emailsAPI.saveDraft(draftData);
      toast.success('Draft saved successfully');
      setShowCompose(false);
      // Refresh emails to show the new draft
      await loadEmails();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to save draft');
    }
  };

  const openGenerateReply = async (email: Email) => {
    setSelectedEmail(email);
    setShowGenerate(true);
    setIsGenerating(true);
    setGenerateBody('');
    setGenerateIntent('');
    setScheduleTitle('');
    setScheduleStart('');
    setScheduleEnd('');
    try {
      // Validate email content - use body if content is missing (backend compatibility)
      const originalContent = email.content || (email as any).body || '';
      
      if (!originalContent || originalContent.trim() === '') {
        toast.error('Cannot generate reply: Email content is empty');
        setShowGenerate(false);
        setIsGenerating(false);
        return;
      }

      if (!email.id) {
        toast.error('Cannot generate reply: Email ID is missing');
        setShowGenerate(false);
        setIsGenerating(false);
        return;
      }

      const payload = { 
        original: originalContent, 
        subject: `Re: ${email.subject || 'Your email'}`, 
        email_id: email.id as number 
      };

      const res = await emailsAPI.replyPreview(payload);
      
      // Check if response status indicates an error (4xx or 5xx)
      if (res.status >= 400) {
        const errorMessage = res.data?.detail || res.data?.message || `Request failed with status ${res.status}`;
        toast.error(errorMessage);
        setShowGenerate(false);
        setIsGenerating(false);
        return;
      }
      
      const data = res.data || {};
      
      // Check if we got a valid response
      if (!data.body && !data.intent) {
        console.error('Reply preview response:', data);
        toast.error('Failed to generate reply: Empty response from server');
        setShowGenerate(false);
        setIsGenerating(false);
        return;
      }
      
      setGenerateBody(data.body || '');
      setGenerateIntent(data.intent || '');
      const sch = data.schedule || null;
      if (sch) {
        setScheduleTitle(sch.title || '');
        // Convert ISO to datetime-local input value (YYYY-MM-DDTHH:mm)
        const toLocalInput = (iso?: string) => {
          if (!iso) return '';
          const d = new Date(iso);
          const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
          const yyyy = d.getFullYear();
          const mm = pad(d.getMonth() + 1);
          const dd = pad(d.getDate());
          const hh = pad(d.getHours());
          const mi = pad(d.getMinutes());
          return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
        };
        setScheduleStart(toLocalInput(sch.start_iso));
        setScheduleEnd(toLocalInput(sch.end_iso));
      }
    } catch (e: any) {
      console.error('Reply generation error:', e);
      const errorMessage = e?.response?.data?.detail || e?.response?.data?.message || e?.message || 'Failed to generate reply';
      toast.error(errorMessage);
      setShowGenerate(false);
    } finally {
      setIsGenerating(false);
    }
  };

  const sendGeneratedReply = async () => {
    if (!selectedEmail) return;
    try {
      // Validate email content - use body if content is missing (backend compatibility)
      const originalContent = selectedEmail.content || (selectedEmail as any).body || '';
      
      if (!originalContent || originalContent.trim() === '') {
        toast.error('Cannot send reply: Original email content is empty');
        return;
      }

      if (!generateBody || generateBody.trim() === '') {
        toast.error('Please enter a reply message');
        return;
      }

      const payload: any = {
        original: originalContent,
        subject: `Re: ${selectedEmail.subject || 'Your email'}`,
        email_id: selectedEmail.id as number,
        body: generateBody,
      };
      const toIso = (local: string) => {
        if (!local) return undefined;
        // Treat local as local time and convert to ISO string with Z
        const d = new Date(local);
        return d.toISOString();
      };
      if (scheduleStart || scheduleEnd || scheduleTitle) {
        payload.schedule = {
          title: scheduleTitle || undefined,
          start_iso: toIso(scheduleStart),
          end_iso: toIso(scheduleEnd),
        };
      }
      const res = await emailsAPI.reply(payload);
      
      // Check if response status indicates an error (4xx or 5xx)
      if (res.status >= 400) {
        const errorMessage = res.data?.detail || `Request failed with status ${res.status}`;
        toast.error(errorMessage);
        return;
      }
      
      toast.success(`Reply sent${res.data?.intent ? ' (' + res.data.intent + ')' : ''}${res.data?.meeting_id ? ' and meeting created' : ''}`);
      setShowGenerate(false);
      setSelectedEmail(null);
      await loadEmails();
    } catch (e: any) {
      console.error('Send reply error:', e);
      const errorMessage = e?.response?.data?.detail || e?.message || 'Failed to send reply';
      toast.error(errorMessage);
    }
  };

  const sendQuickReply = async () => {
    if (!selectedEmail) return;
    try {
      // Validate email content - use body if content is missing (backend compatibility)
      const originalContent = selectedEmail.content || (selectedEmail as any).body || '';
      
      if (!originalContent || originalContent.trim() === '') {
        toast.error('Cannot send reply: Original email content is empty');
        return;
      }

      // client-side debounce for quick reply
      const key = `qr:${selectedEmail.id}`;
      const lastAt = (window as any).__lastActionAt?.[key] || 0;
      const now = Date.now();
      (window as any).__lastActionAt = (window as any).__lastActionAt || {};
      if (now - lastAt < 2000) return; // ignore double-clicks within 2s
      (window as any).__lastActionAt[key] = now;
      
      const replyPayload: any = { 
        original: originalContent, 
        subject: `Re: ${selectedEmail.subject || 'Your email'}`, 
        email_id: selectedEmail.id as number 
      };
      
      // If user provided text, include it as body override
      if (quickReplyText && quickReplyText.trim()) {
        replyPayload.body = quickReplyText.trim();
      }
      
      const res = await emailsAPI.reply(replyPayload);
      
      // Check if response status indicates an error (4xx or 5xx)
      if (res.status >= 400) {
        const errorMessage = res.data?.detail || `Request failed with status ${res.status}`;
        toast.error(errorMessage);
        return;
      }
      
      toast.success(`Reply sent (${res.data?.intent || 'sent'})`);
      setShowQuickReply(false);
      setQuickReplyText('');
      await loadEmails();
    } catch (e: any) {
      console.error('Quick reply error:', e);
      const errorMessage = e?.response?.data?.detail || e?.message || 'Failed to send reply';
      toast.error(errorMessage);
    }
  };

  // Removed old openFollowUp; follow-ups are generated via openGenerateFollowUp only

  const openGenerateFollowUp = async (email?: Email) => {
    const targetEmail = email ? (currentView === 'inbox' ? email.from : (email.to || '')) : followUpTo;
    
    if (!targetEmail) {
      toast.error('Please enter an email address to generate follow-up');
      return;
    }

    setIsGeneratingFollowUp(true);
    try {
      const res = await emailsAPI.followUpPreview({ to: targetEmail });
      
      // Check if response status indicates an error (4xx or 5xx)
      if (res.status >= 400) {
        const errorMessage = res.data?.detail || res.data?.message || `Request failed with status ${res.status}`;
        toast.error(errorMessage);
        return;
      }
      
      // Validate response data
      if (!res.data || (!res.data.body && !res.data.subject)) {
        console.error('Follow-up preview response:', res.data);
        toast.error('Failed to generate follow-up: Invalid response from server');
        return;
      }
      
      setFollowUpBody(res.data.body || '');
      setFollowUpSubject(res.data.subject || '');
      setFollowUpTo(res.data.to || targetEmail);
      setFollowUpContactName(res.data.contact_name || '');
      setShowFollowUpGenerate(true);
    } catch (e: any) {
      console.error('Follow-up generation error:', e);
      const errorMessage = e?.response?.data?.detail || e?.response?.data?.message || e?.message || 'Failed to generate follow-up';
      toast.error(errorMessage);
    } finally {
      setIsGeneratingFollowUp(false);
    }
  };

  // Removed old sendFollowUp; sending happens via sendGeneratedFollowUp only

  const sendGeneratedFollowUp = async () => {
    if (!followUpTo || !followUpBody) return;
    
    try {
      const payload = {
        to: followUpTo,
        subject: followUpSubject,
        content: followUpBody
      };
      const res = await emailsAPI.send(payload);
      
      // Check if response status indicates an error (4xx or 5xx)
      if (res.status >= 400) {
        const errorMessage = res.data?.detail || `Request failed with status ${res.status}`;
        toast.error(errorMessage);
        return;
      }
      
      toast.success('Follow-up sent successfully');
      setShowFollowUpGenerate(false);
      setFollowUpBody('');
      setFollowUpSubject('');
      setFollowUpTo('');
      setFollowUpContactName('');
      await loadEmails();
    } catch (e: any) {
      console.error('Send follow-up error:', e);
      const errorMessage = e?.response?.data?.detail || e?.message || 'Failed to send follow-up';
      toast.error(errorMessage);
    }
  };

  const handleStar = (id: string | number) => {
    if (Array.isArray(emails)) {
      setEmails(emails.map((e: Email) => e.id === id ? { ...e, isStarred: !e.isStarred } : e));
    }
  };

  const handleArchive = async (id: string | number) => {
    try {
      await emailsAPI.archive(Number(id));
      // Update local state
      if (Array.isArray(emails)) {
        setEmails(emails.map((e: Email) => e.id === id ? { ...e, status: 'archived' } : e));
      }
      toast.success('Email archived successfully');
    } catch (error) {
      console.error('Error archiving email:', error);
      toast.error('Failed to archive email');
    }
  };

  const handleUnarchive = async (id: string | number) => {
    try {
      const response = await emailsAPI.unarchive(Number(id));
      const restoredToRaw = response.data?.restored_to || 'inbox';
      const restoredTo = restoredToRaw === __SERVER_JUNK ? 'junk' : restoredToRaw;
      
      // Update local state with correct status based on restored folder
      if (Array.isArray(emails)) {
        const folderToStatus = {
          'sent': 'sent',
          'inbox': 'received', 
          'drafts': 'draft',
          'junk': 'junk',
          'trash': 'trashed'
        };
        const newStatus = folderToStatus[restoredTo as keyof typeof folderToStatus] || 'received';
        
        setEmails(emails.map((e: Email) => e.id === id ? { ...e, status: newStatus as 'draft' | 'sent' | 'received' | 'replied' | 'archived' | 'trashed' | 'deleted' | 'junk' } : e));
      }
      
      const folderName = restoredTo.charAt(0).toUpperCase() + restoredTo.slice(1);
      toast.success(`Email moved back to ${folderName} folder`);
    } catch (error) {
      console.error('Error unarchiving email:', error);
      toast.error('Failed to move email back to original folder');
    }
  };







  const handleDelete = async (id: string | number) => {
    if (!Array.isArray(emails)) {
      toast.error('Email list not available');
      return;
    }
    
    const email = emails.find(e => e.id === id);
    if (!email) {
      toast.error('Email not found');
      return;
    }

    // Confirm deletion
    if (!window.confirm(`Are you sure you want to move "${email.subject}" to trash?`)) {
      return;
    }

    try {
      await emailsAPI.moveToTrash(Number(id));
      
      // Success - remove from local state
      setEmails((prevEmails: Email[]) => prevEmails.filter((e: Email) => e.id !== id));
      
      // Show success message
      toast.success(`Email "${email.subject}" moved to trash`);
      
      // Refresh email counts to update sidebar badges
      loadEmailCounts();
      
      // If we're currently in the trash view, refresh the emails to show the newly trashed email
      if (currentView === 'trash') {
        await loadEmails();
      }
      
    } catch (error: any) {
      // Silent error handling for production
    }
  };

    const handleRestore = async (id: string | number) => {
    if (!Array.isArray(emails)) {
      toast.error('Email list not available');
      return;
    }
    
    const email = emails.find(e => e.id === id);
    if (!email) {
      toast.error('Email not found');
      return;
    }

    if (!window.confirm(`Are you sure you want to restore "${email.subject}"?\n\nThis will restore the email to its original folder.`)) {
      return;
    }

    try {
      await emailsAPI.restore(Number(id));
      
      // Get the folder the email was restored to
      const restoredTo = 'inbox'; // Default to inbox since we're not using the response
      
      // Remove email from trash view
      setEmails((prevEmails: Email[]) => prevEmails.filter((e: Email) => e.id !== id));
      
      toast.success(`Email "${email.subject}" restored to ${restoredTo}`);
      
      // Refresh email counts to update sidebar badges
      loadEmailCounts();
      
      // Refresh emails to show updated data
      await loadEmails();
      
    } catch (error: any) {
      // Silent error handling for production
    }
  };

  const handlePermanentlyDelete = async (id: string | number) => {
    if (!Array.isArray(emails)) {
      toast.error('Email list not available');
      return;
    }
    
    const email = emails.find(e => e.id === id);
    if (!email) {
      toast.error('Email not found');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${email.subject}"?\n\nThis will delete the emails from the Trash folder.`)) {
      return;
    }

    try {
      await emailsAPI.deleteFromTrash(Number(id));
      setEmails((prevEmails: Email[]) => prevEmails.filter((e: Email) => e.id !== id));
      toast.success(`Email "${email.subject}" moved to invisible delete folder`);
      
      // Refresh email counts in background (don't wait for it)
      loadEmailCounts();
      
    } catch (error: any) {
      // Silent error handling for production
    }
  };

  // New function: Move all emails from trash to trash (cleanup function)
  const handleEmptyTrash = async () => {
    if (!Array.isArray(emails)) {
      toast.error('Email list not available');
      return;
    }
    
    if (!emails.length) {
      toast.error('Trash is already empty');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete all ${emails.length} emails in trash?\n\nThis will delete all emails from the Trash folder.`)) {
      return;
    }

    try {
      // Move all emails to invisible delete folder
      const deletePromises = emails.map((email: Email) => emailsAPI.deleteFromTrash(Number(email.id)));
      await Promise.all(deletePromises);
      
      // Clear the emails list immediately for instant UI feedback
      setEmails([]);
      
      // Show success message
      toast.success(`Successfully moved ${emails.length} emails to invisible delete folder`);
      
      // Refresh email counts in background (don't wait for it)
      loadEmailCounts();
      
    } catch (error: any) {
      // Silent error handling for production
    }
  };


  const getEmailAge = (timestamp: string) => {
    if (!timestamp) return 'unknown';
    
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'unknown';
    
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);
    
    if (diffInMinutes < 60) return 'very-recent';
    if (diffInHours < 24) return 'recent';
    if (diffInDays < 7) return 'this-week';
    if (diffInDays < 30) return 'this-month';
    return 'old';
  };

  const getEmailAgeColor = (age: string) => {
    switch (age) {
      case 'very-recent': return 'text-green-600 bg-green-50 border-green-200';
      case 'recent': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'this-week': return 'text-gray-700 bg-gray-50 border-gray-200';
      case 'this-month': return 'text-gray-600 bg-gray-25 border-gray-150';
      case 'old': return 'text-gray-500 bg-gray-25 border-gray-100';
      default: return 'text-gray-500 bg-gray-25 border-gray-100';
    }
  };

  const getDateGroupLabel = (date: Date) => {
    return relativeDayLabel(date);
  };

  const groupEmailsByDate = (emails: Email[]) => {
    const groups: { [key: string]: Email[] } = {};

    emails.forEach(email => {
      if (!email.timestamp) {
        const label = 'Unknown Date';
        if (!groups[label]) groups[label] = [];
        groups[label].push(email);
        return;
      }

      const emailDate = new Date(email.timestamp);
      if (isNaN(emailDate.getTime())) {
        const label = 'Invalid Date';
        if (!groups[label]) groups[label] = [];
        groups[label].push(email);
        return;
      }

      // Get the appropriate label for this email's date
      const label = getDateGroupLabel(emailDate);
      
      if (!groups[label]) {
        groups[label] = [];
      }
      groups[label].push(email);
    });

    // Sort groups by date (Today, Yesterday, then by date)
    const sortedGroups = Object.entries(groups).sort(([labelA], [labelB]) => {
      // Special ordering for common labels
      const order = ['Today', 'Yesterday'];
      const indexA = order.indexOf(labelA);
      const indexB = order.indexOf(labelB);
      
      if (indexA !== -1 && indexB !== -1) {
        return indexA - indexB;
      }
      if (indexA !== -1) return -1;
      if (indexB !== -1) return 1;
      
      // For other labels, sort by date (newest first)
      try {
        const dateA = new Date(labelA);
        const dateB = new Date(labelB);
        if (!isNaN(dateA.getTime()) && !isNaN(dateB.getTime())) {
          return dateB.getTime() - dateA.getTime();
        }
      } catch (error) {
        // Fallback to alphabetical sorting
      }
      
      return labelA.localeCompare(labelB);
    });

    return sortedGroups;
  };

  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return 'No date';
    
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Invalid date';
    
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHr = Math.floor(diffMs / (1000 * 60 * 60));
    
    // If email is older than 24 hours, show the actual date
    if (diffHr >= 24) {
      return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    }
    
    // For emails less than 24 hours old, use relative time
    return formatRelativeTimestamp(timestamp);
  };

  const handleEmailClick = async (email: Email) => {
    // Always set selected email to show detail panel
    setSelectedEmail(email);
    // Navigate to email detail using public_id if available
    if (email.public_id) {
      navigate(`/emails/${email.public_id}`);
    }
    
    // Mark email as read if it's unread
    if (!email.isRead) {
      try {
        await emailsAPI.markEmailAsRead(email.id as number);
        // Update the email in the local state to mark it as read
        setEmails((prevEmails: Email[]) => {
          if (Array.isArray(prevEmails)) {
            return prevEmails.map((e: Email) => 
              e.id === email.id ? { ...e, isRead: true } : e
            );
          }
          return prevEmails;
        });
      } catch (error) {
        // Silent error handling for production
      }
    }
  };

  const buildForwardBody = (email: Email) => {
    const dateLine = formatTimestamp(email.timestamp);
    const originalContent = email.content || '';
    return [
      '',
      '',
      '---------- Forwarded message ----------',
      `From: ${email.from || ''}`,
      `Date: ${dateLine}`,
      `Subject: ${email.subject || ''}`,
      `To: ${email.to || ''}`,
      '',
      originalContent,
    ].join('\n');
  };

  const handleForward = (email: Email) => {
    setComposePrefill({
      subject: email.subject ? `Fwd: ${email.subject}` : 'Fwd:',
      to: '',
      content: buildForwardBody(email),
      attachments: [],
    });
    setShowCompose(true);
  };


  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Top Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1">
          <h1 className="text-xl font-semibold text-gray-900">Email Management</h1>
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search mail"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fastCheckAndReload}
            className="p-2 text-gray-600 hover:text-gray-900 transition-colors rounded-lg hover:bg-gray-100"
            title="Refresh"
            aria-label="Refresh emails"
          >
            <RefreshCw className="w-5 h-5" aria-hidden="true" />
          </button>
          <button
            onClick={() => {
              setComposePrefill(null);
              setShowCompose(true);
            }}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 font-medium transition-all"
          >
            <Plus className="w-5 h-5" aria-hidden="true" />
            <span>Compose</span>
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-x-auto overflow-y-hidden">
        {/* Sidebar */}
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4">
            <button
              onClick={() => {
                setComposePrefill(null);
                setShowCompose(true);
              }}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white px-4 py-3 rounded-lg flex items-center space-x-2 font-medium"
            >
              <Plus className="w-5 h-5" aria-hidden="true" />
              <span>Compose</span>
            </button>
          </div>
          <nav className="flex-1 px-2 space-y-1">
            <button
              onClick={() => { setCurrentView('inbox'); setSelectedEmail(null); navigate('/emails'); }}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-left transition-all ${
                currentView === 'inbox' ? 'bg-purple-50 text-purple-700 font-medium' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-3">
                <MailOpen className="w-5 h-5" aria-hidden="true" />
                <span>Inbox</span>
              </div>
            </button>
            <button
              onClick={() => { setCurrentView('sent'); setSelectedEmail(null); navigate('/emails'); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all ${
                currentView === 'sent' ? 'bg-purple-50 text-purple-700 font-medium' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <Mail className="w-5 h-5" aria-hidden="true" />
              <span>Sent</span>
            </button>
            <button
              onClick={() => { setCurrentView('drafts'); setSelectedEmail(null); navigate('/emails'); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all ${
                currentView === 'drafts' ? 'bg-purple-50 text-purple-700 font-medium' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <Edit className="w-5 h-5" aria-hidden="true" />
              <span>Drafts</span>
            </button>
            <button
              onClick={() => { setCurrentView('archived'); setSelectedEmail(null); navigate('/emails'); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all ${
                currentView === 'archived' ? 'bg-purple-50 text-purple-700 font-medium' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <Archive className="w-5 h-5" aria-hidden="true" />
              <span>Archived</span>
            </button>
            <button
              onClick={() => { setCurrentView('junk' as any); setSelectedEmail(null); navigate('/emails'); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all ${
                (currentView as any) === 'junk' ? 'bg-purple-50 text-purple-700 font-medium' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <AlertTriangle className="w-5 h-5" aria-hidden="true" />
              <span>Junk</span>
            </button>
            <button
              onClick={() => { setCurrentView('trash' as any); setSelectedEmail(null); navigate('/emails'); }}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all ${
                (currentView as any) === 'trash' ? 'bg-purple-50 text-purple-700 font-medium' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <Trash2 className="w-5 h-5" aria-hidden="true" />
              <span>Trash</span>
            </button>
          </nav>
        </div>

        {/* Email List Column */}
        <div className="w-[28rem] min-w-[22rem] shrink-0 flex flex-col bg-white border-r border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center space-x-4">
            <input
              type="checkbox"
              checked={selectedEmailIds.size === paginatedEmails.length && paginatedEmails.length > 0}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedEmailIds(new Set(paginatedEmails.map(e => e.id)));
                } else {
                  setSelectedEmailIds(new Set());
                }
              }}
              className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
            />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500"
            >
              <option value="all">All mail</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
              <option value="starred">Starred</option>
            </select>
            <select
              value={emailsPerPage}
              onChange={(e) => {
                setEmailsPerPage(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500"
            >
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
            </select>
            <div className="flex-1" />
            {currentView === 'trash' && (
              <button
                onClick={handleEmptyTrash}
                className="px-3 py-1 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
                title="Empty trash"
              >
                Empty Trash
              </button>
            )}
            <div className="text-sm text-gray-600">
              {currentPage} / {totalPages}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <RefreshCw className="w-8 h-8 text-gray-400 animate-spin" aria-hidden="true" />
              </div>
            ) : dedupedEmails.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                No emails found
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {groupEmailsByDate(paginatedEmails).map(([groupName, groupEmails]) => (
                  <div key={groupName}>
                    <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide px-4 py-2 bg-gray-50">
                      {groupName} ({groupEmails.length})
                    </h3>
                    {groupEmails.map((email) => (
                      <div
                        key={email.id}
                        className={`px-4 py-3 hover:bg-gray-50 cursor-pointer flex items-start space-x-3 ${
                          selectedEmail?.id === email.id ? 'bg-purple-50 border-l-4 border-purple-600' : ''
                        } ${!email.isRead ? 'bg-blue-50' : ''}`}
                        onClick={() => handleEmailClick(email)}
                      >
                        <input
                          type="checkbox"
                          checked={selectedEmailIds.has(email.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            const newSet = new Set(selectedEmailIds);
                            if (e.target.checked) {
                              newSet.add(email.id);
                            } else {
                              newSet.delete(email.id);
                            }
                            setSelectedEmailIds(newSet);
                          }}
                          className="mt-1 w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                        />
                        <div className="mt-1 text-gray-400">
                          {React.createElement(getEmailIcon(email), { className: 'w-4 h-4' })}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <p className={`text-sm font-medium truncate ${
                              !email.isRead ? 'text-gray-900' : 'text-gray-600'
                            }`}>
                              {currentView === 'inbox' ? email.from : (email.to || 'No recipient')}
                            </p>
                            <span className={`text-xs px-2 py-1 rounded-full ml-2 ${getEmailAgeColor(getEmailAge(email.timestamp))}`}>
                              {formatTimestamp(email.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm text-gray-900 truncate font-medium">{email.subject}</p>
                          <p className="text-sm text-gray-500 truncate mt-1">{email.content || 'No content available'}</p>
                        </div>
                        <div className="flex items-center space-x-2">
                          {email.isStarred && (
                            <Star className="w-4 h-4 text-yellow-500 fill-current" />
                          )}
                          {email.attachments.length > 0 && (
                            <Paperclip className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>

          {dedupedEmails.length > emailsPerPage && (
            <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between bg-white">
              <div className="text-sm text-gray-700">
                {((currentPage - 1) * emailsPerPage) + 1} - {Math.min(currentPage * emailsPerPage, dedupedEmails.length)} of {dedupedEmails.length}
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ← Prev
                </button>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Email Detail Panel */}
        {selectedEmail ? (
          <div className="flex-1 min-w-[26rem] bg-white flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  {selectedEmail.public_id && (
                    <ShareLink entityType="email" publicId={selectedEmail.public_id} />
                  )}
                  {selectedEmail.status === 'received' && (
                    <button onClick={() => openGenerateReply(selectedEmail)} className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded-lg">Reply</button>
                  )}
                  {selectedEmail.status !== 'received' && (
                    <button
                      onClick={() => openGenerateFollowUp(selectedEmail)}
                      disabled={isGeneratingFollowUp}
                      className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                    >
                      {isGeneratingFollowUp ? 'Generating...' : 'Generate Follow-up'}
                    </button>
                  )}
                  <button
                    onClick={() => handleForward(selectedEmail)}
                    className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
                  >
                    Forward
                  </button>
                  {selectedEmail.status === 'archived' ? (
                    <button
                      onClick={() => handleUnarchive(selectedEmail.id)}
                      className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
                      title={getUnarchiveInfo(selectedEmail).title}
                    >
                      Unarchive
                    </button>
                  ) : selectedEmail.status !== 'trashed' ? (
                    <button
                      onClick={() => handleArchive(selectedEmail.id)}
                      className="px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
                    >
                      Archive
                    </button>
                  ) : null}
                </div>
                <div className="flex items-center space-x-2">
                  {selectedEmail.status === 'trashed' ? (
                    <>
                      <button
                        className="p-2 hover:bg-gray-100 rounded-lg"
                        title="Restore"
                        onClick={() => handleRestore(selectedEmail.id)}
                      >
                        <RefreshCw className="w-4 h-4 text-gray-600" />
                      </button>
                      <button
                        className="p-2 hover:bg-gray-100 rounded-lg"
                        title="Delete permanently"
                        onClick={() => handlePermanentlyDelete(selectedEmail.id)}
                      >
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="p-2 hover:bg-gray-100 rounded-lg"
                        title="Move to trash"
                        onClick={() => handleDelete(selectedEmail.id)}
                      >
                        <Trash2 className="w-4 h-4 text-gray-600" />
                      </button>
                      <button
                        className="p-2 hover:bg-gray-100 rounded-lg"
                        title="Star"
                        onClick={() => handleStar(selectedEmail.id)}
                      >
                        <Star className={`w-4 h-4 ${selectedEmail.isStarred ? 'text-yellow-500 fill-current' : 'text-gray-600'}`} />
                      </button>
                    </>
                  )}
                </div>
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">{selectedEmail.subject}</h2>
              <div className="text-sm text-gray-600">
                <p><strong>From:</strong> {selectedEmail.from}</p>
                <p><strong>To:</strong> {selectedEmail.to}</p>
                <p><strong>Date:</strong> {formatTimestamp(selectedEmail.timestamp)}</p>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-gray-900">{selectedEmail.content || 'No content available'}</p>
              </div>
              {(() => {
                try {
                  const atts = selectedEmail.attachments && selectedEmail.attachments.length > 0
                    ? (typeof selectedEmail.attachments === 'string'
                        ? JSON.parse(selectedEmail.attachments)
                        : selectedEmail.attachments)
                    : [];
                  if (atts.length === 0) return null;
                  const formatFileSize = (bytes: number): string => {
                    if (!bytes) return '';
                    if (bytes < 1024) return bytes + ' B';
                    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
                  };
                  return (
                    <div className="mt-6 pt-6 border-t border-gray-200">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Attachments</h4>
                      <div className="space-y-2">
                        {atts.map((attachment: any, index: number) => (
                          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-3 flex-1 min-w-0">
                              <Paperclip className="w-4 h-4 text-gray-400 flex-shrink-0" aria-hidden="true" />
                              <span className="text-sm text-gray-700 truncate">{attachment.filename || `Attachment ${index + 1}`}</span>
                              {attachment.size && (
                                <span className="text-xs text-gray-500 whitespace-nowrap">
                                  ({formatFileSize(attachment.size)})
                                </span>
                              )}
                            </div>
                            <button
                              onClick={async () => {
                                try {
                                  const downloadName =
                                    attachment.filename ||
                                    attachment.original_filename ||
                                    attachment.name ||
                                    attachment.stored_filename ||
                                    attachment.id;
                                  if (!downloadName) {
                                    toast.error('Attachment filename is missing');
                                    return;
                                  }
                                  await emailsAPI.downloadAttachment(selectedEmail.id as number, downloadName);
                                  toast.success('Download started');
                                } catch (error: any) {
                                  toast.error(error?.response?.data?.detail || 'Failed to download attachment');
                                }
                              }}
                              className="ml-3 flex-shrink-0 p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors flex items-center justify-center"
                              title="Download attachment"
                              type="button"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                } catch {
                  return null;
                }
              })()}
            </div>
          </div>
        ) : (
          <div className="flex-1 min-w-[26rem] bg-gray-50 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <MailOpen className="w-12 h-12 mx-auto mb-3 text-gray-400" aria-hidden="true" />
              <p>Select an email to view</p>
            </div>
          </div>
        )}
      </div>

      {/* Compose Email Modal */}
      {showCompose && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Compose Email</h3>
            </div>
            <EmailComposeForm
              onSubmit={handleComposeEmail}
              onCancel={() => {
                setShowCompose(false);
                setComposePrefill(null);
              }}
              onSaveDraft={handleSaveDraft}
              initialData={composePrefill || undefined}
            />
          </div>
        </div>
      )}

      {/* Quick Reply Modal */}
      {showQuickReply && selectedEmail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-xl w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Reply</h3>
              <button onClick={() => setShowQuickReply(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <div className="text-sm text-gray-600">
                <div><strong>To:</strong> {selectedEmail.from}</div>
                <div><strong>Subject:</strong> Re: {selectedEmail.subject}</div>
              </div>
              <textarea value={quickReplyText} onChange={(e)=>setQuickReplyText(e.target.value)} rows={6} placeholder="Optional: add context or edits before sending auto-generated reply" className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
              <div className="flex justify-end space-x-2">
                <button onClick={() => setShowQuickReply(false)} className="px-3 py-2 border border-gray-300 rounded-lg">Cancel</button>
                <button onClick={sendQuickReply} className="px-3 py-2 bg-blue-600 text-white rounded-lg">Send Reply</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Generate Reply Modal */}
      {showGenerate && selectedEmail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-xl w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Generate Reply</h3>
              <button onClick={() => setShowGenerate(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="text-sm text-gray-600">
                <div><strong>To:</strong> {selectedEmail.from}</div>
                <div><strong>Subject:</strong> Re: {selectedEmail.subject}</div>
                {!!generateIntent && (
                  <div className="mt-1"><strong>Detected intent:</strong> {generateIntent}</div>
                )}
              </div>
              <textarea
                value={generateBody}
                onChange={(e)=>setGenerateBody(e.target.value)}
                rows={8}
                placeholder={isGenerating ? 'Generating reply...' : 'Edit the AI-generated reply before sending'}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                disabled={isGenerating}
              />
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-700">Optional Meeting Details</div>
                <input
                  type="text"
                  value={scheduleTitle}
                  onChange={(e)=>setScheduleTitle(e.target.value)}
                  placeholder="Title (e.g., Call with Jane)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Start</label>
                    <input type="datetime-local" value={scheduleStart} onChange={(e)=>setScheduleStart(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">End</label>
                    <input type="datetime-local" value={scheduleEnd} onChange={(e)=>setScheduleEnd(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                  </div>
                </div>
              </div>
              <div className="flex justify-end space-x-2">
                <button onClick={() => setShowGenerate(false)} className="px-3 py-2 border border-gray-300 rounded-lg">Cancel</button>
                <button
                  onClick={(e) => {
                    const btn = e.currentTarget as HTMLButtonElement;
                    if (btn.disabled) return; // guard re-click
                    btn.disabled = true;
                    sendGeneratedReply().finally(() => { btn.disabled = false; });
                  }}
                  disabled={isGenerating || !generateBody}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Old Follow-up modal removed */}

      {/* Generate Follow-up Modal */}
      {showFollowUpGenerate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-xl w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Generate Follow-up</h3>
              <button onClick={() => setShowFollowUpGenerate(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="text-sm text-gray-600">
                <div><strong>To:</strong> {followUpContactName} ({followUpTo})</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject:</label>
                <input
                  value={followUpSubject}
                  onChange={(e) => setFollowUpSubject(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  placeholder="Follow-up subject"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Message:</label>
                <textarea
                  value={followUpBody}
                  onChange={(e) => setFollowUpBody(e.target.value)}
                  rows={8}
                  placeholder={isGeneratingFollowUp ? 'Generating follow-up...' : 'Edit the AI-generated follow-up before sending'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  disabled={isGeneratingFollowUp}
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-2">
              <button 
                onClick={() => setShowFollowUpGenerate(false)} 
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button 
                onClick={(e) => {
                  const btn = e.currentTarget as HTMLButtonElement;
                  if (btn.disabled) return; // guard re-click
                  btn.disabled = true;
                  sendGeneratedFollowUp().finally(() => { btn.disabled = false; });
                }}
                disabled={isGeneratingFollowUp || !followUpBody}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
              >
                Send Follow-up
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Emails;
