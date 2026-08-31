import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Menu, 
  X, 
  LogOut,
  User,
  Settings,
  LogIn,
  PlayCircle
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTour } from '../contexts/TourContext';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { startTour } = useTour();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const navigation = [
    { name: 'Command Center', href: '/dashboard', icon: '🤖' },
    { name: 'ICP Builder', href: '/icp-builder', icon: '🎯' },
    { name: 'Prospects', href: '/contacts', icon: '👥' },
    { name: 'Conversations', href: '/conversations', icon: '💬' },
    { name: 'Pipeline', href: '/pipeline', icon: '📊' },
    { name: 'Emails', href: '/emails', icon: '✉️' },
    { name: 'Meetings', href: '/meetings', icon: '📅' },
  ];

  const handleLogout = () => {
    logout();
    setIsUserMenuOpen(false);
  };

  const handleProfileClick = () => {
    setIsUserMenuOpen(false);
  };

  const handleHomeClick = (e: React.MouseEvent) => {
    if (user) {
      e.preventDefault();
      navigate('/dashboard');
    }
  };

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-50 shadow-sm">
      <div className="w-full max-w-[1400px] mx-auto px-4 lg:px-8">
        <div className="flex justify-between h-16 items-center gap-4">
          {!user && (
            <Link
              to="/"
              className="flex items-center gap-3 flex-shrink-0 group"
              onClick={handleHomeClick}
            >
              <img 
                src="/images/logo.svg" 
                alt="WolfAssistants Logo" 
                className="h-10 w-auto"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                  const fallback = (e.target as HTMLImageElement).nextElementSibling as HTMLElement;
                  if (fallback) fallback.style.display = 'flex';
                }}
              />
              <div className="w-8 h-8 bg-blue-600 flex items-center justify-center rounded-lg group-hover:bg-blue-700 transition-colors hidden">
                <span className="text-white font-bold text-lg leading-none">W</span>
              </div>
              <span className="text-xl font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">WolfAssistants</span>
            </Link>
          )}
          
          {/* Desktop Navigation - Expanded full width when user is authenticated */}
          {user && (
            <div className="hidden md:flex items-center space-x-2 flex-1 justify-start overflow-x-auto py-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center gap-2 px-3.5 py-2 text-sm font-medium transition-all duration-200 whitespace-nowrap rounded-lg ${
                      isActive
                        ? 'bg-blue-50 text-blue-600 font-semibold shadow-sm'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                    title={item.name}
                  >
                    <span className="text-base" aria-label={item.name}>{item.icon}</span>
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          )}

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {!user ? (
              // Show login button when user is not authenticated
              <Link
                to="/login"
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              >
                <LogIn className="w-4 h-4" />
                <span className="hidden sm:inline">Sign in</span>
              </Link>
            ) : (
              // Show user menu when authenticated
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center space-x-2 px-2 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors duration-200"
                >
                  {user?.profile_image_url ? (
                    <img src={user.profile_image_url} alt="Profile" className="w-8 h-8 rounded-full object-cover border-2 border-gray-200" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-600" />
                    </div>
                  )}
                </button>

                {/* User Dropdown */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-52 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                    <button
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        startTour();
                      }}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-200"
                    >
                      <PlayCircle className="w-4 h-4" />
                      Take Quick Tour
                    </button>
                    <Link
                      to="/profile"
                      onClick={handleProfileClick}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-200"
                    >
                      <Settings className="w-4 h-4" />
                      Profile & Settings
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-200"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Mobile menu button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors duration-200"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation - Only show when user is authenticated */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200 bg-white">
            <div className="space-y-1">
              {user && navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-colors duration-200 ${
                      isActive
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <span>{item.icon}</span>
                    {item.name}
                  </Link>
                );
              })}
              {!user && (
                <Link
                  to="/login"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors duration-200"
                >
                  <LogIn className="w-4 h-4" />
                  Sign in
                </Link>
              )}
              {user && (
                <>
                  <button
                    onClick={() => {
                      setIsMobileMenuOpen(false);
                      startTour();
                    }}
                    className="flex items-center gap-2 w-full px-4 py-3 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors duration-200"
                  >
                    <PlayCircle className="w-4 h-4" />
                    Take Quick Tour
                  </button>
                  <Link
                    to="/profile"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors duration-200"
                  >
                    <Settings className="w-4 h-4" />
                    Profile & Settings
                  </Link>
                </>
              )}
              
              {/* Legal Links for Mobile */}
              <div className="border-t border-gray-200 pt-4 mt-4">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-4">Legal</div>
                <Link
                  to="/terms"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors duration-200"
                >
                  Terms & Conditions
                </Link>
                <Link
                  to="/privacy"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors duration-200"
                >
                  Privacy Policy
                </Link>
                <Link
                  to="/returns"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors duration-200"
                >
                  Return Policy
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;