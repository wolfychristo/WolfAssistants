import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Shield, 
  AlertTriangle, 
  Ban, 
  Bell,
  Activity,
  TrendingUp,
  UserCheck
} from 'lucide-react';
import { useCallback } from 'react';

interface UserActivity {
  id: number;
  user_id: number;
  activity_type: string;
  description: string;
  ip_address: string;
  risk_score: number;
  created_at: string;
  metadata: string;
}

interface UserBan {
  id: number;
  user_id: number;
  user_email: string;
  reason: string;
  description: string;
  status: string;
  banned_at: string;
  expires_at: string | null;
  banned_by: string;
  appeal_submitted_at: string | null;
}

interface AbusePattern {
  id: number;
  user_id: number;
  user_email: string;
  pattern_type: string;
  severity: number;
  occurrences: number;
  first_detected: string;
  last_detected: string;
  is_active: boolean;
  auto_ban_triggered: boolean;
}

interface AdminNotification {
  id: number;
  type: string;
  title: string;
  message: string;
  user_id: number | null;
  user_email: string | null;
  priority: number;
  is_read: boolean;
  created_at: string;
  metadata: string;
}

interface AbuseStatistics {
  total_abuse_patterns: number;
  active_bans: number;
  high_risk_users: number;
  recent_notifications: number;
}

const AdminUserManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [activities, setActivities] = useState<UserActivity[]>([]);
  const [bans, setBans] = useState<UserBan[]>([]);
  const [abusePatterns, setAbusePatterns] = useState<AbusePattern[]>([]);
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const [statistics, setStatistics] = useState<AbuseStatistics | null>(null);
  const [loading, setLoading] = useState(false);

  // Ban user form
  const [banForm, setBanForm] = useState({
    user_id: '',
    reason: 'spam',
    description: '',
    ban_duration_days: ''
  });

  // Unban user form
  const [unbanForm, setUnbanForm] = useState({
    user_id: '',
    reason: ''
  });


  const loadStatistics = useCallback(async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/statistics/abuse', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatistics(data);
      }
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  }, []);

  const loadActivities = useCallback(async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/users/activities?limit=50', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setActivities(data.activities);
      }
    } catch (error) {
      console.error('Error loading activities:', error);
    }
  }, []);

  const loadBans = useCallback(async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/users/bans?limit=50', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setBans(data.bans);
      }
    } catch (error) {
      console.error('Error loading bans:', error);
    }
  }, []);

  const loadAbusePatterns = useCallback(async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/users/abuse-patterns?days=30', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAbusePatterns(data.patterns);
      }
    } catch (error) {
      console.error('Error loading abuse patterns:', error);
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/notifications?limit=20', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setNotifications(data.notifications);
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('admin_token');
      if (!token) return;

      switch (activeTab) {
        case 'overview':
          await Promise.all([
            loadStatistics(),
            loadNotifications()
          ]);
          break;
        case 'activities':
          await loadActivities();
          break;
        case 'bans':
          await loadBans();
          break;
        case 'patterns':
          await loadAbusePatterns();
          break;
        case 'notifications':
          await loadNotifications();
          break;
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  }, [activeTab, loadStatistics, loadNotifications, loadActivities, loadBans, loadAbusePatterns]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const banUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/users/ban', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: parseInt(banForm.user_id),
          reason: banForm.reason,
          description: banForm.description,
          ban_duration_days: banForm.ban_duration_days ? parseInt(banForm.ban_duration_days) : null
        })
      });

      if (response.ok) {
        alert('User banned successfully');
        setBanForm({ user_id: '', reason: 'spam', description: '', ban_duration_days: '' });
        loadBans();
        loadStatistics();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error banning user:', error);
      alert('Error banning user');
    }
  };

  const unbanUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('http://localhost:8000/api/v1/admin/users/unban', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: parseInt(unbanForm.user_id),
          reason: unbanForm.reason
        })
      });

      if (response.ok) {
        alert('User unbanned successfully');
        setUnbanForm({ user_id: '', reason: '' });
        loadBans();
        loadStatistics();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error unbanning user:', error);
      alert('Error unbanning user');
    }
  };

  const markNotificationRead = async (notificationId: number) => {
    try {
      const token = localStorage.getItem('admin_token');
      await fetch(`http://localhost:8000/api/v1/admin/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      loadNotifications();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 80) return 'text-red-600 bg-red-100';
    if (score >= 50) return 'text-yellow-600 bg-yellow-100';
    if (score >= 20) return 'text-orange-600 bg-orange-100';
    return 'text-green-600 bg-green-100';
  };

  const getSeverityColor = (severity: number) => {
    if (severity >= 4) return 'text-red-600 bg-red-100';
    if (severity >= 3) return 'text-orange-600 bg-orange-100';
    if (severity >= 2) return 'text-yellow-600 bg-yellow-100';
    return 'text-blue-600 bg-blue-100';
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 4) return 'text-red-600 bg-red-100';
    if (priority >= 3) return 'text-orange-600 bg-orange-100';
    if (priority >= 2) return 'text-yellow-600 bg-yellow-100';
    return 'text-blue-600 bg-blue-100';
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: TrendingUp },
    { id: 'activities', label: 'User Activities', icon: Activity },
    { id: 'bans', label: 'User Bans', icon: Ban },
    { id: 'patterns', label: 'Abuse Patterns', icon: AlertTriangle },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'actions', label: 'Actions', icon: Shield }
  ];

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">User Management & Abuse Prevention</h1>
          <p className="text-gray-600">Monitor user activities, detect abuse patterns, and manage user access</p>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          )}

          {!loading && (
            <>
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                      <div className="flex items-center">
                        <div className="p-2 bg-red-100 rounded-lg">
                          <Ban className="w-6 h-6 text-red-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-red-600">Active Bans</p>
                          <p className="text-2xl font-bold text-red-900">{statistics?.active_bans || 0}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-6">
                      <div className="flex items-center">
                        <div className="p-2 bg-orange-100 rounded-lg">
                          <AlertTriangle className="w-6 h-6 text-orange-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-orange-600">Abuse Patterns</p>
                          <p className="text-2xl font-bold text-orange-900">{statistics?.total_abuse_patterns || 0}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                      <div className="flex items-center">
                        <div className="p-2 bg-yellow-100 rounded-lg">
                          <Users className="w-6 h-6 text-yellow-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-yellow-600">High Risk Users</p>
                          <p className="text-2xl font-bold text-yellow-900">{statistics?.high_risk_users || 0}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                      <div className="flex items-center">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Bell className="w-6 h-6 text-blue-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-blue-600">Notifications</p>
                          <p className="text-2xl font-bold text-blue-900">{statistics?.recent_notifications || 0}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recent Notifications */}
                  <div className="bg-gray-50 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Notifications</h3>
                    <div className="space-y-3">
                      {notifications.slice(0, 5).map((notification) => (
                        <div
                          key={notification.id}
                          className={`p-4 rounded-lg border ${
                            notification.is_read ? 'bg-white border-gray-200' : 'bg-blue-50 border-blue-200'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <h4 className="font-medium text-gray-900">{notification.title}</h4>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(notification.priority)}`}>
                                  Priority {notification.priority}
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
                              <p className="text-xs text-gray-500 mt-2">
                                {new Date(notification.created_at).toLocaleString()}
                              </p>
                            </div>
                            {!notification.is_read && (
                              <button
                                onClick={() => markNotificationRead(notification.id)}
                                className="ml-4 text-blue-600 hover:text-blue-800"
                              >
                                Mark as read
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Activities Tab */}
              {activeTab === 'activities' && (
                <div className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">User Activities</h3>
                    <button
                      onClick={loadActivities}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Refresh
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            User ID
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Activity
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Description
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Risk Score
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            IP Address
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Time
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {activities.map((activity) => (
                          <tr key={activity.id}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {activity.user_id}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {activity.activity_type}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900">
                              {activity.description}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(activity.risk_score)}`}>
                                {activity.risk_score}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {activity.ip_address}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(activity.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Bans Tab */}
              {activeTab === 'bans' && (
                <div className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">User Bans</h3>
                    <button
                      onClick={loadBans}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Refresh
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            User
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Reason
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Banned By
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Banned At
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Expires
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Appeal
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {bans.map((ban) => (
                          <tr key={ban.id}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {ban.user_email}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900">
                              {ban.reason}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                ban.status === 'active' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                              }`}>
                                {ban.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {ban.banned_by}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(ban.banned_at).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {ban.expires_at ? new Date(ban.expires_at).toLocaleString() : 'Permanent'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {ban.appeal_submitted_at ? 'Submitted' : 'None'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Abuse Patterns Tab */}
              {activeTab === 'patterns' && (
                <div className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">Abuse Patterns</h3>
                    <button
                      onClick={loadAbusePatterns}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Refresh
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            User
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Pattern Type
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Severity
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Occurrences
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            First Detected
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Last Detected
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Auto Ban
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {abusePatterns.map((pattern) => (
                          <tr key={pattern.id}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {pattern.user_email}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900">
                              {pattern.pattern_type}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(pattern.severity)}`}>
                                {pattern.severity}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {pattern.occurrences}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(pattern.first_detected).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(pattern.last_detected).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {pattern.auto_ban_triggered ? (
                                <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                  Triggered
                                </span>
                              ) : (
                                <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                  No
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <div className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">Admin Notifications</h3>
                    <button
                      onClick={loadNotifications}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Refresh
                    </button>
                  </div>

                  <div className="space-y-4">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-6 rounded-lg border ${
                          notification.is_read ? 'bg-white border-gray-200' : 'bg-blue-50 border-blue-200'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3">
                              <h4 className="text-lg font-semibold text-gray-900">{notification.title}</h4>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(notification.priority)}`}>
                                Priority {notification.priority}
                              </span>
                              {!notification.is_read && (
                                <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  New
                                </span>
                              )}
                            </div>
                            <p className="text-gray-600 mt-2">{notification.message}</p>
                            {notification.user_email && (
                              <p className="text-sm text-gray-500 mt-2">
                                Related User: {notification.user_email}
                              </p>
                            )}
                            <p className="text-xs text-gray-500 mt-3">
                              {new Date(notification.created_at).toLocaleString()}
                            </p>
                          </div>
                          {!notification.is_read && (
                            <button
                              onClick={() => markNotificationRead(notification.id)}
                              className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                              Mark as Read
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions Tab */}
              {activeTab === 'actions' && (
                <div className="p-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Ban User Form */}
                    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                      <h3 className="text-lg font-semibold text-red-900 mb-4 flex items-center">
                        <Ban className="w-5 h-5 mr-2" />
                        Ban User
                      </h3>
                      <form onSubmit={banUser} className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            User ID
                          </label>
                          <input
                            type="number"
                            value={banForm.user_id}
                            onChange={(e) => setBanForm({ ...banForm, user_id: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Reason
                          </label>
                          <select
                            value={banForm.reason}
                            onChange={(e) => setBanForm({ ...banForm, reason: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          >
                            <option value="spam">Unwanted Outreach</option>
                            <option value="abuse">Abuse</option>
                            <option value="suspicious_activity">Suspicious Activity</option>
                            <option value="terms_violation">Terms Violation</option>
                            <option value="fraud">Fraud</option>
                            <option value="harassment">Harassment</option>
                            <option value="inappropriate_content">Inappropriate Content</option>
                            <option value="system_abuse">System Abuse</option>
                            <option value="multiple_accounts">Multiple Accounts</option>
                            <option value="manual_ban">Manual Ban</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description
                          </label>
                          <textarea
                            value={banForm.description}
                            onChange={(e) => setBanForm({ ...banForm, description: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                            rows={3}
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Ban Duration (days) - Leave empty for permanent
                          </label>
                          <input
                            type="number"
                            value={banForm.ban_duration_days}
                            onChange={(e) => setBanForm({ ...banForm, ban_duration_days: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                            placeholder="e.g., 7 for 7 days"
                          />
                        </div>
                        <button
                          type="submit"
                          className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                        >
                          Ban User
                        </button>
                      </form>
                    </div>

                    {/* Unban User Form */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                      <h3 className="text-lg font-semibold text-green-900 mb-4 flex items-center">
                        <UserCheck className="w-5 h-5 mr-2" />
                        Unban User
                      </h3>
                      <form onSubmit={unbanUser} className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            User ID
                          </label>
                          <input
                            type="number"
                            value={unbanForm.user_id}
                            onChange={(e) => setUnbanForm({ ...unbanForm, user_id: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Reason for Unban
                          </label>
                          <textarea
                            value={unbanForm.reason}
                            onChange={(e) => setUnbanForm({ ...unbanForm, reason: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                            rows={3}
                            required
                          />
                        </div>
                        <button
                          type="submit"
                          className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                        >
                          Unban User
                        </button>
                      </form>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminUserManagement;
