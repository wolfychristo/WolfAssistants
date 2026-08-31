import React from 'react';
import { useQuery } from 'react-query';
import { 
  Users, 
  Mail, 
  Calendar, 
  TrendingUp
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useEmailConfig } from '../contexts/EmailConfigContext';
import { useTimezone } from '../contexts/TimezoneContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { contactsAPI, emailsAPI, meetingsAPI } from '../services/api';
import toast from 'react-hot-toast';
import MeetingReminders from '../components/MeetingReminders';
import TodoList from '../components/TodoList';
import RecentContacts from '../components/RecentContacts';
import RecentEmails from '../components/RecentEmails';

// Minimal country->timezone mapping (can be expanded)
const countryToTimezone: { code: string; name: string; tz: string }[] = [
  { code: 'US', name: 'United States', tz: 'America/New_York' },
  { code: 'GB', name: 'United Kingdom', tz: 'Europe/London' },
  { code: 'DE', name: 'Germany', tz: 'Europe/Berlin' },
  { code: 'FR', name: 'France', tz: 'Europe/Paris' },
  { code: 'IN', name: 'India', tz: 'Asia/Kolkata' },
  { code: 'AE', name: 'United Arab Emirates', tz: 'Asia/Dubai' },
  { code: 'AU', name: 'Australia', tz: 'Australia/Sydney' },
  { code: 'JP', name: 'Japan', tz: 'Asia/Tokyo' },
  { code: 'CN', name: 'China', tz: 'Asia/Shanghai' },
  { code: 'SG', name: 'Singapore', tz: 'Asia/Singapore' },
  { code: 'ZA', name: 'South Africa', tz: 'Africa/Johannesburg' },
  { code: 'BR', name: 'Brazil', tz: 'America/Sao_Paulo' },
  { code: 'CA', name: 'Canada', tz: 'America/Toronto' },
];

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { timeZone, setTimeZone } = useTimezone();
  const { setCountry } = useCurrency() as any;
  const { isLoading } = useEmailConfig();

  // Fetch dashboard data
  const { data: contacts, refetch: refetchContacts } = useQuery('contacts', contactsAPI.getAll);
  const { data: emailsRes } = useQuery('emails', () => emailsAPI.getAll(), {
    retry: 1,
    onError: (error) => {
      // Silent error handling for production
    }
  });
  const { data: meetings } = useQuery('meetings', meetingsAPI.getAll);
  const { data: responseRateData } = useQuery('responseRate', emailsAPI.getResponseRate, {
    retry: 1,
    onError: (error) => {
      // Silent error handling for production
    }
  });

  const contactsArr = Array.isArray(contacts?.data) ? (contacts!.data as any[]) : [];
  const emailsArr = Array.isArray(emailsRes?.data) ? (emailsRes!.data as any[]) : [];
  const meetingsArr = Array.isArray(meetings?.data) ? (meetings!.data as any[]) : [];

  // Safe email filtering with fallback
  const getEmailsSentCount = () => {
    try {
      if (!Array.isArray(emailsArr)) {
        return 0;
      }
      return emailsArr.filter((e: any) => (e.status || '').toLowerCase() === 'sent').length || 0;
    } catch (error) {
      return 0;
    }
  };

  const handleGenerateAndSend = async () => {
    try {
      // Check if user is authenticated
      if (!user) {
        toast.error('Please log in to generate emails');
        window.location.href = '/';
        return;
      }
      
      // Check if user has a valid token
      const token = localStorage.getItem('token');
      if (!token) {
        toast.error('Authentication token missing. Please log in again.');
        window.location.href = '/';
        return;
      }

      // Check if there are contacts to send emails to
      if (!contactsArr || contactsArr.length === 0) {
        toast.error('No contacts found. Please add contacts first before generating emails.');
        return;
      }

      // Check backend connectivity first
      try {
        const healthCheck = await fetch('/api/v1/emails/health', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (!healthCheck.ok) {
          throw new Error(`Backend health check failed: ${healthCheck.status} ${healthCheck.statusText}`);
        }
      } catch (healthError) {
        toast.error('Cannot connect to backend server. Please ensure the backend is running on localhost:8000');
        return;
      }
      
      // Show loading state
      const loadingToast = toast.loading('Generating and sending emails...');
      
      // Call the emails API to generate and send emails for contacts
      const response = await emailsAPI.generateAndSend();
      
      // Close loading toast
      toast.dismiss(loadingToast);
      
      if (response?.data?.results) {
        const results = response.data.results;
        const summary = response.data.summary;
        
        // Use summary if available, otherwise calculate from results
        const sentCount = summary?.sent || results.filter((r: any) => r.status === 'sent').length;
        const errorCount = summary?.errors || results.filter((r: any) => r.status === 'error').length;
        const skippedCount = summary?.skipped || response.data.skipped || 0;
        const warningCount = summary?.warnings || results.filter((r: any) => r.status === 'warning').length;
        const totalContacts = response.data.total_contacts || 0;
        const processed = response.data.processed || 0;
        
        // Only show success if emails were actually sent
        if (sentCount > 0) {
          let message = `Successfully sent ${sentCount} email(s). `;
          if (skippedCount > 0) {
            message += `${skippedCount} contact(s) already had emails sent. `;
          }
          if (warningCount > 0) {
            message += `${warningCount} email(s) used fallback templates. `;
          }
          if (errorCount > 0) {
            message += `${errorCount} email(s) failed to send.`;
          }
          toast.success(message.trim());
        } else if (errorCount > 0 && sentCount === 0) {
          // All emails failed
          toast.error(`Failed to send emails. ${errorCount} email(s) failed to send.`);
        } else if (skippedCount > 0 && sentCount === 0) {
          // All were skipped
          toast(`${skippedCount} contact(s) already had emails sent. No new emails generated.`, {
            icon: 'ℹ️',
            style: { color: "#2563eb" }
          });
        } else if (processed === 0 && totalContacts === 0) {
          // No contacts
          toast.error('No contacts found. Please add contacts before generating emails.');
        } else {
          // No action taken
          toast('No emails were generated or sent.', {
            icon: 'ℹ️',
            style: { color: "#2563eb" }
          });
        }
        
        // Refresh data using React Query instead of page reload
        await refetchContacts();
        
      } else if (response?.data?.message) {
        // Handle special messages
        const message = response.data.message;
        
        // Check if it's an error message
        if (response.data.error || 
            message.toLowerCase().includes('error') || 
            message.toLowerCase().includes('failed') ||
            message.toLowerCase().includes('not configured') ||
            message.toLowerCase().includes('no contacts')) {
          toast.error(message);
        } else if (message.toLowerCase().includes('no contacts')) {
          toast.error(message);
        } else {
          // Only show success if it's actually a success
          if (message.toLowerCase().includes('sent') || message.toLowerCase().includes('success')) {
            toast.success(message);
          } else {
            toast(message, {
              icon: 'ℹ️',
              style: { color: "#2563eb" }
            });
          }
        }
      } else {
        // No response data - don't show generic success
        toast.error('No response from server. Please check backend logs.');
      }
      
    } catch (error: any) {
      let errorMessage = 'Failed to generate/send emails';
      let showEmailConfigHelp = false;
      
      // Handle specific error types
      if (error?.response?.status === 401) {
        errorMessage = 'Authentication failed. Please log in again.';
        // Redirect to login
        localStorage.removeItem('token');
        window.location.href = '/';
        return;
      } else if (error?.response?.status === 400) {
        // Check if it's an email configuration issue
        if (error?.response?.data?.detail?.includes('SMTP') || 
            error?.response?.data?.detail?.includes('email') ||
            error?.response?.data?.detail?.includes('configuration')) {
          errorMessage = 'Email server configuration is missing or invalid. Please configure your email settings in Profile.';
          showEmailConfigHelp = true;
        } else {
          errorMessage = error.response.data.detail || 'Invalid request - please check your configuration';
        }
      } else if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error?.message) {
        errorMessage = error.message;
      }
      
      // Handle network/CORS errors
      if (error?.message?.includes('Network Error') || error?.code === 'ERR_NETWORK') {
        errorMessage = 'Network error - please check if the backend server is running on localhost:8000';
      }
      
      // Handle timeout errors
      if (error?.code === 'ECONNABORTED') {
        errorMessage = 'Request timed out - the backend may be slow or unreachable';
      }
      
      // Show error message
      toast.error(errorMessage);
      
      // Show additional help for email configuration issues
      if (showEmailConfigHelp) {
        setTimeout(() => {
          const confirmed = window.confirm(
            'Would you like to go to your Profile page to configure email settings now?'
          );
          if (confirmed) {
            window.location.href = '/profile';
          }
        }, 2000);
      }
    }
  };

  const stats = [
    {
      title: 'Total Contacts',
      value: contactsArr.length || 0,
      icon: Users,
      color: 'bg-brand-red',
    },
    {
      title: 'Emails Sent',
      value: getEmailsSentCount(),
      icon: Mail,
      color: 'bg-brand-red',
    },
    {
      title: 'Upcoming Meetings',
      value: Array.isArray(meetingsArr) ? meetingsArr.filter((m: any) => m.start_time && new Date(m.start_time) > new Date()).length : 0,
      icon: Calendar,
      color: 'bg-brand-red',
    },
    {
      title: 'Response Rate',
      value: responseRateData?.data?.responseRate || '0%',
      icon: TrendingUp,
      color: 'bg-brand-red',
    },
  ];

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 pt-20 quick-tour-dashboard">
        {/* Header */}
        <div className="rounded-lg border border-gray-200 shadow-sm p-6">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Welcome back, {user?.name}! 👋
              </h1>
              <p className="text-gray-600">
                Here's what's happening with your AI-assisted email today
              </p>
            </div>
        
         {/* Actions */}
         <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 w-full lg:w-auto">
           <div className="flex items-center gap-3">
             <select
               className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
               aria-label="Select country to set default timezone and currency"
               title="Select Country"
               value={countryToTimezone.find(c => c.tz === timeZone)?.code || ''}
               onChange={(e) => {
                 const found = countryToTimezone.find(c => c.code === e.target.value);
                 if (found) {
                   setTimeZone(found.tz);
                   setCountry(e.target.value);
                   toast.success(`Timezone updated to ${found.tz}`);
                 }
               }}
             >
               <option value="">Select Country</option>
               {countryToTimezone.map(c => (
                 <option key={c.code} value={c.code}>{c.name} ({c.tz})</option>
               ))}
             </select>
           </div>
           <div className="flex flex-col sm:flex-row gap-4">
             <button 
               onClick={() => {
                 const contactCount = contactsArr.length;
                 if (contactCount === 0) {
                   toast.error('No contacts found. Please add contacts first.');
                   return;
                 }
                 
                 const confirmed = window.confirm(
                   `This will generate and send personalized emails to ${contactCount} contact(s). Are you sure you want to continue?`
                 );
                 
                 if (confirmed) {
                   handleGenerateAndSend();
                 }
               }} 
               className="flex items-center justify-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all text-sm quick-tour-generate-email" 
               aria-label="Generate and send emails" 
               title="Generate and send emails"
             >
               <span>Generate & Send Emails</span>
             </button>
           </div>
           
           {/* Email Configuration Help */}
           {isLoading && (
             <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
               <div className="flex items-center gap-3">
                 <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                 <span className="text-sm text-blue-800">Checking email configuration...</span>
               </div>
             </div>
           )}
         </div>
         </div>
       </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, index) => {
            const IconComponent = stat.icon;
            const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500'];
            return (
              <div 
                key={index} 
                className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {stat.value}
                    </p>
                  </div>
                  <div className={`p-3 rounded-lg ${colors[index]} text-white`}>
                    <IconComponent className="w-6 h-6" aria-hidden="true" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

      {/* Meeting Reminders and Tasks */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <MeetingReminders />
        <TodoList />
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-8 sm:pb-12">
        <RecentContacts />
        <RecentEmails />
      </div>
      </div>
    </div>
  );
};

export default Dashboard;