import React, { useState, useEffect } from 'react';
import { 
  Download,
  Star, 
  TrendingUp, 
  TrendingDown,
  Users,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useCallback } from 'react';

interface FeedbackData {
  id: number;
  email: string;
  full_name: string | null;
  company_name: string | null;
  pricing_tier: string;
  deleted_at: string | null;
  feedback_category: string | null;
  feedback_custom_category: string | null;
  feedback_rating: number | null;
  feedback_details: string | null;
  improvements_suggested: string | null;
  competitor_switched_to: string | null;
  contact_consent: boolean;
  contact_method: string | null;
  created_at: string | null;
  account_age_days: number | null;
}

interface FeedbackAnalytics {
  category_analysis: Array<{
    category: string;
    count: number;
    average_rating: number | null;
  }>;
  rating_distribution: Array<{
    rating: number;
    count: number;
  }>;
  competitor_analysis: Array<{
    competitor: string;
    count: number;
  }>;
  contact_consent_analysis: Array<{
    consent: boolean;
    count: number;
  }>;
}

const AdminFeedbackDashboard: React.FC = () => {
  const [feedbackData, setFeedbackData] = useState<FeedbackData[]>([]);
  const [analytics, setAnalytics] = useState<FeedbackAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    category: '',
    min_rating: '',
    max_rating: '',
    search: ''
  });
  const [sortBy, setSortBy] = useState('deleted_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const fetchFeedbackData = useCallback(async () => {
    try {
      const adminToken = localStorage.getItem('admin_token');
      if (!adminToken) {
        throw new Error('No admin token found');
      }
      
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '50',
        ...(filters.category && { category: filters.category }),
        ...(filters.min_rating && { min_rating: filters.min_rating }),
        ...(filters.max_rating && { max_rating: filters.max_rating })
      });

      const response = await fetch(`http://localhost:8000/api/v1/admin/feedback-details?${params}`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch feedback data');
      }

      const data = await response.json();
      setFeedbackData(data.feedback_data);
      setTotalPages(data.total_pages);
    } catch (error) {
      console.error('Error fetching feedback data:', error);
      toast.error('Failed to load feedback data');
    }
  }, [page, filters]);

  const fetchAnalytics = useCallback(async () => {
    try {
      const adminToken = localStorage.getItem('admin_token');
      if (!adminToken) {
        throw new Error('No admin token found');
      }
      
      const response = await fetch('http://localhost:8000/api/v1/admin/feedback-analytics', {
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to load analytics');
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchFeedbackData(), fetchAnalytics()]);
      setLoading(false);
    };
    
    loadData();
  }, [fetchFeedbackData, fetchAnalytics]);

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const exportToCSV = () => {
    const headers = [
      'ID', 'Email', 'Full Name', 'Company', 'Pricing Tier', 'Deleted At',
      'Category', 'Custom Category', 'Rating', 'Details', 'Improvements', 'Competitor',
      'Contact Consent', 'Contact Method', 'Account Age (Days)'
    ];

    const csvData = feedbackData.map(item => [
      item.id,
      item.email,
      item.full_name || '',
      item.company_name || '',
      item.pricing_tier,
      item.deleted_at || '',
      item.feedback_category || '',
      item.feedback_custom_category || '',
      item.feedback_rating || '',
      item.feedback_details || '',
      item.improvements_suggested || '',
      item.competitor_switched_to || '',
      item.contact_consent ? 'Yes' : 'No',
      item.contact_method || '',
      item.account_age_days || ''
    ]);

    const csvContent = [headers, ...csvData]
      .map(row => row.map(field => `"${field}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback-data-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };


  const renderStars = (rating: number | null) => {
    if (!rating) return <span className="text-gray-400">No rating</span>;
    
    return (
      <div className="flex items-center">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-4 h-4 ${
              star <= rating ? 'text-yellow-400 fill-current' : 'text-gray-300'
            }`}
          />
        ))}
        <span className="ml-1 text-sm text-gray-600">({rating})</span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-brand-red mx-auto mb-4" />
          <p className="text-gray-600">Loading feedback data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 space-y-10">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 bg-brand-white rounded-3xl border border-gray-100 p-8 shadow-sm">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-brand-black flex items-center justify-center rounded-lg">
                <MessageSquare className="w-5 h-5 text-brand-white" />
              </div>
              <h1 className="text-3xl font-bold text-brand-black tracking-tight uppercase">Intelligence <span className="text-brand-red italic">Debrief.</span></h1>
            </div>
            <p className="text-gray-400 font-medium text-sm">Analyzing operative feedback and system attrition metrics.</p>
          </div>
          <button
            onClick={exportToCSV}
            className="px-8 py-3 bg-brand-black text-white rounded-full font-bold uppercase tracking-widest text-[10px] hover:bg-brand-red transition-all shadow-xl shadow-brand-black/10 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export Raw Intel (CSV)
          </button>
        </div>

        {/* Analytics Overview */}
        {analytics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { label: 'Total Feedback', value: analytics.category_analysis.reduce((sum, item) => sum + item.count, 0), icon: AlertTriangle, color: 'text-brand-red', bg: 'bg-brand-red/5' },
              { 
                label: 'Avg Rating', 
                value: analytics.rating_distribution.length > 0 
                  ? (analytics.rating_distribution.reduce((sum, item) => sum + (item.rating * item.count), 0) / 
                     analytics.rating_distribution.reduce((sum, item) => sum + item.count, 0)).toFixed(1)
                  : 'N/A',
                icon: Star, color: 'text-amber-500', bg: 'bg-amber-500/5' 
              },
              { label: 'Contact Consent', value: analytics.contact_consent_analysis.find(item => item.consent)?.count || 0, icon: MessageSquare, color: 'text-blue-500', bg: 'bg-blue-50/5' },
              { label: 'Categories', value: analytics.category_analysis.length, icon: Users, color: 'text-brand-black', bg: 'bg-brand-gray' }
            ].map((stat, i) => (
              <div key={i} className="bg-brand-white p-8 rounded-3xl border border-gray-100 shadow-sm group hover:shadow-2xl transition-all duration-700">
                <div className={`w-12 h-12 ${stat.bg} rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">{stat.label}</p>
                <p className="text-4xl font-bold text-brand-black tracking-tighter">{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="bg-brand-white rounded-3xl border border-gray-100 p-8 shadow-sm">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-brand-black uppercase tracking-widest ml-4">Debrief Category</label>
              <select
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
                className="w-full px-6 py-4 bg-brand-gray border border-gray-100 rounded-2xl focus:ring-2 focus:ring-brand-red outline-none transition-all font-black text-[10px] uppercase tracking-widest text-gray-500 appearance-none cursor-pointer"
              >
                <option value="">ALL PROTOCOLS</option>
                <option value="pricing">PRICING_SECTOR</option>
                <option value="features">ENGINE_CAPABILITY</option>
                <option value="support">COMMS_SUPPORT</option>
                <option value="usability">UI_INTERFACE</option>
                <option value="performance">TRANSMISSION_SPEED</option>
                <option value="other">EXTERNAL_FACTORS</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-brand-black uppercase tracking-widest ml-4">Minimum Rating</label>
              <select
                value={filters.min_rating}
                onChange={(e) => handleFilterChange('min_rating', e.target.value)}
                className="w-full px-6 py-4 bg-brand-gray border border-gray-100 rounded-2xl focus:ring-2 focus:ring-brand-red outline-none transition-all font-black text-[10px] uppercase tracking-widest text-gray-500 appearance-none cursor-pointer"
              >
                <option value="">ANY_RATING</option>
                <option value="1">1+ Stars</option>
                <option value="2">2+ Stars</option>
                <option value="3">3+ Stars</option>
                <option value="4">4+ Stars</option>
                <option value="5">5 Stars</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-brand-black uppercase tracking-widest ml-4">Maximum Rating</label>
              <select
                value={filters.max_rating}
                onChange={(e) => handleFilterChange('max_rating', e.target.value)}
                className="w-full px-6 py-4 bg-brand-gray border border-gray-100 rounded-2xl focus:ring-2 focus:ring-brand-red outline-none transition-all font-black text-[10px] uppercase tracking-widest text-gray-500 appearance-none cursor-pointer"
              >
                <option value="">ANY_RATING</option>
                <option value="1">1 Star</option>
                <option value="2">2 Stars</option>
                <option value="3">3 Stars</option>
                <option value="4">4 Stars</option>
                <option value="5">5 Stars</option>
              </select>
            </div>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-brand-white rounded-[2.5rem] border border-gray-100 shadow-sm overflow-hidden transition-all duration-700 hover:shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-brand-gray/50 border-b border-gray-100">
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer"
                      onClick={() => handleSort('email')}>
                    Operative Signal
                    {sortBy === 'email' && (
                      sortOrder === 'asc' ? <TrendingUp className="w-4 h-4 inline ml-1" /> : <TrendingDown className="w-4 h-4 inline ml-1" />
                    )}
                  </th>
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer"
                      onClick={() => handleSort('feedback_category')}>
                    Category
                    {sortBy === 'feedback_category' && (
                      sortOrder === 'asc' ? <TrendingUp className="w-4 h-4 inline ml-1" /> : <TrendingDown className="w-4 h-4 inline ml-1" />
                    )}
                  </th>
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer"
                      onClick={() => handleSort('feedback_rating')}>
                    Sentiment
                    {sortBy === 'feedback_rating' && (
                      sortOrder === 'asc' ? <TrendingUp className="w-4 h-4 inline ml-1" /> : <TrendingDown className="w-4 h-4 inline ml-1" />
                    )}
                  </th>
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    Detailed Intel
                  </th>
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    Competitor
                  </th>
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer"
                      onClick={() => handleSort('deleted_at')}>
                    Timestamp
                    {sortBy === 'deleted_at' && (
                      sortOrder === 'asc' ? <TrendingUp className="w-4 h-4 inline ml-1" /> : <TrendingDown className="w-4 h-4 inline ml-1" />
                    )}
                  </th>
                  <th className="p-8 text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    Contact
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {feedbackData.map((item) => (
                  <tr key={item.id} className="group hover:bg-brand-gray/30 transition-colors">
                    <td className="p-8 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-bold text-brand-black">{item.email}</div>
                        <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1">
                          {item.full_name || 'ANONYMOUS'} • {item.company_name || 'PRIVATE'}
                        </div>
                        <div className="text-[8px] font-black text-brand-red/40 uppercase tracking-widest mt-1">
                          {item.pricing_tier} • {item.account_age_days} DAYS ACTIVE
                        </div>
                      </div>
                    </td>
                    <td className="p-8 whitespace-nowrap">
                      {item.feedback_category && (
                        <span className={`px-4 py-1.5 bg-brand-gray text-[8px] font-black uppercase tracking-widest rounded-full border border-gray-100`}>
                          {item.feedback_category === 'other' && item.feedback_custom_category 
                            ? item.feedback_custom_category 
                            : item.feedback_category}
                        </span>
                      )}
                    </td>
                    <td className="p-8 whitespace-nowrap">
                      {renderStars(item.feedback_rating)}
                    </td>
                    <td className="p-8">
                      <div className="text-xs text-gray-600 font-medium leading-relaxed max-w-sm line-clamp-2">
                        {item.feedback_details}
                      </div>
                      {item.improvements_suggested && (
                        <div className="text-[10px] text-brand-red font-black uppercase tracking-tight mt-2 italic">
                          <strong>UPGRADE:</strong> {item.improvements_suggested}
                        </div>
                      )}
                    </td>
                    <td className="p-8 whitespace-nowrap text-xs font-bold text-gray-400 uppercase">
                      {item.competitor_switched_to || '-'}
                    </td>
                    <td className="p-8 whitespace-nowrap text-[10px] font-medium text-gray-300 uppercase tracking-widest">
                      {item.deleted_at ? new Date(item.deleted_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="p-8 whitespace-nowrap">
                      {item.contact_consent ? (
                        <span className="inline-flex items-center px-3 py-1 bg-green-500/10 text-green-500 text-[8px] font-black uppercase tracking-widest rounded-full">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          AUTHORIZED
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-3 py-1 bg-brand-red/10 text-brand-red text-[8px] font-black uppercase tracking-widest rounded-full">
                          <XCircle className="w-3 h-3 mr-1" />
                          DENIED
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="bg-brand-gray/50 px-8 py-6 flex items-center justify-between border-t border-gray-100 sm:px-10">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-6 py-2 bg-brand-white border border-gray-100 rounded-xl text-[10px] font-black uppercase tracking-widest text-gray-400 disabled:opacity-30"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-6 py-2 bg-brand-white border border-gray-100 rounded-xl text-[10px] font-black uppercase tracking-widest text-gray-400 disabled:opacity-30"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                  Sector <span className="text-brand-black">{page}</span> of{' '}
                  <span className="text-brand-black">{totalPages}</span>
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="p-2 bg-brand-white border border-gray-100 rounded-xl text-gray-400 hover:text-brand-black transition-colors disabled:opacity-30"
                  >
                    <TrendingDown className="w-4 h-4 rotate-90" />
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="p-2 bg-brand-white border border-gray-100 rounded-xl text-gray-400 hover:text-brand-black transition-colors disabled:opacity-30"
                  >
                    <TrendingUp className="w-4 h-4 -rotate-90" />
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminFeedbackDashboard;
