import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { useEmailConfig, EmailConfig } from '../contexts/EmailConfigContext';
import toast from 'react-hot-toast';
import PlaceholderImage from '../components/PlaceholderImage';
import DeliverabilityDashboard from '../components/DeliverabilityDashboard';

// Password Reset Flow Component
const PasswordResetFlow: React.FC = () => {
  const [step, setStep] = useState<'email' | 'otp' | 'password' | 'complete'>('email');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      toast.error('Please enter your email address');
      return;
    }

    setLoading(true);
    try {
      const response = await authAPI.forgotPasswordOtp(email);
      if (response.data.exists && response.data.otp_sent) {
        setStep('otp');
        toast.success('OTP sent to your email address');
      } else if (!response.data.exists) {
        toast.error('This email is not registered in our system');
      } else {
        toast.error('Failed to send OTP. Please try again.');
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otp) {
      toast.error('Please enter the OTP');
      return;
    }

    setLoading(true);
    try {
      await authAPI.verifyResetOtp(email, otp);
      setStep('password');
      toast.success('OTP verified successfully');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword || !confirmPassword) {
      toast.error('Please enter both passwords');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);
    try {
      await authAPI.resetPasswordOtp({
        email,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword
      });
      setStep('complete');
      toast.success('Password reset successfully!');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  const resetFlow = () => {
    setStep('email');
    setEmail('');
    setOtp('');
    setNewPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="rounded-lg shadow p-12 mt-6 w-full max-w-7xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Reset Password</h2>
      
      {/* Step 1: Email Input */}
      {step === 'email' && (
        <div>
          <p className="text-gray-600 mb-6">Enter your email address to receive a password reset OTP.</p>
          <form onSubmit={handleEmailSubmit} className="max-w-md">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your email address"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
            >
              {loading ? 'Sending...' : 'Send OTP'}
            </button>
          </form>
        </div>
      )}

      {/* Step 2: OTP Input */}
      {step === 'otp' && (
        <div>
          <p className="text-gray-600 mb-6">
            We've sent a 6-character alphanumeric OTP to <strong>{email}</strong>. Please enter it below.
            <br />
            <span className="text-sm text-gray-500">Format: 2 numbers, 2 uppercase letters, 2 lowercase letters (e.g., 12AbCd)</span>
          </p>
          <form onSubmit={handleOtpSubmit} className="max-w-md">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                OTP Code
              </label>
              <input
                type="text"
                value={otp}
                onChange={(e) => {
                  // Allow alphanumeric characters and limit to 6 characters
                  const value = e.target.value.replace(/[^a-zA-Z0-9]/g, '').slice(0, 6);
                  setOtp(value);
                }}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-2xl tracking-widest"
                placeholder="12AbCd"
                maxLength={6}
                required
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={resetFlow}
                className="flex-1 px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
              >
                {loading ? 'Verifying...' : 'Verify OTP'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Step 3: New Password */}
      {step === 'password' && (
        <div>
          <p className="text-gray-600 mb-6">Enter your new password below.</p>
          <form onSubmit={handlePasswordSubmit} className="max-w-md">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter new password"
                minLength={8}
                required
              />
            </div>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Confirm New Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Confirm new password"
                minLength={8}
                required
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep('otp')}
                className="flex-1 px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading || !newPassword || !confirmPassword}
                className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60"
              >
                {loading ? 'Resetting...' : 'Reset Password'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Step 4: Success */}
      {step === 'complete' && (
        <div className="text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Password Reset Successful!</h3>
          <p className="text-gray-600 mb-6">Your password has been successfully updated.</p>
          <button
            onClick={resetFlow}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Reset Another Password
          </button>
        </div>
      )}
    </div>
  );
};

const Profile: React.FC = () => {
  const [form, setForm] = useState<{
    name: string;
    username: string;
    company_name: string;
    team_size: string;
    revenue_size: string;
    social_link: string;
    calendly_link: string;
    profile_image_url: string;
    email?: string;
  }>({
    name: '',
    username: '',
    company_name: '',
    team_size: '',
    revenue_size: '',
    social_link: '',
    calendly_link: '',
    profile_image_url: ''
  });
  const [loading, setLoading] = useState(false);
  const { 
    emailConfig, 
    updateEmailConfig
  } = useEmailConfig();  // Local state for email form updates
  const [localEmailCfg, setLocalEmailCfg] = useState<EmailConfig>({
    smtp_host: '',
    smtp_port: undefined,
    smtp_username: '',
    smtp_password: '',
    smtp_from: '',
    smtp_use_tls: true,
    imap_host: '',
    imap_port: undefined,
    imap_username: '',
    imap_password: '',
    imap_use_ssl: true,
    auto_followup_enabled: false,
    auto_followup_max_days: 14,
    auto_followup_daily_hour: 9
  });

  // Sync local state with context when it loads
  useEffect(() => {
    if (emailConfig) {
      setLocalEmailCfg(emailConfig);
    }
  }, [emailConfig]);

  const handleEmailCfgUpdate = (field: keyof EmailConfig, value: any) => {
    setLocalEmailCfg(prev => ({ ...prev, [field]: value }));
  };

  const handleSaveEmailCfg = async () => {
    if (await updateEmailConfig(localEmailCfg)) {
      // Config saved successfully - no need to reload since we just saved it
      // Email configuration saved successfully
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await authAPI.me();
        setForm((prevForm: typeof form) => ({ 
          ...prevForm, 
          ...res.data,
          social_link: res.data.website_url || res.data.social_link || '' // Load website_url into social_link
        }));
      } catch {
        toast.error('Failed to load profile');
      }
    })();
  }, []);

  const save = async () => {
    try {
      setLoading(true);
      await authAPI.updateProfile({
        full_name: form.name,
        username: form.username,
        company_name: form.company_name,
        team_size: form.team_size,
        revenue_size: form.revenue_size,
        social_link: form.social_link,
        website_url: form.social_link, // Map social_link to website_url for backend
        calendly_link: form.calendly_link,
        profile_image_url: form.profile_image_url,
      });
      toast.success('Profile updated');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 pt-20">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Admin Profile</h1>

      {/* Profile card */}
      <div className="bg-white rounded-lg shadow p-12 w-full max-w-7xl">
        <div className="flex items-start gap-8">
          {/* Avatar + upload */}
          <div>
            {form.profile_image_url ? (
              <img src={form.profile_image_url} alt="Profile avatar" className="w-28 h-28 rounded-full object-cover border" />
            ) : (
              <PlaceholderImage size={112} className="w-28 h-28 rounded-full object-cover border" alt="Profile avatar" />
            )}
            <div className="mt-3 flex items-center gap-3">
              <input
                type="file"
                accept="image/*"
                onChange={(e)=>{
                  const file = e.target.files && e.target.files[0];
                  if (!file) return;
                  if (!file.type.startsWith('image/')) { toast.error('Please upload an image'); return; }
                  const reader = new FileReader();
                  reader.onload = () => setForm({...form, profile_image_url: String(reader.result || '')});
                  reader.readAsDataURL(file);
                }}
                className="block w-full text-sm"
                aria-label="Upload profile image"
                title="Upload profile image"
              />
              {form.profile_image_url ? (
                <button type="button" className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200" onClick={()=>setForm({...form, profile_image_url: ''})}>Remove</button>
              ) : null}
            </div>
          </div>

          {/* Form fields */}
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.name || ''} onChange={(e)=>setForm({...form, name:e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.username || ''} onChange={(e)=>setForm({...form, username:e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.company_name || ''} onChange={(e)=>setForm({...form, company_name:e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Team Size</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.team_size || ''} onChange={(e)=>setForm({...form, team_size:e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Revenue Size</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.revenue_size || ''} onChange={(e)=>setForm({...form, revenue_size:e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Website / Portfolio URL</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.social_link || ''} onChange={(e)=>setForm({...form, social_link:e.target.value})} placeholder="https://yourwebsite.com" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Calendly Link</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg" value={form.calendly_link || ''} onChange={(e)=>setForm({...form, calendly_link:e.target.value})} placeholder="https://calendly.com/yourlink" />
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-between">
          <button
            onClick={save}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Email setup card */}
      <div className="bg-white rounded-lg shadow p-12 mt-6 w-full max-w-7xl quick-tour-email-config">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Email Configuration</h2>
        <p className="text-gray-600 mb-8">Configure your business email settings for sending and receiving emails.</p>
                 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
           <p className="text-blue-800 text-sm">
             <strong>Important:</strong> All fields marked with <span className="text-red-500">*</span> are required for sending emails. 
             Password is required for email authentication.
           </p>
         </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          {/* SMTP Section */}
          <div className="mb-10">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <h3 className="text-xl font-semibold text-gray-800">SMTP Settings (Send Emails)</h3>
            </div>
            <p className="text-sm text-gray-500 mb-6">Configure your outgoing email server. Recommended settings for Hostinger: smtp.hostinger.com:587 with TLS enabled.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SMTP Host <span className="text-red-500">*</span>
                </label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="smtp.hostinger.com"
                  value={localEmailCfg.smtp_host || ''} 
                  onChange={(e) => handleEmailCfgUpdate('smtp_host', e.target.value)} 
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SMTP Port <span className="text-red-500">*</span>
                </label>
                <input 
                  type="number" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="587 or 465"
                  value={localEmailCfg.smtp_port || ''} 
                  onChange={(e) => handleEmailCfgUpdate('smtp_port', e.target.value ? Number(e.target.value) : undefined)} 
                  required
                />
              </div>
              
              <div className="flex items-center gap-3">
                <input 
                  id="smtp_tls" 
                  type="checkbox" 
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" 
                  checked={!!localEmailCfg.smtp_use_tls} 
                  onChange={(e) => handleEmailCfgUpdate('smtp_use_tls', e.target.checked)} 
                />
                <label htmlFor="smtp_tls" className="text-sm font-medium text-gray-700">Use TLS/SSL</label>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username <span className="text-red-500">*</span>
                </label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="your-email@domain.com"
                  value={localEmailCfg.smtp_username || ''} 
                  onChange={(e) => handleEmailCfgUpdate('smtp_username', e.target.value)} 
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password <span className="text-red-500">*</span>
                </label>
                <input 
                  type="password" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="Your email password"
                  value={localEmailCfg.smtp_password || ''} 
                  onChange={(e) => handleEmailCfgUpdate('smtp_password', e.target.value)} 
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  From Address <span className="text-red-500">*</span>
                </label>
                <input 
                  type="email" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="sender@domain.com"
                  value={localEmailCfg.smtp_from || ''} 
                  onChange={(e) => handleEmailCfgUpdate('smtp_from', e.target.value)} 
                  required
                />
              </div>
            </div>
            
            <div className="flex items-center gap-4 mt-6">
              <button 
                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors" 
                onClick={handleSaveEmailCfg}
              >
                Save SMTP
              </button>
            </div>
          </div>

          {/* IMAP */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <h3 className="text-xl font-semibold text-gray-800">IMAP Settings (Receive Emails)</h3>
            </div>
            <p className="text-sm text-gray-500 mb-6">Configure your incoming email server. Recommended settings for Hostinger: imap.hostinger.com:993 with SSL enabled.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">IMAP Host</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="imap.hostinger.com"
                  value={localEmailCfg.imap_host || ''} 
                  onChange={(e) => handleEmailCfgUpdate('imap_host', e.target.value)} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">IMAP Port</label>
                <input 
                  type="number" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="993 or 143"
                  value={localEmailCfg.imap_port || ''} 
                  onChange={(e) => handleEmailCfgUpdate('imap_port', e.target.value ? Number(e.target.value) : undefined)} 
                />
              </div>
              <div className="flex items-center gap-3">
                <input 
                  id="imap_ssl" 
                  type="checkbox" 
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" 
                  checked={!!localEmailCfg.imap_use_ssl} 
                  onChange={(e) => handleEmailCfgUpdate('imap_use_ssl', e.target.checked)} 
                />
                <label htmlFor="imap_ssl" className="text-sm font-medium text-gray-700">Use SSL</label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="your-email@domain.com"
                  value={localEmailCfg.imap_username || ''} 
                  onChange={(e) => handleEmailCfgUpdate('imap_username', e.target.value)} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
                <input 
                  type="password" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  placeholder="Your email password"
                  value={localEmailCfg.imap_password || ''} 
                  onChange={(e) => handleEmailCfgUpdate('imap_password', e.target.value)} 
                />
              </div>
            </div>
            
            <div className="flex items-center gap-4 mt-6">
              <button 
                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors" 
                onClick={handleSaveEmailCfg}
              >
                Save IMAP
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Auto Follow-ups */}
      <div className="rounded-lg shadow p-12 mt-6 w-full max-w-7xl">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Auto Follow-ups</h2>
        <p className="text-gray-600 mb-6">Automatically send a daily follow-up to contacts who haven’t replied since your last email. You can turn this off anytime.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          <div className="flex items-center gap-3">
            <label htmlFor="auto_followup_enabled" className="relative inline-flex h-6 w-11 items-center cursor-pointer select-none">
              <input
                id="auto_followup_enabled"
                type="checkbox"
                className="sr-only"
                checked={!!localEmailCfg.auto_followup_enabled}
                onChange={(e)=>handleEmailCfgUpdate('auto_followup_enabled', e.target.checked)}
              />
              <span aria-hidden className={`${localEmailCfg.auto_followup_enabled ? 'bg-green-500' : 'bg-gray-300'} absolute inset-0 rounded-full transition-colors`}></span>
              <span aria-hidden className={`${localEmailCfg.auto_followup_enabled ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform`}></span>
            </label>
            <span className="text-sm font-medium text-gray-700">Enable Auto Follow-ups</span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Days Window</label>
            <input
              type="number"
              className="w-full px-3 py-2 border rounded-lg"
              value={localEmailCfg.auto_followup_max_days ?? 14}
              onChange={(e)=>handleEmailCfgUpdate('auto_followup_max_days', e.target.value ? Number(e.target.value) : undefined)}
              min={1}
              max={60}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Hour (0–23)</label>
            <input
              type="number"
              className="w-full px-3 py-2 border rounded-lg"
              value={localEmailCfg.auto_followup_daily_hour ?? 9}
              onChange={(e)=>handleEmailCfgUpdate('auto_followup_daily_hour', e.target.value ? Number(e.target.value) : undefined)}
              min={0}
              max={23}
            />
          </div>
        </div>
        {/* Status badge */}
        <div className="mt-4 flex items-center gap-4 text-sm">
          <span className={`inline-flex items-center px-3 py-1 rounded-full ${localEmailCfg.auto_followup_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
            {localEmailCfg.auto_followup_enabled ? 'Auto Follow-ups: ON' : 'Auto Follow-ups: OFF'}
          </span>
          {localEmailCfg.last_auto_followup_run && (
            <span className="text-gray-600">Last run: {new Date(localEmailCfg.last_auto_followup_run).toLocaleString()} ({localEmailCfg.last_auto_followup_sent_count || 0} sent)</span>
          )}
          {localEmailCfg.auto_followup_enabled && typeof localEmailCfg.auto_followup_daily_hour === 'number' && (
            <span className="text-gray-600">Preferred hour: {localEmailCfg.auto_followup_daily_hour}:00</span>
          )}
        </div>
        <div className="mt-6">
          <button
            onClick={handleSaveEmailCfg}
            className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Save Auto Follow-up Settings
          </button>
        </div>
      </div>

      {/* Email Deliverability Dashboard */}
      <div className="rounded-lg shadow p-12 mt-6 w-full max-w-7xl">
        <DeliverabilityDashboard />
      </div>

      {/* Password Reset Flow */}
      <PasswordResetFlow />

      {/* Account Management card */}
      <div className="rounded-lg shadow p-12 mt-6 w-full max-w-7xl">
        <h2 className="text-lg font-semibold mb-3">Account Management</h2>
        <p className="text-sm text-gray-600 mb-6">Manage your account settings and security.</p>
        <div className="flex items-center gap-4">
          <button
            onClick={() => window.location.href = '/delete-account'}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
};

export default Profile;