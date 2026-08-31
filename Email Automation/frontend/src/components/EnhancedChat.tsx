import React, { useState, useEffect, useRef, useCallback } from 'react';
import { wolfyAPI, chatSessionsAPI, cleanupCorruptedSessionIds } from '../services/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Send, Loader2, MessageSquare, X } from 'lucide-react';
import { ChatSessions } from './ChatSessions';
import { useAuth } from '../contexts/AuthContext';

interface ChatMessage {
  id: number;
  public_id?: string;
  role: 'user' | 'wolfy';
  content: string;
  intent?: string;
  status?: string;
  message_metadata?: any;
  created_at: string;
}

interface ChatSession {
  id: number;
  public_id?: string;
  title: string;
  contact_name?: string;
  contact_email?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  last_message_at?: string;
  message_count?: number;
}

interface EnhancedChatProps {
  mode?: 'widget' | 'fullpage';
  onClose?: () => void;
  selectedSessionId?: number;
}

export const EnhancedChat: React.FC<EnhancedChatProps> = ({ 
  mode = 'fullpage', 
  onClose,
  selectedSessionId,
}) => {
  const { user, isLoading: authLoading } = useAuth();
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSession = useCallback(async (session: ChatSession) => {
    try {
      // Set loading state to prevent message sending during session switch
      setIsLoading(true);
      
      // Clear current state first to prevent mixing conversations
      setMessages([]);
      setCurrentSession(null);
      
      const response = await chatSessionsAPI.getById(session.id);
      const sessionData = response.data;
      setCurrentSession(sessionData);
      setMessages(sessionData.messages || []);
      
      // Store this session as the last active one
      if (user?.email) {
        localStorage.setItem(`wolfy_last_session_${user.email}`, session.id.toString());
      }
    } catch (error: any) {
      if (error?.response?.status === 401) {
        return;
      }
      // Don't log 404 errors as they're expected when sessions are deleted
      if (error?.response?.status !== 404) {
        console.error('Failed to load session:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [user?.email]);

  const loadActiveSession = useCallback(async () => {
    try {
      // First, try to restore the last active session from localStorage
      const lastSessionIdRaw = localStorage.getItem(`wolfy_last_session_${user?.email}`);
      if (lastSessionIdRaw) {
        // Sanitize and validate the session ID
        // Remove any non-numeric characters (handles cases like "3:1" -> "3")
        const sanitizedId = lastSessionIdRaw.trim().split(':')[0].split('/')[0].split('?')[0].split('#')[0];
        const sessionId = parseInt(sanitizedId, 10);
        
        // Validate that we got a valid number
        if (isNaN(sessionId) || sessionId <= 0 || !Number.isInteger(sessionId)) {
          // Invalid session ID, remove it from localStorage
          console.warn('Invalid session ID in localStorage, removing:', lastSessionIdRaw);
          localStorage.removeItem(`wolfy_last_session_${user?.email}`);
        } else {
          try {
            const response = await chatSessionsAPI.getById(sessionId);
            const sessionData = response.data;
            setCurrentSession(sessionData);
            setMessages(sessionData.messages || []);
            // Update localStorage with the clean session ID if it was corrupted
            if (lastSessionIdRaw !== sessionId.toString()) {
              localStorage.setItem(`wolfy_last_session_${user?.email}`, sessionId.toString());
            }
            return;
          } catch (error: any) {
            // If the session doesn't exist anymore (404), silently remove it from localStorage
            // Don't log 404 errors as they're expected when sessions are deleted
            if (error?.response?.status === 404) {
              localStorage.removeItem(`wolfy_last_session_${user?.email}`);
            } else {
              // Log other errors (network, auth, etc.)
              console.error('Failed to load session from localStorage:', error);
              localStorage.removeItem(`wolfy_last_session_${user?.email}`);
            }
          }
        }
      }

      // Fallback: load the most recent session (include inactive to find the most recent one)
      const response = await chatSessionsAPI.getAll({ limit: 1, include_inactive: true });
      const sessions = response.data.sessions || [];
      if (sessions.length > 0) {
        const activeSession = sessions.find((s: ChatSession) => s.is_active) || sessions[0];
        await loadSession(activeSession);
        // Store this session as the last active one
        localStorage.setItem(`wolfy_last_session_${user?.email}`, activeSession.id.toString());
      }
    } catch (error: any) {
      // Handle authentication errors gracefully
      if (error?.response?.status === 401) {
        // Don't show error for auth issues, just start fresh
        return;
      }
      console.error('Failed to load active session:', error);
    }
  }, [user?.email, loadSession]);

  useEffect(() => {
    // Clean up any corrupted session IDs in localStorage when user changes
    if (user?.email) {
      cleanupCorruptedSessionIds(user.email);
    }
  }, [user?.email]);

  useEffect(() => {
    // Only load sessions if user is authenticated and not loading
    if (user && !authLoading) {
      if (selectedSessionId) {
        // Set loading state to prevent message sending during session switch
        setIsLoading(true);
        
        // Clear current messages first to prevent mixing conversations
        setMessages([]);
        setCurrentSession(null);
        
        // Load the selected session explicitly
        chatSessionsAPI.getById(selectedSessionId)
          .then((res) => {
            setCurrentSession(res.data);
            setMessages(res.data.messages || []);
          })
          .catch((err: any) => {
            // Don't log 404 errors as they're expected when sessions are deleted
            if (err?.response?.status !== 404) {
              console.error('Failed to load selected session:', err);
            }
          })
          .finally(() => setIsLoading(false));
      } else {
        loadActiveSession();
      }
    } else if (!user) {
      // Clear session data when user logs out
      setCurrentSession(null);
      setMessages([]);
    }
  }, [user, authLoading, selectedSessionId, loadActiveSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !user) return;

    const message = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await wolfyAPI.chat({
        message,
        session_id: currentSession?.id,
        contact_name: currentSession?.contact_name,
        contact_email: currentSession?.contact_email,
      });

      const responseData = response.data;
      
      // If this is a new session, update our current session
      if (responseData.is_new_session) {
        setCurrentSession(prev => {
          const newSession = {
            ...prev!,
            id: responseData.session_id,
            title: responseData.session_title || prev!.title,
          };
          
          // Store this new session as the last active one
          if (user?.email) {
            localStorage.setItem(`wolfy_last_session_${user.email}`, responseData.session_id.toString());
          }
          
          return newSession;
        });
      } else if (responseData.session_title && currentSession) {
        // Update title if it was auto-generated from the first message
        if (responseData.session_title !== currentSession.title) {
          setCurrentSession(prev => prev ? { ...prev, title: responseData.session_title } : prev);
        }
      }

      // Normalize backend response to ChatMessage shape
      const raw = responseData?.message;
      let wolfyMessage: ChatMessage;
      if (raw && typeof raw === 'object' && 'content' in raw) {
        const createdAt = (raw as any).created_at || new Date().toISOString();
        wolfyMessage = { ...(raw as any), created_at: createdAt } as ChatMessage;
      } else {
        const content: string = typeof raw === 'string'
          ? raw
          : (responseData?.text || responseData?.message?.message || '');
        const intent: string | undefined = responseData?.intent || responseData?.message?.intent;
        const status: string | undefined = responseData?.status || responseData?.message?.status;
        const message_metadata: any = responseData?.result || responseData?.message?.message_metadata;
        wolfyMessage = {
          id: Date.now() + 1,
          role: 'wolfy',
          content: content || 'Okay.',
          intent,
          status,
          message_metadata,
          created_at: new Date().toISOString(),
        };
      }
      setMessages(prev => [...prev, wolfyMessage]);
    } catch (error: any) {
      // Handle timeout specifically with a clearer user message
      if (error?.code === 'ECONNABORTED') {
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'wolfy',
          content: 'Wolfy is taking longer than expected. I will keep trying, or you can retry in a moment.',
          created_at: new Date().toISOString(),
        }]);
        console.warn('Chat request timed out');
        return;
      }

      console.error('Failed to send message:', error);
      
      // Handle authentication errors
      if (error?.response?.status === 401) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'wolfy',
          content: 'Please log in to use Wolfy. You can access the login page from the navigation menu.',
          created_at: new Date().toISOString(),
        }]);
      } else {
        // Add generic error message
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'wolfy',
          content: 'Sorry, I encountered an error. Please try again.',
          created_at: new Date().toISOString(),
        }]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleNewSession = async () => {
    try {
      // Create a new session without prompting - backend will auto-generate title
      const response = await chatSessionsAPI.create({
        // No title provided - backend will generate "New Chat {datetime}"
      });
      const newSession = response.data;
      
      // Set as current session and load it
      setCurrentSession(newSession);
      setMessages([]);
      setShowSessions(false);
    } catch (error) {
      console.error('Failed to create new session:', error);
      alert('Failed to create new chat session. Please try again.');
      // Fallback to just clearing current session
      setCurrentSession(null);
      setMessages([]);
      setShowSessions(true);
    }
  };

  const handleSelectSession = (session: ChatSession) => {
    loadSession(session);
    setShowSessions(false);
  };

  // Removed relative time display per request

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user';
    
    return (
      <div
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div
          className={`max-w-[80%] break-words ${
            isUser
              ? 'bg-blue-600 text-white rounded-lg rounded-br-sm px-4 py-2'
              : 'bg-gray-800 text-gray-100 rounded-lg rounded-bl-sm px-4 py-2 border border-gray-700'
          }`}
        >
          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          {/* Timestamp removed per request */}
          
          {/* Show metadata for Wolfy's responses with results */}
          {!isUser && message.message_metadata && (
            <div className="mt-2 p-2 bg-gray-700 bg-opacity-50 rounded text-xs border border-gray-600">
              <div className="font-medium text-gray-300">Action completed:</div>
              <div className="text-xs text-gray-400 mt-1">
                {JSON.stringify(message.message_metadata, null, 2)}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  if (showSessions) {
    return (
      <div className={`${mode === 'widget' ? 'w-80 h-96' : 'h-full'} flex flex-col bg-gray-900`}>
        <div className="p-4 border-b border-gray-700 flex items-center justify-between bg-gray-800">
          <h3 className="font-semibold text-white">Select Chat Session</h3>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowSessions(false)}
            className="text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-hidden">
          <ChatSessions
            onSelectSession={handleSelectSession}
            onNewSession={handleNewSession}
            currentSessionId={currentSession?.id}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`${mode === 'widget' ? 'w-80 h-96' : 'h-full'} flex flex-col bg-gray-900`}>
      {/* Header - Only show in widget mode */}
      {mode === 'widget' && (
        <div className="p-4 border-b border-gray-700 flex items-center justify-between bg-gray-800">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-blue-400" />
            <div>
              <h3 className="font-semibold text-white">
                {currentSession?.title || 'New Chat'}
              </h3>
              {currentSession?.contact_name && (
                <p className="text-xs text-gray-400">
                  with {currentSession.contact_name}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleNewSession}
              className="text-gray-400 hover:text-white"
            >
              New Chat
            </Button>
            {onClose && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onClose}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {authLoading ? (
              <div className="text-center text-gray-400 py-8">
                <Loader2 className="w-12 h-12 mx-auto mb-4 text-gray-600 animate-spin" />
                <p className="text-white">Loading Wolfy...</p>
                <p className="text-sm text-gray-400">Please wait while we initialize your chat.</p>
              </div>
            ) : !user ? (
              <div className="text-center text-gray-400 py-8">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                <p className="text-white">Please log in to use Wolfy</p>
                <p className="text-sm text-gray-400">You need to be authenticated to start a conversation with Wolfy.</p>
              </div>
            ) : messages.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-600" />
            <p className="text-white">Start a conversation with Wolfy</p>
            <p className="text-sm text-gray-400">Ask me to send emails, schedule meetings, or help with your business tasks.</p>
          </div>
        ) : (
          messages.map(renderMessage)
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg rounded-bl-sm px-4 py-2 flex items-center gap-2 border border-gray-700">
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-sm text-gray-300">Wolfy is thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-700 bg-gray-800">
        <div className="flex gap-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={authLoading ? "Loading..." : user ? "Type your message..." : "Please log in to use Wolfy"}
                disabled={isLoading || !user || authLoading}
                className="flex-1 bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:border-gray-500"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading || !user || authLoading}
                size="sm"
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};
