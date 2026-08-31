import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, authAPI } from '../services/api';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<{ success: boolean; message: string }>;
  register: (userData: {
    email: string;
    password: string;
    name: string;
    businessName?: string;
    username?: string;
    company_name?: string;
    team_size?: string;
    revenue_size?: string;
    social_link?: string;
    calendly_link?: string;
    heard_about_us?: string;
    referral_code?: string;
  }) => Promise<{ success: boolean; message: string }>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    if (token) {
      // Basic token format validation before making API call
      try {
        // Check if token looks like a JWT (has 3 parts separated by dots)
        const tokenParts = token.split('.');
        if (tokenParts.length !== 3) {
          throw new Error('Invalid token format');
        }
        
        // Check if token is expired (basic check without full JWT parsing)
        const payload = JSON.parse(atob(tokenParts[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < currentTime) {
          throw new Error('Token expired');
        }
        
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        // Verify token and get user info
        authAPI.me()
          .then(response => {
            const userData = response.data;
            // Ensure id is a number
            if (userData.id) {
              userData.id = Number(userData.id);
            }
            setUser(userData);
          })
          .catch((error) => {
            // Token validation failed, clear everything silently
            // Token validation failed, clearing auth data
            setUser(null);
            localStorage.removeItem('token');
            delete api.defaults.headers.common['Authorization'];
            // Don't redirect automatically - let the user stay on current page
          })
          .finally(() => {
            setIsLoading(false);
          });
      } catch (error) {
        // Invalid token format or expired, clear it immediately
        // Invalid or expired token, clearing auth data
        setUser(null);
        localStorage.removeItem('token');
        delete api.defaults.headers.common['Authorization'];
        setIsLoading(false);
      }
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await authAPI.login({ email, password });
      
      // Check if response is successful and has the expected structure
      if (!response.data || !response.data.token || !response.data.user) {
        // Response doesn't have expected structure - treat as error
        const errorDetail = response.data?.detail || response.data?.message || 'Login failed';
        throw new Error(errorDetail);
      }
      
      const { token, user } = response.data;
      
      // Ensure id is a number
      if (user && user.id) {
        user.id = Number(user.id);
      }
      
      localStorage.setItem('token', token);
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      setUser(user);
      return { success: true, message: 'Successfully logged in' };
    } catch (error: any) {
      // Handle different types of errors
      if (error.response) {
        // Server responded with error status
        const errorDetail = error.response.data?.detail || error.response.data?.message || '';
        console.error('Login error response:', {
          status: error.response.status,
          detail: errorDetail,
          data: error.response.data
        });
        
        if (error.response.status === 401) {
          // Use the actual error message from backend if available
          const message = errorDetail || 'Wrong username or email or password';
          throw new Error(message);
        } else if (error.response.status === 400) {
          throw new Error(errorDetail || 'Invalid request');
        } else if (error.response.status === 422) {
          throw new Error(errorDetail || 'Validation error. Please check your input.');
        } else if (error.response.status >= 500) {
          throw new Error(errorDetail || 'Server error. Please try again later.');
        }
      } else if (error.request) {
        // Network error
        console.error('Login network error:', error.request);
        throw new Error('Network error. Please check your connection.');
      } else {
        // Other error
        console.error('Login error:', error);
        throw new Error(error.message || 'Login failed. Please try again.');
      }
      // This line should never be reached, but TypeScript needs it
      throw error;
    }
  };

  const register = async (userData: {
    email: string;
    password: string;
    name: string;
    businessName?: string;
    username?: string;
    company_name?: string;
    team_size?: string;
    revenue_size?: string;
    social_link?: string;
    calendly_link?: string;
    heard_about_us?: string;
    referral_code?: string;
  }) => {
    try {
      const response = await authAPI.register(userData);
      const { token, user } = response.data;
      
      localStorage.setItem('token', token);
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      setUser(user);
      // Set flag to indicate this is a new user registration (for showing tour)
      localStorage.setItem('is_new_user', 'true');
      return { success: true, message: 'Successfully registered' };
    } catch (error: any) {
      // Handle different types of errors
      if (error.response) {
        // Server responded with error status
        if (error.response.status === 400) {
          if (error.response.data?.detail?.includes('already exists')) {
            throw new Error('Email already exists. Please use a different email.');
          }
          throw new Error(error.response.data?.detail || 'Invalid request');
        } else if (error.response.status >= 500) {
          throw new Error('Server error. Please try again later.');
        }
      } else if (error.request) {
        // Network error
        throw new Error('Network error. Please check your connection.');
      } else {
        // Other error
        throw new Error('Registration failed. Please try again.');
      }
      // This line should never be reached, but TypeScript needs it
      throw error;
    }
  };

  const logout = () => {
    // Clear chat session data for the current user
    if (user?.email) {
      localStorage.removeItem(`wolfy_last_session_${user.email}`);
    }
    
    localStorage.removeItem('token');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
  };

  const value = {
    user,
    login,
    register,
    logout,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
