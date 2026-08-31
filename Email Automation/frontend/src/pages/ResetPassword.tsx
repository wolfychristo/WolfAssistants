import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';

const ResetPassword: React.FC = () => {
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [sent, setSent] = useState(false);
  const [step, setStep] = useState<'request' | 'verify' | 'reset'>('request');
  const token = params.get('token') || '';

  const sendResetLink: React.FormEventHandler = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.forgotPassword(email);
      
      // Handle the new API response structure
      if (response.data && response.data.exists === false) {
        toast.error('This email is not registered in our system');
        return;
      }
      
      if (response.data && response.data.link_sent === true) {
        toast.success('Password reset link has been sent to your email');
        setSent(true);
      } else {
        toast.error('Reset link generated but failed to send email. Please try again later.');
      }
    } catch {
      toast.error('Failed to send reset link');
    }
  };

  const resetPassword: React.FormEventHandler = async (e) => {
    e.preventDefault();
    
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters long');
      return;
    }
    
    try {
      await authAPI.resetPassword(token, newPassword);
      toast.success('Password updated');
      window.location.href = '/login';
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to reset password');
    }
  };

  // OTP flow handlers
  const requestOtp: React.FormEventHandler = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.forgotPasswordOtp(email);
      
      // Handle the new API response structure
      if (response.data && response.data.exists === false) {
        toast.error('This email is not registered in our system');
        return;
      }
      
      if (response.data && response.data.otp_sent === true) {
        toast.success('OTP has been sent to the email ID');
        setStep('verify');
      } else {
        toast.error('OTP generated but failed to send email. Please try again later.');
      }
    } catch {
      toast.error('Failed to send OTP');
    }
  };

  const verifyOtp: React.FormEventHandler = async (e) => {
    e.preventDefault();
    
    // Validate OTP format (6 alphanumeric characters)
    if (!otp || otp.length !== 6 || !/^[a-zA-Z0-9]+$/.test(otp)) {
      toast.error('Please enter a valid 6-character OTP (letters and numbers only)');
      return;
    }
    
    try {
      await authAPI.verifyResetOtp(email, otp);
      toast.success('OTP verified');
      setStep('reset');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Invalid or expired OTP');
    }
  };

  const resetWithOtp: React.FormEventHandler = async (e) => {
    e.preventDefault();
    
    // Validate OTP format again before password reset
    if (!otp || otp.length !== 6 || !/^[a-zA-Z0-9]+$/.test(otp)) {
      toast.error('Please enter a valid 6-character OTP (letters and numbers only)');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters long');
      return;
    }
    
    try {
      await authAPI.resetPasswordOtp({ email, otp, new_password: newPassword, confirm_password: confirmPassword });
      toast.success('Password updated');
      window.location.href = '/login';
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to reset password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 bg-white p-6 rounded-lg shadow">
        {!token ? (
          <div className="space-y-6">
            {step === 'request' && (
              <form onSubmit={requestOtp} className="space-y-4" aria-label="Request OTP form" title="Request OTP">
                <h2 className="text-xl font-semibold text-gray-900">Forgot Password</h2>
                <input type="email" required placeholder="Your email" value={email} onChange={(e)=>setEmail(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                <button type="submit" className="w-full py-2 bg-brand-red text-white rounded-lg hover:bg-primary-600">Send OTP</button>
                <div className="text-sm text-gray-500">Prefer a link? <button type="button" className="text-brand-red hover:underline" onClick={sendResetLink}>Send reset link</button></div>
                {sent && <p className="text-sm text-gray-600">Check your email for the reset link.</p>}
              </form>
            )}
            {step === 'verify' && (
              <form onSubmit={verifyOtp} className="space-y-4" aria-label="Verify OTP form" title="Verify OTP">
                <h2 className="text-xl font-semibold text-gray-900">Enter OTP</h2>
                <p className="text-sm text-gray-600">Enter the 6-character code sent to your email (letters and numbers)</p>
                <input type="text" inputMode="text" pattern="[a-zA-Z0-9]*" required placeholder="6-character OTP" value={otp} onChange={(e)=>setOtp(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                <div className="flex gap-2">
                  <button type="button" onClick={()=>setStep('request')} className="w-1/2 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">Back</button>
                  <button type="submit" className="w-1/2 py-2 bg-brand-red text-white rounded-lg hover:bg-primary-600">Verify</button>
                </div>
              </form>
            )}
            {step === 'reset' && (
              <form onSubmit={resetWithOtp} className="space-y-4" aria-label="Reset with OTP form" title="Reset password">
                <h2 className="text-xl font-semibold text-gray-900">Set New Password</h2>
                <input type="password" required placeholder="New password (min 6 characters)" value={newPassword} onChange={(e)=>setNewPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                <input type="password" required placeholder="Confirm new password" value={confirmPassword} onChange={(e)=>setConfirmPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                <div className="flex gap-2">
                  <button type="button" onClick={()=>setStep('verify')} className="w-1/2 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">Back</button>
                  <button type="submit" className="w-1/2 py-2 bg-brand-red text-white rounded-lg hover:bg-primary-600">Reset password</button>
                </div>
              </form>
            )}
          </div>
        ) : (
          <form onSubmit={resetPassword} className="space-y-4" aria-label="Reset password form" title="Reset password">
            <h2 className="text-xl font-semibold text-gray-900">Set New Password</h2>
            <input type="password" required placeholder="New password (min 6 characters)" value={newPassword} onChange={(e)=>setNewPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <button type="submit" className="w-full py-2 bg-brand-red text-white rounded-lg hover:bg-primary-600">Reset password</button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPassword;