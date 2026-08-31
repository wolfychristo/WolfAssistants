import React, { useState, useEffect } from 'react';
import { chatSessionsAPI } from '../services/api';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
// Removed timestamp rendering; no need to import formatter

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

interface ChatSessionsProps {
  onSelectSession: (session: ChatSession) => void;
  onNewSession: () => void;
  currentSessionId?: number;
}

export const ChatSessions: React.FC<ChatSessionsProps> = ({
  onSelectSession,
  onNewSession,
  currentSessionId
}) => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [newSessionContact, setNewSessionContact] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

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

  const handleCreateSession = async () => {
    try {
      const sessionData: any = {};
      if (newSessionTitle.trim()) {
        sessionData.title = newSessionTitle.trim();
      }
      if (newSessionContact.trim()) {
        sessionData.contact_name = newSessionContact.trim();
      }

      const response = await chatSessionsAPI.create(sessionData);
      const newSession = response.data;
      setSessions(prev => [newSession, ...prev]);
      
      // Store this session as the last active one
      if (user?.email) {
        localStorage.setItem(`wolfy_last_session_${user.email}`, newSession.id.toString());
      }
      
      onSelectSession(newSession);
      setNewSessionTitle('');
      setNewSessionContact('');
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    if (!window.confirm('Are you sure you want to delete this chat session?')) {
      return;
    }

    try {
      await chatSessionsAPI.delete(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      // Clear localStorage if this was the last active session
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
        // Store this session as the last active one
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

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-800 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Chat Sessions</h2>
          <div className="flex gap-2">
            <Button 
              size="sm" 
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white"
              onClick={async () => {
                try {
                  // Create session without prompting - backend will auto-generate title
                  const response = await chatSessionsAPI.create({
                    // No title provided - backend will generate "New Chat {datetime}"
                  });
                  const newSession = response.data;
                  setSessions(prev => [newSession, ...prev]);
                  onSelectSession(newSession);
                } catch (error) {
                  console.error('Failed to create new session:', error);
                  alert('Failed to create new chat session. Please try again.');
                }
              }}
            >
              <Plus className="w-4 h-4" />
              New Chat
            </Button>
            <Dialog>
              <DialogTrigger>
                <Button size="sm" className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-white border-gray-600">
                  <Plus className="w-4 h-4" />
                  Custom
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-gray-800 border-gray-700">
                <DialogHeader>
                  <DialogTitle className="text-white">Start New Chat</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-gray-300">Session Title (optional)</label>
                    <Input
                      value={newSessionTitle}
                      onChange={(e) => setNewSessionTitle(e.target.value)}
                      placeholder="e.g., Project Discussion"
                      className="bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-300">Contact Name (optional)</label>
                    <Input
                      value={newSessionContact}
                      onChange={(e) => setNewSessionContact(e.target.value)}
                      placeholder="e.g., John Smith"
                      className="bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => {
                      setNewSessionTitle('');
                      setNewSessionContact('');
                    }} className="border-gray-600 text-gray-300 hover:bg-gray-700">
                      Cancel
                    </Button>
                    <Button onClick={handleCreateSession} className="bg-blue-600 hover:bg-blue-700 text-white">
                      Start Chat
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
        
        {/* Search */}
        <Input
          placeholder="Search sessions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full bg-gray-700 border-gray-600 text-white placeholder-gray-400"
        />
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {filteredSessions.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            {searchTerm ? 'No sessions found' : 'No chat sessions yet'}
          </div>
        ) : (
          filteredSessions.map((session) => (
            <Card
              key={session.id}
              className={`p-3 cursor-pointer transition-colors hover:bg-gray-800 border-gray-700 ${
                currentSessionId === session.id ? 'bg-gray-700 border-gray-600' : 'bg-gray-800'
              }`}
              onClick={() => handleActivateSession(session.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <h3 className="font-medium text-white truncate">
                      {session.title}
                    </h3>
                    {session.is_active && (
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full flex-shrink-0"></div>
                        <span className="text-xs text-green-400">Active</span>
                      </div>
                    )}
                  </div>
                  
                  {session.contact_name && (
                    <p className="text-sm text-gray-400 mt-1 truncate">
                      with {session.contact_name}
                    </p>
                  )}
                  
                  {/* Removed message count and timestamp per request */}
                </div>
                
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0 text-gray-400 hover:text-white hover:bg-gray-700"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSession(session.id);
                    }}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};
