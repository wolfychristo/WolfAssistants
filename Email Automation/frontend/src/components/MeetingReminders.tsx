import React, { useEffect, useMemo, useState } from 'react';
import { AlarmClock, CalendarClock, Search, RefreshCw } from 'lucide-react';
import { useQuery } from 'react-query';
import { meetingsAPI } from '../services/api';
import { isToday, isTomorrow, isThisWeek } from 'date-fns';

export const MeetingReminders: React.FC = () => {
  const { data, refetch, isLoading, error } = useQuery('meetings-reminders', meetingsAPI.getAll, { 
    refetchInterval: 60000,
    retry: 1,
    onError: (error: any) => {
      // Silent error handling for production
    }
  });
  const [now, setNow] = useState(Date.now());
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'today' | 'tomorrow' | 'this_week' | 'upcoming'>('all');

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  const filteredMeetings = useMemo(() => {
    const items = data?.data || [];
    if (!items || !Array.isArray(items)) return [];

    let filtered = items.filter((m) => {
      const matchesSearch = m.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (m.description && m.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
                           (m.location && m.location.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const meetingDate = new Date(m.start_time);
      let matchesFilter = true;
      
      switch (filterType) {
        case 'today':
          matchesFilter = isToday(meetingDate);
          break;
        case 'tomorrow':
          matchesFilter = isTomorrow(meetingDate);
          break;
        case 'this_week':
          matchesFilter = isThisWeek(meetingDate);
          break;
        case 'upcoming':
          matchesFilter = meetingDate.getTime() > now - 5 * 60000; // include those started within last 5m
          break;
        default:
          matchesFilter = true;
      }
      
      return matchesSearch && matchesFilter;
    });

    return filtered.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  }, [data, searchTerm, filterType, now]);

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlarmClock className="w-5 h-5 text-purple-600" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900">Meeting Reminders</h3>
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
              placeholder="Search meetings..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="all">All Meetings</option>
              <option value="upcoming">Upcoming</option>
              <option value="today">Today</option>
              <option value="tomorrow">Tomorrow</option>
              <option value="this_week">This Week</option>
            </select>
          </div>
        </div>
      </div>
      {/* Fixed-height scrollable list */}
      <div className="relative h-80 overflow-y-auto pr-2 scrollbar-thin">
        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading meetings...</p>
          </div>
        )}
        {error ? (
          <div className="text-center py-12">
            <CalendarClock className="w-12 h-12 mx-auto mb-4 text-red-300" />
            <p className="text-red-600 mb-4">Failed to load meetings.</p>
            <button 
              onClick={() => refetch()} 
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Try again
            </button>
          </div>
        ) : filteredMeetings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <CalendarClock className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <p className="text-sm">No upcoming meetings.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredMeetings.map((meeting) => (
              <div key={meeting.id} className="p-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{meeting.title}</p>
                    <p className="text-sm text-gray-600 truncate">
                      {new Date(meeting.start_time).toLocaleString()} • {meeting.location || meeting.type || 'Meeting'}
                    </p>
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

export default MeetingReminders;


