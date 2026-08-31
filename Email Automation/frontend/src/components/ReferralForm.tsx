/**
 * Referral Form Component
 * 
 * A beautiful, engaging form for users to invite friends and earn credits.
 */

import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface ReferralStats {
  total_invitations: number;
  successful_signups: number;
  conversion_rate: number;
  total_credits_earned: number;
  pending_invitations: number;
  recent_activity: Array<{
    email: string;
    status: string;
    created_at: string;
    credits_earned: number;
  }>;
}

interface CreditBalance {
  total_credits: number;
  available_credits: number;
  used_credits: number;
  credits_expiring_soon: number;
}

interface ReferralFormProps {
  className?: string;
}

export const ReferralForm: React.FC<ReferralFormProps> = ({ className = '' }) => {
  const [email, setEmail] = useState('');
  const [personalMessage, setPersonalMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [creditBalance, setCreditBalance] = useState<CreditBalance | null>(null);
  const [myReferralCode, setMyReferralCode] = useState('');

  // Load referral data on component mount
  useEffect(() => {
    loadReferralData();
  }, []);

  const loadReferralData = async () => {
    try {
      const [statsResponse, creditsResponse, codeResponse] = await Promise.all([
        api.get('/referrals/stats').catch(() => ({ data: null })),
        api.get('/referrals/credits/balance').catch(() => ({ data: null })),
        api.get('/referrals/my-code').catch(() => ({ data: { code: '' } }))
      ]);

      if (statsResponse.data) {
        setStats(statsResponse.data);
      }
      if (creditsResponse.data) {
        setCreditBalance(creditsResponse.data);
      }
      if (codeResponse.data && codeResponse.data.code) {
        setMyReferralCode(codeResponse.data.code);
      }
    } catch (error) {
      console.error('Failed to load referral data:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setMessage({ type: 'error', text: 'Please enter an email address' });
      return;
    }

    if (!isValidEmail(email)) {
      setMessage({ type: 'error', text: 'Please enter a valid email address' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const response = await api.post('/referrals/invite', {
        email: email.trim(),
        personal_message: personalMessage.trim() || null
      });

      setMessage({ 
        type: 'success', 
        text: `Invitation sent! You earned ${response.data.credits_earned} credits!` 
      });
      
      // Reset form
      setEmail('');
      setPersonalMessage('');
      
      // Reload data
      loadReferralData();
      
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to send invitation. Please try again.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isValidEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const copyReferralCode = async () => {
    try {
      await navigator.clipboard.writeText(myReferralCode);
      setMessage({ type: 'success', text: 'Referral code copied to clipboard!' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to copy referral code' });
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'signed_up': return 'text-green-600 bg-green-100';
      case 'opened': return 'text-blue-600 bg-blue-100';
      case 'sent': return 'text-yellow-600 bg-yellow-100';
      case 'pending': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusText = (status: string): string => {
    switch (status) {
      case 'signed_up': return 'Joined!';
      case 'opened': return 'Opened';
      case 'sent': return 'Sent';
      case 'pending': return 'Pending';
      default: return status;
    }
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm p-8 ${className}`}>
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-red-600 flex items-center justify-center mx-auto mb-4 rounded-full">
          <span className="text-4xl">🎁</span>
        </div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Invite Friends & Earn Credits
        </h2>
        <p className="text-lg text-gray-600">
          Get <span className="text-purple-600 font-bold text-xl">50 credits</span> when your friend signs up!
        </p>
      </div>

      {/* Credit Balance */}
      {creditBalance && (
        <div className="bg-gray-100 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Your Credits</p>
              <p className="text-3xl font-bold text-purple-600">
                {(creditBalance.available_credits || 0).toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600 mb-1">Total Earned</p>
              <p className="text-2xl font-bold text-gray-900">
                {(creditBalance.total_credits || 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Referral Form */}
      <form onSubmit={handleSubmit} className="space-y-6 mb-8">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Friend's Email Address
          </label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter friend's email address"
            className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            disabled={isLoading}
            required
          />
        </div>

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
            Personal Message <span className="text-gray-500 font-normal">(Optional)</span>
          </label>
          <textarea
            id="message"
            value={personalMessage}
            onChange={(e) => setPersonalMessage(e.target.value)}
            placeholder="Add a personal message to make it more engaging..."
            rows={3}
            maxLength={200}
            className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
            disabled={isLoading}
          />
          <p className="text-xs text-gray-500 mt-1 text-right">
            {personalMessage.length}/200 characters
          </p>
        </div>

        <button
          type="submit"
          disabled={isLoading || !email.trim()}
          className="w-full bg-gradient-to-r from-purple-600 to-purple-700 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-purple-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Sending Invitation...
            </span>
          ) : (
            <>
              Send Invitation! 🚀
            </>
          )}
        </button>
      </form>

      {/* Message Display */}
      {message && (
        <div className={`p-4 rounded-lg mb-6 ${
          message.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <p className="font-medium">{message.text}</p>
        </div>
      )}

      {/* My Referral Code */}
      {myReferralCode && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 mb-8">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Your Referral Code</h3>
          <div className="flex items-center gap-3">
            <code className="flex-1 bg-white px-4 py-3 rounded-lg border border-gray-300 text-lg font-bold text-gray-900">
              {myReferralCode}
            </code>
            <button
              onClick={copyReferralCode}
              className="px-4 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-all"
            >
              Copy
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            Share this code with friends or include it in your social media posts
          </p>
        </div>
      )}

      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
            <p className="text-3xl font-bold text-purple-600 mb-1">{stats.total_invitations || 0}</p>
            <p className="text-xs font-medium text-gray-600">Invitations Sent</p>
          </div>
          <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
            <p className="text-3xl font-bold text-green-600 mb-1">{stats.successful_signups || 0}</p>
            <p className="text-xs font-medium text-gray-600">Friends Joined</p>
          </div>
          <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
            <p className="text-3xl font-bold text-blue-600 mb-1">{stats.conversion_rate || 0}%</p>
            <p className="text-xs font-medium text-gray-600">Success Rate</p>
          </div>
          <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
            <p className="text-3xl font-bold text-orange-600 mb-1">{stats.total_credits_earned || 0}</p>
            <p className="text-xs font-medium text-gray-600">Credits Earned</p>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {stats && stats.recent_activity && stats.recent_activity.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-2">
            {stats.recent_activity.slice(0, 5).map((activity, index) => (
              <div key={index} className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{activity.email}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(activity.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <span className={`px-3 py-1 rounded text-xs font-medium ${
                    getStatusColor(activity.status)
                  }`}>
                    {getStatusText(activity.status)}
                  </span>
                  {activity.credits_earned > 0 && (
                    <span className="text-xs font-medium text-green-600">
                      +{activity.credits_earned} credits
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Benefits Section */}
      <div className="mt-8 pt-8 border-t border-gray-200">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">Why Your Friends Will Love WolfAssistants</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-gray-200">
            <div className="w-12 h-12 bg-purple-100 flex items-center justify-center flex-shrink-0 rounded-lg">
              <span className="text-2xl">🤖</span>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-1">AI-Powered Assistance</h4>
              <p className="text-sm text-gray-600">Save hours with smart AI-assisted email</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-gray-200">
            <div className="w-12 h-12 bg-blue-100 flex items-center justify-center flex-shrink-0 rounded-lg">
              <span className="text-2xl">📊</span>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-1">Smart Analytics</h4>
              <p className="text-sm text-gray-600">Get insights to optimize your campaigns</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-gray-200">
            <div className="w-12 h-12 bg-green-100 flex items-center justify-center flex-shrink-0 rounded-lg">
              <span className="text-2xl">🎯</span>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-1">Personalized</h4>
              <p className="text-sm text-gray-600">Tailored recommendations for your industry</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border border-gray-200">
            <div className="w-12 h-12 bg-orange-100 flex items-center justify-center flex-shrink-0 rounded-lg">
              <span className="text-2xl">⚡</span>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-1">Easy Setup</h4>
              <p className="text-sm text-gray-600">Get started in minutes, not hours</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReferralForm;
