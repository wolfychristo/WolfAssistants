import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Shield, Lock, AlertTriangle } from 'lucide-react';
import { toast } from 'react-hot-toast';

const AdminLogin: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [isValidAccess, setIsValidAccess] = useState(false);

  // Complex access code validation
  const ADMIN_ACCESS_CODE = 'WOLF_ADMIN_2024_SECURE_ACCESS';
  const ADMIN_SECRET_PHRASE = 'admin_wolf_assistants_secure_entry';

  useEffect(() => {
    // Only auto-redirect if explicitly requested via URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const autoRedirect = urlParams.get('redirect') === 'true';
    
    if (autoRedirect) {
      const token = localStorage.getItem('admin_token');
      const isAdmin = localStorage.getItem('is_admin') === 'true';
      
      if (token && isAdmin) {
        navigate('/wolf-admin-secure-2024');
      }
    }
  }, [navigate]);

  const handleAccessCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (accessCode === ADMIN_ACCESS_CODE || accessCode === ADMIN_SECRET_PHRASE) {
      setIsValidAccess(true);
      toast.success('Access granted. Please enter your admin credentials.');
    } else {
      toast.error('Invalid access code. Access denied.');
      setAccessCode('');
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast.error('Please enter both email and password');
      return;
    }

    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok && data.user?.is_admin) {
        // Store admin-specific tokens
        localStorage.setItem('admin_token', data.token);
        localStorage.setItem('admin_user', JSON.stringify(data.user));
        localStorage.setItem('is_admin', 'true');
        
        toast.success('Admin access granted');
        navigate('/wolf-admin-secure-2024');
      } else if (response.ok && !data.user?.is_admin) {
        toast.error('Access denied. Admin privileges required.');
      } else {
        toast.error(data.detail || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isValidAccess) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          {/* Security Warning */}
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6">
            <div className="flex items-center mb-2">
              <AlertTriangle className="w-5 h-5 text-red-400 mr-2" />
              <h3 className="text-red-400 font-semibold">Restricted Access</h3>
            </div>
            <p className="text-red-300 text-sm">
              This is a restricted administrative area. Unauthorized access is prohibited and monitored.
            </p>
          </div>

          {/* Access Code Form */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-8 shadow-2xl">
            <div className="text-center mb-6">
              <div className="mx-auto w-16 h-16 bg-red-600 rounded-full flex items-center justify-center mb-4">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">Admin Access Portal</h1>
              <p className="text-gray-400">Enter access code to continue</p>
            </div>

            {/* Clear Session Button */}
            <div className="mb-4 text-center">
              <button
                type="button"
                onClick={() => {
                  localStorage.removeItem('admin_token');
                  localStorage.removeItem('is_admin');
                  localStorage.removeItem('admin_user');
                  toast.success('Admin session cleared');
                }}
                className="text-sm text-gray-400 hover:text-red-400 transition-colors underline"
              >
                Clear Admin Session
              </button>
            </div>

            <form onSubmit={handleAccessCodeSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Access Code
                </label>
                <input
                  type="password"
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="Enter secure access code"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center"
              >
                <Lock className="w-5 h-5 mr-2" />
                Verify Access
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">
                This system is monitored and logged. All access attempts are recorded.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-red-900 to-black flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Admin Login Form */}
        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-8 shadow-2xl">
          <div className="text-center mb-6">
            <div className="mx-auto w-16 h-16 bg-red-600 rounded-full flex items-center justify-center mb-4">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Admin Login</h1>
            <p className="text-gray-400">Enter your administrator credentials</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Admin Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="admin@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="Enter password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Authenticating...
                </>
              ) : (
                <>
                  <Shield className="w-5 h-5 mr-2" />
                  Login as Admin
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => setIsValidAccess(false)}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              ← Back to Access Code
            </button>
          </div>

          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500">
              Admin access is logged and monitored for security purposes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
