import React, { useState, useMemo } from 'react';
import { Mail, Search, RefreshCw } from 'lucide-react';
import { useQuery } from 'react-query';
import { emailsAPI } from '../services/api';

interface Email {
  id: number;
  subject: string;
  content?: string;
  to: string;
  from: string;
  status: string;
  timestamp?: string;
  isStarred?: boolean;
  isRead?: boolean;
}

interface RecentEmailsProps {
  className?: string;
}

const RecentEmails: React.FC<RecentEmailsProps> = ({ className = '' }) => {
  const { data: emailsRes, refetch, isLoading, error } = useQuery('emails', () => emailsAPI.getAll(), {
    retry: 1,
    onError: (error) => {
      // Silent error handling for production
    }
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'sent' | 'received' | 'starred' | 'unread'>('all');

  const filteredEmails = useMemo(() => {
    const emailsArr = emailsRes?.data || [];
    if (!emailsArr || !Array.isArray(emailsArr)) return [];

    let filtered = emailsArr.filter((email: Email) => {
      // Filter out deleted emails
      if ((email.status || '').toLowerCase() === 'deleted') return false;
      
      const matchesSearch = (email.subject || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (email.content && email.content.toLowerCase().includes(searchTerm.toLowerCase())) ||
                           (email.to || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (email.from || '').toLowerCase().includes(searchTerm.toLowerCase());
      
      let matchesStatus = true;
      switch (filterStatus) {
        case 'sent':
          matchesStatus = email.status === 'sent';
          break;
        case 'received':
          matchesStatus = email.status === 'received';
          break;
        case 'starred':
          matchesStatus = email.isStarred === true;
          break;
        case 'unread':
          matchesStatus = email.isRead === false;
          break;
        default:
          matchesStatus = true;
      }
      
      return matchesSearch && matchesStatus;
    });

    return filtered.sort((a, b) => {
      // Sort by timestamp, whichever is more recent
      const aTime = a.timestamp;
      const bTime = b.timestamp;
      if (aTime && bTime) {
        return new Date(bTime).getTime() - new Date(aTime).getTime();
      }
      return b.id - a.id;
    });
  }, [emailsRes, searchTerm, filterStatus]);

  

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-orange-50 to-red-50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-orange-600" />
            <h3 className="text-lg font-semibold text-gray-900">Recent Emails</h3>
          </div>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors duration-150 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Search and Filters */}
        <div className="space-y-3">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search emails..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="all">All Emails</option>
              <option value="sent">Sent</option>
              <option value="received">Received</option>
              <option value="starred">Starred</option>
              <option value="unread">Unread</option>
            </select>
          </div>
        </div>
      </div>

      {/* Fixed-height scrollable list */}
      <div className="relative h-80 overflow-y-auto pr-2 scrollbar-thin">
        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading emails...</p>
          </div>
        )}
        {error ? (
          <div className="text-center py-12">
            <Mail className="w-12 h-12 mx-auto mb-4 text-red-300" />
            <p className="text-red-600 mb-4">Failed to load emails.</p>
            <button 
              onClick={() => refetch()} 
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Try again
            </button>
          </div>
        ) : filteredEmails.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Mail className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <p className="text-sm">No emails found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredEmails.map((email) => (
              <div key={email.id} className="p-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{email.subject || 'No Subject'}</p>
                    <p className="text-sm text-gray-600 truncate">
                      {email.status === 'sent' ? 'To:' : 'From:'} {email.status === 'sent' ? (email.to || 'Unknown') : (email.from || 'Unknown')}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      email.status === 'sent' ? 'bg-green-100 text-green-800' :
                      email.status === 'received' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {email.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
    </div>
  );
};

export default RecentEmails;
