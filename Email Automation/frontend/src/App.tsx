import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './components/LandingPage';
import { TrialBanner } from './components/TrialBanner';
import Dashboard from './pages/Dashboard';
import Contacts from './pages/Contacts';
import Emails from './pages/Emails';
import Meetings from './pages/Meetings';
import ResetPassword from './pages/ResetPassword';
import Invoices from './pages/Invoices';
import Profile from './pages/Profile';
import Login from './pages/Login';
import PricingPage from './pages/PricingPage';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { EmailConfigProvider } from './contexts/EmailConfigContext';
import { TimezoneProvider } from './contexts/TimezoneContext';
import { CurrencyProvider } from './contexts/CurrencyContext';
import { TourProvider, useTour } from './contexts/TourContext';
import QuickTour from './components/QuickTour';
import WolfyPage from './pages/Wolfy';
import ScrapedLeads from './pages/ScrapedLeads';
import TermsAndConditions from './pages/TermsAndConditions';
import PrivacyPolicy from './pages/PrivacyPolicy';
import ReturnPolicy from './pages/ReturnPolicy';
import AdminDashboard from './pages/AdminDashboard';
import AdminFeedbackDashboard from './pages/AdminFeedbackDashboard';
import AdminLogin from './pages/AdminLogin';
import SecureAdminLogin from './pages/SecureAdminLogin';
import SecureAdminDashboard from './pages/SecureAdminDashboard';
import ICPBuilderPage from './pages/ICPBuilderPage';
import ConversationsPage from './pages/ConversationsPage';
import PipelinePage from './pages/PipelinePage';
import DeleteAccount from './pages/DeleteAccount';
import AdminProtectedRoute from './components/AdminProtectedRoute';

import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2, // Retry failed requests twice
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false, // Don't refetch on window focus to avoid unnecessary requests
    },
    mutations: {
      retry: 1, // Retry failed mutations once
      retryDelay: 1000, // Wait 1 second before retry
    },
  },
});

// Component to conditionally render landing page or redirect to dashboard
const ConditionalLandingPage: React.FC = () => {
  const { user } = useAuth();
  
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <LandingPage />;
};

// Component to handle tour logic
const AppWithTour: React.FC = () => {
  const { showTour, completeTour, skipTour } = useTour();

  return (
              <Router>
                <div className="App">
                  <Navbar />
                  <TrialBanner />
                  <Routes>
                    {/* Public routes */}
                    <Route path="/" element={<ConditionalLandingPage />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/reset-password" element={<ResetPassword />} />
                    <Route path="/pricing" element={<PricingPage />} />
                    <Route path="/terms" element={<TermsAndConditions />} />
                    <Route path="/privacy" element={<PrivacyPolicy />} />
                    <Route path="/returns" element={<ReturnPolicy />} />
                    
                    {/* Protected routes */}
                    <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                    <Route path="/icp-builder" element={<ProtectedRoute><ICPBuilderPage /></ProtectedRoute>} />
                    <Route path="/conversations" element={<ProtectedRoute><ConversationsPage /></ProtectedRoute>} />
                    <Route path="/pipeline" element={<ProtectedRoute><PipelinePage /></ProtectedRoute>} />
                    <Route path="/contacts" element={<ProtectedRoute><Contacts /></ProtectedRoute>} />
                    <Route path="/contacts/:publicId" element={<ProtectedRoute><Contacts /></ProtectedRoute>} />
                    <Route path="/emails" element={<ProtectedRoute><Emails /></ProtectedRoute>} />
                    <Route path="/emails/:publicId" element={<ProtectedRoute><Emails /></ProtectedRoute>} />
                    <Route path="/meetings" element={<ProtectedRoute><Meetings /></ProtectedRoute>} />
                    <Route path="/meetings/:publicId" element={<ProtectedRoute><Meetings /></ProtectedRoute>} />
                    <Route path="/wolfy" element={<ProtectedRoute><WolfyPage /></ProtectedRoute>} />
                    <Route path="/chat/:publicId" element={<ProtectedRoute><WolfyPage /></ProtectedRoute>} />
                    <Route path="/scraped-leads" element={<ProtectedRoute><ScrapedLeads /></ProtectedRoute>} />
                    <Route path="/invoices" element={<ProtectedRoute><Invoices /></ProtectedRoute>} />
                    <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
                    {/* Secret Admin Routes - Complex URLs for security */}
                    <Route path="/admin-login" element={<AdminLogin />} />
                    <Route path="/secure-admin-login" element={<SecureAdminLogin />} />
                    <Route path="/wolf-admin-secure-2024" element={<AdminProtectedRoute><AdminDashboard /></AdminProtectedRoute>} />
                    <Route path="/wolf-admin-secure-2024/feedback" element={<AdminProtectedRoute><AdminFeedbackDashboard /></AdminProtectedRoute>} />
                    <Route path="/secure-admin-dashboard" element={<SecureAdminDashboard />} />
                    <Route path="/delete-account" element={<ProtectedRoute><DeleteAccount /></ProtectedRoute>} />
                    
                    {/* Default redirect */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                  <Toaster position="top-right" />
        <QuickTour 
          run={showTour} 
          onComplete={completeTour}
          onSkip={skipTour}
        />
                </div>
              </Router>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TourProvider>
          <EmailConfigProvider>
            <TimezoneProvider>
              <CurrencyProvider>
                <AppWithTour />
            </CurrencyProvider>
          </TimezoneProvider>
        </EmailConfigProvider>
        </TourProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
