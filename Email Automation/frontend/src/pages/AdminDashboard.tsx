import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserPlus, 
  UserMinus, 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  PieChart, 
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
  RotateCcw,
  MessageSquare,
  Star,
  Shield
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { User, AdminStats } from '../types';
import AdminUserManagement from './AdminUserManagement';
import { useCallback } from 'react';

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'analytics' | 'feedback' | 'user-management'>('overview');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [deletionReason, setDeletionReason] = useState('');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const handleAdminLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    localStorage.removeItem('is_admin');
    window.location.href = '/admin-login';
  };

  const fetchStats = useCallback(async () => {
    try {
      const adminToken = localStorage.getItem('admin_token');
      if (!adminToken) {
        throw new Error('No admin token found');
      }
      
      const response = await fetch('http://localhost:8000/api/v1/admin/stats', {
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch admin stats');
      }
      
      const data = await response.json();
      
      // Transform the data to match the expected structure
      const transformedData = {
        total_users: data.user_stats?.total_users || 0,
        active_users: data.user_stats?.active_users || 0,
        deleted_users: data.user_stats?.deleted_users || 0,
        new_signups_today: 0, // Not provided by backend
        new_signups_this_week: 0, // Not provided by backend
        new_signups_this_month: 0, // Not provided by backend
        deletion_reasons: {}, // Not provided by backend
        tier_distribution: {}, // Not provided by backend
        recent_signups: data.recent_users?.map((user: any) => ({
          id: 0, // Not provided
          email: user.email,
          full_name: user.full_name,
          company_name: user.company_name,
          pricing_tier: 'free', // Not provided
          created_at: user.created_at,
          is_active: user.is_active
        })) || [],
        recent_deletions: data.feedback_details?.map((feedback: any) => ({
          id: 0, // Not provided
          email: feedback.email,
          full_name: null, // Not provided
          company_name: null, // Not provided
          deletion_reason: feedback.category,
          deleted_at: null, // Not provided
          feedback_category: feedback.category,
          feedback_custom_category: feedback.custom_category,
          feedback_rating: feedback.rating,
          feedback_details: feedback.details
        })) || [],
        feedback_categories: data.feedback_stats?.categories?.reduce((acc: any, cat: any) => {
          acc[cat.category] = cat.count;
          return acc;
        }, {} as Record<string, number>) || {},
        average_feedback_rating: 0, // Not provided by backend
        feedback_insights: {
          total_feedback_responses: data.feedback_stats?.users_with_feedback || 0,
          most_common_category: null,
          lowest_rated_category: null,
          contact_consent_rate: 0
        },
        admin_users: data.user_stats?.admin_users || 0
      };
      
      setStats(transformedData);
    } catch (error) {
      console.error('Error fetching stats:', error);
      toast.error('Failed to load admin statistics');
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const adminToken = localStorage.getItem('admin_token');
      if (!adminToken) {
        throw new Error('No admin token found');
      }
      
      const response = await fetch(`http://localhost:8000/api/v1/admin/users?page=${page}&limit=20&include_deleted=${includeDeleted}`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }
      
      const data = await response.json();
      setUsers(data.users || []);
      setTotalPages(data.total_pages || 1);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast.error('Failed to load users');
    }
  }, [page, includeDeleted]);

  const deleteUser = async (userId: number, reason: string) => {
    try {
      const adminToken = localStorage.getItem('admin_token');
      if (!adminToken) {
        throw new Error('No admin token found');
      }
      
      const response = await fetch(`http://localhost:8000/api/v1/admin/users/${userId}/delete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId, reason }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete user');
      }
      
      toast.success('User deleted successfully');
      fetchUsers();
      fetchStats();
    } catch (error) {
      console.error('Error deleting user:', error);
      toast.error('Failed to delete user');
    }
  };

  const restoreUser = async (userId: number) => {
    try {
      const adminToken = localStorage.getItem('admin_token');
      if (!adminToken) {
        throw new Error('No admin token found');
      }
      
      const response = await fetch(`http://localhost:8000/api/v1/admin/users/${userId}/restore`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to restore user');
      }
      
      toast.success('User restored successfully');
      fetchUsers();
      fetchStats();
    } catch (error) {
      console.error('Error restoring user:', error);
      toast.error('Failed to restore user');
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchStats(), fetchUsers()]);
      setLoading(false);
    };
    
    loadData();
  }, [fetchStats, fetchUsers]);

  const StatCard: React.FC<{ title: string; value: number; icon: React.ReactNode; color: string; trend?: number }> = ({ 
    title, 
    value, 
    icon, 
    color, 
    trend 
  }) => (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900">{(value || 0).toLocaleString()}</p>
          {trend !== undefined && (
            <div className={`flex items-center mt-2 text-sm ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend >= 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
              {Math.abs(trend)}%
            </div>
          )}
        </div>
        <div className={`p-3 rounded-full ${color}`}>
          {icon}
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-brand-red mx-auto mb-4" />
          <p className="text-gray-600">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-600 mt-2">Monitor user activity, signups, and system health</p>
          </div>
          <button
            onClick={handleAdminLogout}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            Admin Logout
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('overview')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'overview'
                    ? 'border-brand-red text-brand-red'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'users'
                    ? 'border-brand-red text-brand-red'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Users
              </button>
              <button
                onClick={() => setActiveTab('analytics')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'analytics'
                    ? 'border-brand-red text-brand-red'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Analytics
              </button>
              <button
                onClick={() => setActiveTab('feedback')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'feedback'
                    ? 'border-brand-red text-brand-red'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Feedback
              </button>
              <button
                onClick={() => setActiveTab('user-management')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'user-management'
                    ? 'border-brand-red text-brand-red'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Shield className="w-4 h-4 inline mr-1" />
                User Management
              </button>
            </nav>
          </div>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-8">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard
                title="Total Users"
                value={stats.total_users}
                icon={<Users className="w-6 h-6 text-white" />}
                color="bg-brand-red"
              />
              <StatCard
                title="Active Users"
                value={stats.active_users}
                icon={<CheckCircle className="w-6 h-6 text-white" />}
                color="bg-green-500"
              />
              <StatCard
                title="New Signups Today"
                value={stats.new_signups_today}
                icon={<UserPlus className="w-6 h-6 text-white" />}
                color="bg-blue-500"
              />
              <StatCard
                title="Deleted Users"
                value={stats.deleted_users}
                icon={<UserMinus className="w-6 h-6 text-white" />}
                color="bg-red-500"
              />
            </div>

            {/* Tier Distribution */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">User Tier Distribution</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(stats.tier_distribution || {}).map(([tier, count]) => (
                  <div key={tier} className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-2xl font-bold text-brand-red">{count}</p>
                    <p className="text-sm text-gray-600 capitalize">{tier}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Signups */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Signups</h3>
                <div className="space-y-3">
                  {(stats.recent_signups || []).map((user) => (
                    <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">{user.email}</p>
                        <p className="text-sm text-gray-600">
                          {user.full_name} • {user.company_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(user.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        user.pricing_tier === 'free' ? 'bg-gray-200 text-gray-800' :
                        user.pricing_tier === 'starter' ? 'bg-blue-200 text-blue-800' :
                        user.pricing_tier === 'professional' ? 'bg-purple-200 text-purple-800' :
                        'bg-yellow-200 text-yellow-800'
                      }`}>
                        {user.pricing_tier}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Deletions */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Deletions</h3>
                <div className="space-y-3">
                  {(stats.recent_deletions || []).map((user) => (
                    <div key={user.id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">{user.email}</p>
                        <p className="text-sm text-gray-600">
                          {user.full_name} • {user.company_name}
                        </p>
                        <p className="text-xs text-red-600">
                          {user.deletion_reason || 'No reason provided'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {user.deleted_at ? new Date(user.deleted_at).toLocaleDateString() : 'Unknown'}
                        </p>
                      </div>
                      <XCircle className="w-5 h-5 text-red-500" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeDeleted}
                      onChange={(e) => setIncludeDeleted(e.target.checked)}
                      className="rounded border-gray-300 text-brand-red focus:ring-brand-red"
                    />
                    <span className="ml-2 text-sm text-gray-700">Include deleted users</span>
                  </label>
                </div>
                <button
                  onClick={() => fetchUsers()}
                  className="flex items-center px-4 py-2 bg-brand-red text-white rounded-lg hover:bg-primary-600 transition-colors"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </button>
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tier
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {(users || []).map((user) => (
                      <tr key={user.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">{user.email}</div>
                            <div className="text-sm text-gray-500">
                              {user.full_name} • {user.company_name}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            user.pricing_tier === 'free' ? 'bg-gray-200 text-gray-800' :
                            user.pricing_tier === 'starter' ? 'bg-blue-200 text-blue-800' :
                            user.pricing_tier === 'professional' ? 'bg-purple-200 text-purple-800' :
                            'bg-yellow-200 text-yellow-800'
                          }`}>
                            {user.pricing_tier}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {user.deleted_at ? (
                              <span className="flex items-center text-red-600">
                                <XCircle className="w-4 h-4 mr-1" />
                                Deleted
                              </span>
                            ) : user.is_active ? (
                              <span className="flex items-center text-green-600">
                                <CheckCircle className="w-4 h-4 mr-1" />
                                Active
                              </span>
                            ) : (
                              <span className="flex items-center text-yellow-600">
                                <AlertCircle className="w-4 h-4 mr-1" />
                                Inactive
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            {user.deleted_at ? (
                              <button
                                onClick={() => restoreUser(user.id)}
                                className="text-green-600 hover:text-green-900 flex items-center"
                              >
                                <RotateCcw className="w-4 h-4 mr-1" />
                                Restore
                              </button>
                            ) : (
                              <button
                                onClick={() => setSelectedUser(user)}
                                className="text-red-600 hover:text-red-900 flex items-center"
                              >
                                <Trash2 className="w-4 h-4 mr-1" />
                                Delete
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                <div className="flex-1 flex justify-between sm:hidden">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      Page <span className="font-medium">{page}</span> of{' '}
                      <span className="font-medium">{totalPages}</span>
                    </p>
                  </div>
                  <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                      <button
                        onClick={() => setPage(Math.max(1, page - 1))}
                        disabled={page === 1}
                        className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setPage(Math.min(totalPages, page + 1))}
                        disabled={page === totalPages}
                        className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                      >
                        Next
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* User Analytics */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">User Analytics</h3>
              
              {/* User Growth Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <Users className="w-8 h-8 text-blue-600" />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-600">Total Users</p>
                      <p className="text-2xl font-bold text-gray-900">{stats?.total_users || 0}</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-600">Active Users</p>
                      <p className="text-2xl font-bold text-gray-900">{stats?.active_users || 0}</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-red-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <XCircle className="w-8 h-8 text-red-600" />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-600">Deleted Users</p>
                      <p className="text-2xl font-bold text-gray-900">{stats?.deleted_users || 0}</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <TrendingUp className="w-8 h-8 text-purple-600" />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-600">Retention Rate</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {stats?.total_users && stats.total_users > 0 ? Math.round(((stats?.active_users || 0) / stats.total_users) * 100) : 0}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* User Tier Distribution */}
              {stats?.tier_distribution && Object.keys(stats.tier_distribution).length > 0 && (
                <div className="mb-8">
                  <h4 className="text-md font-semibold text-gray-900 mb-4">User Tier Distribution</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(stats.tier_distribution || {}).map(([tier, count]) => (
                      <div key={tier} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-900 capitalize">
                            {tier}
                          </span>
                          <span className="text-lg font-bold text-brand-red">{count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Feedback Analytics */}
              {stats?.feedback_categories && Object.keys(stats.feedback_categories).length > 0 && (
                <div>
                  <h4 className="text-md font-semibold text-gray-900 mb-4">Feedback Analytics</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {Object.entries(stats.feedback_categories || {}).map(([category, count]) => (
                      <div key={category} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-900 capitalize">
                            {category}
                          </span>
                          <span className="text-lg font-bold text-brand-red">{count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* System Health */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">Database Status</p>
                  <p className="text-lg font-bold text-green-600">Healthy</p>
                </div>
                
                <div className="text-center">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-2">
                    <BarChart3 className="w-8 h-8 text-blue-600" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">Total Feedback</p>
                  <p className="text-lg font-bold text-gray-900">{stats?.feedback_insights?.total_feedback_responses || 0}</p>
                </div>
                
                <div className="text-center">
                  <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-2">
                    <PieChart className="w-8 h-8 text-purple-600" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">Admin Users</p>
                  <p className="text-lg font-bold text-gray-900">{stats?.admin_users || 0}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Feedback Tab */}
        {activeTab === 'feedback' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">User Departure Feedback</h3>
                <button
                  onClick={() => window.open('/wolf-admin-secure-2024/feedback', '_blank')}
                  className="flex items-center px-4 py-2 bg-brand-red text-white rounded-md hover:bg-primary-600"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Detailed View
                </button>
              </div>
              
              {stats?.feedback_categories && Object.keys(stats.feedback_categories).length > 0 ? (
                <div className="space-y-6">
                  {/* Feedback Overview */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <MessageSquare className="w-8 h-8 text-brand-red" />
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-600">Total Feedback</p>
                          <p className="text-2xl font-bold text-gray-900">
                            {stats.feedback_insights?.total_feedback_responses || 0}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <Star className="w-8 h-8 text-yellow-500" />
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-600">Avg Rating</p>
                          <p className="text-2xl font-bold text-gray-900">
                            {stats.average_feedback_rating || 'N/A'}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <CheckCircle className="w-8 h-8 text-green-500" />
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-600">Contact Consent</p>
                          <p className="text-2xl font-bold text-gray-900">
                            {Math.round(stats.feedback_insights?.contact_consent_rate || 0)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Category Breakdown */}
                  <div>
                    <h4 className="text-md font-semibold text-gray-900 mb-4">Feedback Categories</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {Object.entries(stats.feedback_categories || {}).map(([category, count]) => (
                        <div key={category} className="bg-gray-50 rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-900 capitalize">
                              {category}
                            </span>
                            <span className="text-lg font-bold text-brand-red">{count}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Recent Feedback */}
                  {stats.recent_deletions && stats.recent_deletions.length > 0 && (
                    <div>
                      <h4 className="text-md font-semibold text-gray-900 mb-4">Recent Feedback</h4>
                      <div className="space-y-3">
                        {(stats.recent_deletions || [])
                          .filter(user => user.feedback_category)
                          .slice(0, 5)
                          .map((user) => (
                          <div key={user.id} className="bg-gray-50 rounded-lg p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-gray-900">{user.email}</p>
                                <p className="text-sm text-gray-600">
                                  {user.feedback_category === 'other' && user.feedback_custom_category 
                                    ? user.feedback_custom_category 
                                    : user.feedback_category} • 
                                  {user.feedback_rating && (
                                    <span className="ml-1">
                                      {Array.from({ length: user.feedback_rating }, (_, i) => (
                                        <Star key={i} className="w-4 h-4 text-yellow-400 fill-current inline" />
                                      ))}
                                    </span>
                                  )}
                                </p>
                                {user.feedback_details && (
                                  <p className="text-sm text-gray-500 mt-1 truncate max-w-md">
                                    {user.feedback_details}
                                  </p>
                                )}
                              </div>
                              <span className="text-xs text-gray-500">
                                {user.deleted_at ? new Date(user.deleted_at).toLocaleDateString() : ''}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Feedback Yet</h3>
                  <p className="text-gray-600">
                    User departure feedback will appear here once users start providing it.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Delete User Modal */}
        {selectedUser && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Delete User</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Are you sure you want to delete <strong>{selectedUser.email}</strong>?
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reason for deletion
                  </label>
                  <textarea
                    value={deletionReason}
                    onChange={(e) => setDeletionReason(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-red"
                    rows={3}
                    placeholder="Enter reason for deletion..."
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => {
                      setSelectedUser(null);
                      setDeletionReason('');
                    }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      deleteUser(selectedUser.id, deletionReason);
                      setSelectedUser(null);
                      setDeletionReason('');
                    }}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                  >
                    Delete User
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* User Management Tab */}
        {activeTab === 'user-management' && (
          <AdminUserManagement />
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
