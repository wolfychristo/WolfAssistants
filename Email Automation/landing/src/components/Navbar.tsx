import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Menu, 
  X, 
  LogIn,
} from 'lucide-react';

export default function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const pathname = location.pathname;
  const appUrl = process.env.REACT_APP_APP_URL || 'https://app.wolfassistants.com';

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-50 shadow-sm">
      <div className="w-full max-w-7xl mx-auto px-4 lg:px-8">
        <div className="flex justify-between h-16 items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-3 flex-shrink-0 group"
          >
            <img 
              src={`${process.env.PUBLIC_URL || ''}/images/logo.svg`} 
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
          
          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            <Link
              to="/contacts"
              className={`text-sm font-medium transition-colors ${
                pathname === '/contacts'
                  ? 'text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Contacts
            </Link>
            <Link
              to="/features"
              className={`text-sm font-medium transition-colors ${
                pathname === '/features'
                  ? 'text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Features
            </Link>
            <Link
              to="/pricing"
              className={`text-sm font-medium transition-colors ${
                pathname === '/pricing'
                  ? 'text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Pricing
            </Link>
            <a
              href={`${appUrl}/login`}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              <LogIn className="w-4 h-4" />
              <span className="hidden sm:inline">Sign in</span>
            </a>
          </div>

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

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200 bg-white">
            <div className="space-y-1">
              <Link
                to="/contacts"
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  pathname === '/contacts'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                Contacts
              </Link>
              <Link
                to="/features"
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  pathname === '/features'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                Features
              </Link>
              <Link
                to="/pricing"
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  pathname === '/pricing'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                Pricing
              </Link>
              <a
                href={`${appUrl}/login`}
                onClick={() => setIsMobileMenuOpen(false)}
                className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <LogIn className="w-4 h-4" />
                Sign in
              </a>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
