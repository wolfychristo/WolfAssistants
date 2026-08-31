import React, { useState, useEffect } from 'react';
import { chatSessionsAPI } from '../services/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { 
  Plus, 
  MessageSquare, 
  Search, 
  Trash2, 
  ChevronDown,
  Bot
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface ChatSession {
  public_id?: string;
  id: number;
  title: string;
  contact_name?: string;
  contact_email?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  last_message_at?: string;
  message_count?: number;
}

interface ChatSidebarProps {
  onSelectSession: (session: ChatSession) => void;
  onNewSession: () => void;
  currentSessionId?: number;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  onSelectSession,
  onNewSession,
  currentSessionId,
  isCollapsed = false,
  onToggleCollapse
}) => {
  const { user, isLoading: authLoading } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (user && !authLoading) {
      loadSessions();
    } else if (!user) {
      setSessions([]);
      setLoading(false);
    }
  }, [user, authLoading]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await chatSessionsAPI.getAll({ limit: 50, include_inactive: true });
      setSessions(response.data.sessions || []);
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickNewSession = async () => {
    try {
      // Create session without prompting - backend will auto-generate title
      const response = await chatSessionsAPI.create({
        // No title provided - backend will generate "New Chat {datetime}"
      });
      const newSession = response.data;
      setSessions(prev => [newSession, ...prev]);
      
      if (user?.email) {
        localStorage.setItem(`wolfy_last_session_${user.email}`, newSession.id.toString());
      }
      
      onSelectSession(newSession);
    } catch (error) {
      console.error('Failed to create new session:', error);
      alert('Failed to create new chat session. Please try again.');
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    if (!window.confirm('Are you sure you want to delete this chat session?')) {
      return;
    }

    try {
      await chatSessionsAPI.delete(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      if (user?.email) {
        const lastSessionId = localStorage.getItem(`wolfy_last_session_${user.email}`);
        if (lastSessionId === sessionId.toString()) {
          localStorage.removeItem(`wolfy_last_session_${user.email}`);
        }
      }
      
      if (currentSessionId === sessionId) {
        onNewSession();
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleActivateSession = async (sessionId: number) => {
    try {
      await chatSessionsAPI.activate(sessionId);
      const updated = sessions.map(s => ({ ...s, is_active: s.id === sessionId }));
      setSessions(updated);
      const selected = updated.find(s => s.id === sessionId);
      if (selected) {
        if (user?.email) {
          localStorage.setItem(`wolfy_last_session_${user.email}`, selected.id.toString());
        }
        onSelectSession(selected);
      } else {
        onNewSession();
      }
    } catch (error) {
      console.error('Failed to activate session:', error);
      onNewSession();
    }
  };

  const filteredSessions = sessions.filter(session =>
    session.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (session.contact_name && session.contact_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const truncateText = (text: string, maxLength: number) => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  if (isCollapsed) {
    return (
      <div className="w-16 bg-brand-black border-r border-gray-700 flex flex-col items-center py-4 space-y-4">
        <Button
          size="sm"
          className="w-10 h-10 rounded-lg bg-gray-800 hover:bg-gray-700 text-white"
          onClick={handleQuickNewSession}
        >
          <Plus className="w-5 h-5" />
        </Button>
        <div className="w-8 h-px bg-gray-700"></div>
        <div className="flex flex-col space-y-2">
          {sessions.slice(0, 5).map((session) => (
            <Button
              key={session.id}
              size="sm"
              variant="ghost"
              className={`w-10 h-10 rounded-lg ${
                currentSessionId === session.id
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
              onClick={() => handleActivateSession(session.id)}
              title={session.title}
            >
              <MessageSquare className="w-4 h-4" />
            </Button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-brand-black border-r border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6 text-white" />
            <h2 className="text-lg font-semibold text-white">Wolfy</h2>
          </div>
          {onToggleCollapse && (
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-400 hover:text-white hover:bg-gray-800"
              onClick={onToggleCollapse}
            >
              <ChevronDown className="w-4 h-4" />
            </Button>
          )}
        </div>
        
        <Button
          onClick={handleQuickNewSession}
          className="w-full bg-white hover:bg-gray-50 text-gray-900 border border-gray-300 rounded-lg py-2.5 flex items-center gap-2 font-medium"
        >
          <Plus className="w-4 h-4" />
          New chat
        </Button>
        
        <div className="mt-4 relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Q Search chats..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 bg-white border-gray-300 text-gray-900 placeholder-gray-400 focus:border-blue-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4">
            <div className="animate-pulse space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-800 rounded-lg"></div>
              ))}
            </div>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-600" />
            <p className="text-sm">
              {searchTerm ? 'No chats found' : 'No chat sessions yet'}
            </p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {filteredSessions.map((session) => (
              <div
                key={session.id}
                className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                  currentSessionId === session.id
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
                onClick={() => handleActivateSession(session.id)}
              >
                <MessageSquare className="w-5 h-5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {truncateText(session.title, 30)}
                  </p>
                  {session.contact_name && (
                    <p className="text-xs text-gray-400 truncate">
                      {session.contact_name}
                    </p>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-400 transition-opacity"
                  title="Delete session"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
