import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle } from 'lucide-react';

interface AdminProtectedRouteProps {
  children: React.ReactNode;
}

const AdminProtectedRoute: React.FC<AdminProtectedRouteProps> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const checkAdminAccess = async () => {
      try {
        const adminToken = localStorage.getItem('admin_token');
        const isAdminFlag = localStorage.getItem('is_admin') === 'true';
        
        if (!adminToken || !isAdminFlag) {
          setIsAdmin(false);
          setIsLoading(false);
          return;
        }

        // Verify admin token with backend
        const response = await fetch('http://localhost:8000/api/v1/admin-auth/me', {
          headers: {
            'Authorization': `Bearer ${adminToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const userData = await response.json();
          if (userData.is_admin) {
            setIsAdmin(true);
          } else {
            // Clear invalid admin tokens
            localStorage.removeItem('admin_token');
            localStorage.removeItem('is_admin');
            setIsAdmin(false);
          }
        } else {
          // Token is invalid
          localStorage.removeItem('admin_token');
          localStorage.removeItem('is_admin');
          setIsAdmin(false);
        }
      } catch (error) {
        console.error('Admin access check failed:', error);
        setIsAdmin(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAdminAccess();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500 mx-auto mb-4"></div>
          <p className="text-white">Verifying admin access...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-gray-800 rounded-lg p-8 text-center">
          <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Access Denied</h2>
          <p className="text-gray-400 mb-6">
            You do not have administrator privileges to access this area.
          </p>
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-center mb-2">
              <AlertTriangle className="w-5 h-5 text-red-400 mr-2" />
              <span className="text-red-400 font-semibold">Security Notice</span>
            </div>
            <p className="text-red-300 text-sm">
              This access attempt has been logged for security purposes.
            </p>
          </div>
          <button
            onClick={() => window.location.href = '/admin-login'}
            className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
          >
            Go to Admin Login
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default AdminProtectedRoute;
