import React, { useState, useMemo } from 'react';
import { Users, Search, RefreshCw } from 'lucide-react';
import { useQuery } from 'react-query';
import { contactsAPI } from '../services/api';

interface Contact {
  id: number;
  name: string;
  email: string;
  company?: string;
  position?: string;
  status?: string;
  last_contact?: string;
  computed_status?: string;
}

interface RecentContactsProps {
  className?: string;
}

const RecentContacts: React.FC<RecentContactsProps> = ({ className = '' }) => {
  const { data: contacts, refetch, isLoading, error } = useQuery('contacts', contactsAPI.getAll);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'new' | 'sent' | 'replied' | 'interested' | 'meeting_scheduled'>('all');

  const filteredContacts = useMemo(() => {
    const contactsArr = contacts?.data || [];
    if (!contactsArr || !Array.isArray(contactsArr)) return [];

    let filtered = contactsArr.filter((contact: Contact) => {
      const matchesSearch = contact.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           contact.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (contact.company && contact.company.toLowerCase().includes(searchTerm.toLowerCase())) ||
                           (contact.position && contact.position.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchesStatus = filterStatus === 'all' || 
                           (contact.computed_status && contact.computed_status.toLowerCase().replace(' ', '_') === filterStatus);
      
      return matchesSearch && matchesStatus;
    });

    return filtered.sort((a, b) => {
      // Sort by last_contact if available, otherwise by id
      if (a.last_contact && b.last_contact) {
        return new Date(b.last_contact).getTime() - new Date(a.last_contact).getTime();
      }
      return b.id - a.id;
    });
  }, [contacts, searchTerm, filterStatus]);

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-green-50 to-emerald-50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-900">Recent Contacts</h3>
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
              placeholder="Search contacts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-sm"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="all">All Contacts</option>
              <option value="new">New</option>
              <option value="sent">Sent</option>
              <option value="replied">Replied</option>
              <option value="interested">Interested</option>
              <option value="meeting_scheduled">Meeting Scheduled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Fixed-height scrollable list */}
      <div className="relative h-80 overflow-y-auto pr-2 scrollbar-thin">
        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading contacts...</p>
          </div>
        )}
        {error ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 mx-auto mb-4 text-red-300" />
            <p className="text-red-600 mb-4">Failed to load contacts.</p>
            <button 
              onClick={() => refetch()} 
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Try again
            </button>
          </div>
        ) : filteredContacts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Users className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <p className="text-sm">No contacts found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredContacts.map((contact) => (
              <div key={contact.id} className="p-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{contact.name}</p>
                    <p className="text-sm text-gray-600 truncate">{contact.email}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {contact.company && (
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                        {contact.company}
                      </span>
                    )}
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

export default RecentContacts;
