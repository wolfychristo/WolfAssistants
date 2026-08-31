import React from 'react';
import { AlertCircle, Clock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';

export const TrialBanner: React.FC = () => {
  const { user } = useAuth();

  if (!user || !user.trial) {
    return null;
  }

  const { trial } = user;
  const daysRemaining = trial.days_remaining || 0;

  // Don't show banner if trial has expired or user is on paid plan
  if (trial.has_expired || (user.payment_status === 'active' && user.pricing_tier !== 'starter')) {
    return null;
  }

  // Show warning if less than 3 days remaining
  const isWarning = daysRemaining <= 3 && daysRemaining > 0;
  const isExpired = daysRemaining === 0 && trial.has_expired;

  if (isExpired) {
    return (
      <div className="bg-[#dc2626] text-white py-3 px-4 border-b border-[#dc2626]/20">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5" />
            <div>
              <span className="font-semibold">Your free trial has ended.</span>
              <span className="ml-2 text-sm opacity-90">
                Upgrade to continue using all features.
              </span>
            </div>
          </div>
          <Link
            to="/pricing"
            className="px-4 py-2 bg-white text-[#dc2626] rounded-lg font-semibold hover:bg-gray-100 transition-colors text-sm"
          >
            Upgrade Now
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={`${
      isWarning ? 'bg-[#dc2626]' : 'bg-[#0f1419] border-[#dc2626]/30'
    } text-white py-3 px-4 border-b ${
      isWarning ? 'border-[#dc2626]/20' : 'border-white/5'
    }`}>
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className={`w-5 h-5 ${isWarning ? 'text-white' : 'text-[#dc2626]'}`} />
          <div>
            <span className="font-semibold">
              {daysRemaining === 1 
                ? '1 day left in your free trial'
                : `${daysRemaining} days left in your free trial`
              }
            </span>
            {!isWarning && (
              <span className="ml-2 text-sm text-[#94a3b8]">
                Upgrade to keep all features after trial ends.
              </span>
            )}
          </div>
        </div>
        <Link
          to="/pricing"
          className={`px-4 py-2 rounded-lg font-semibold transition-colors text-sm ${
            isWarning
              ? 'bg-white text-[#dc2626] hover:bg-gray-100'
              : 'bg-[#dc2626] text-white hover:bg-[#ef4444]'
          }`}
        >
          Upgrade Now
        </Link>
      </div>
    </div>
  );
};
