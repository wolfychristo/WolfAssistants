import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { shouldShowTour, markTourCompleted, resetTour } from '../components/QuickTour';
import { useAuth } from './AuthContext';

interface TourContextType {
  showTour: boolean;
  startTour: () => void;
  completeTour: () => void;
  skipTour: () => void;
  resetTourStatus: () => void;
}

const TourContext = createContext<TourContextType | undefined>(undefined);

export const useTour = () => {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error('useTour must be used within TourProvider');
  }
  return context;
};

interface TourProviderProps {
  children: ReactNode;
}

export const TourProvider: React.FC<TourProviderProps> = ({ children }) => {
  const [showTour, setShowTour] = useState(false);
  const { user } = useAuth();

  // Check if tour should be shown on mount (auto-start for new users only)
  useEffect(() => {
    if (user && shouldShowTour()) {
      // Check if this is a new user (just registered) vs existing user (logging in)
      const isNewUser = localStorage.getItem('is_new_user') === 'true';
      
      if (isNewUser) {
        // Auto-start tour for new users after signup
        // Small delay to ensure page is fully loaded
        const timer = setTimeout(() => {
          setShowTour(true);
          // Clear the flag after showing tour
          localStorage.removeItem('is_new_user');
        }, 1000);
        return () => clearTimeout(timer);
      }
    }
  }, [user]);

  const startTour = () => {
    setShowTour(true);
  };

  const completeTour = () => {
    setShowTour(false);
    markTourCompleted();
  };

  const skipTour = () => {
    setShowTour(false);
    markTourCompleted();
  };

  const resetTourStatus = () => {
    resetTour();
    setShowTour(false);
  };

  return (
    <TourContext.Provider
      value={{
        showTour,
        startTour,
        completeTour,
        skipTour,
        resetTourStatus,
      }}
    >
      {children}
    </TourContext.Provider>
  );
};

