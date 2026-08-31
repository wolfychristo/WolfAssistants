import React, { useState, useEffect, useCallback } from 'react';
import Joyride, { CallBackProps, STATUS, Step } from 'react-joyride';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface QuickTourProps {
  run?: boolean;
  onComplete?: () => void;
  onSkip?: () => void;
}

const TOUR_STORAGE_KEY = 'quick_tour_completed';

// Check if tour should run based on localStorage
export const shouldShowTour = (): boolean => {
  const completed = localStorage.getItem(TOUR_STORAGE_KEY);
  return completed !== 'true';
};

// Mark tour as completed
export const markTourCompleted = (): void => {
  localStorage.setItem(TOUR_STORAGE_KEY, 'true');
};

// Reset tour (for testing or admin)
export const resetTour = (): void => {
  localStorage.removeItem(TOUR_STORAGE_KEY);
};

const QuickTour: React.FC<QuickTourProps> = ({ run = false, onComplete, onSkip }) => {
  const [runTour, setRunTour] = useState(run);
  const [stepIndex, setStepIndex] = useState(0);
  const [isElementReady, setIsElementReady] = useState(false);
  const [navigationPending, setNavigationPending] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Tour steps configuration with enhanced visual indicators
  // Flow: Start tour -> Email setup -> Add contacts -> Generate & Send -> Manage emails -> Invoice page -> Invite Friends -> End
  const [steps] = useState<Step[]>([
    {
      target: '.quick-tour-dashboard',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            👋 Welcome to WolfAssistants!
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            Your dashboard shows key metrics like contacts, emails sent, meetings scheduled, and response rates. 
            <strong> 👉 Look at the stats cards below</strong> to see your activity at a glance. Let's get you started!
          </p>
        </div>
      ),
      placement: 'center',
      disableBeacon: false,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-email-config',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            ⚙️ Step 1: Email Configuration
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            <strong>👉 This is your first step!</strong> Set up your email account here. Add your SMTP (sending) and IMAP (receiving) settings. 
            Need help? Check the tooltips for common providers like Gmail or Outlook. This is required to send emails.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-add-contact',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            👥 Step 2: Add Your First Contact
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            <strong>👉 Click this button</strong> to add contacts manually, or use the Import button to upload from CSV. 
            Contacts are essential for sending personalized emails! Add at least one contact to continue.
          </p>
        </div>
      ),
      placement: 'right',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-generate-email',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            ✨ Step 3: Generate & Send Emails
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            <strong>👉 This powerful button</strong> lets you generate AI-powered emails for your contacts. 
            The platform will craft personalized messages based on your contacts and context. Click to generate and send emails automatically!
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-manage-emails',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            📧 Step 4: Manage Your Emails
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            <strong>👉 This is your email management center!</strong> Here you can view inbox, sent emails, drafts, and more. 
            Use the sidebar to navigate between folders. Click "Compose" to write new emails or reply to received ones.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-invoice',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            💰 Step 5: Create Invoices
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            <strong>👉 Manage your billing here!</strong> Create professional invoices for your clients. 
            Add line items, set payment terms, and generate PDF invoices. Track payments and manage your business finances.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-referral',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            🎁 Step 6: Invite Friends & Earn Credits
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            <strong>👉 Earn free credits by inviting friends!</strong> Share your referral code or send invitations via email. 
            You'll earn <strong>50 credits</strong> when your friend signs up! Use credits to unlock premium features and extend your usage.
          </p>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
    {
      target: '.quick-tour-dashboard',
      content: (
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '18px', fontWeight: 'bold' }}>
            🎉 You're All Set!
          </h3>
          <p style={{ margin: 0, lineHeight: '1.6' }}>
            Congratulations! You've completed the tour. <strong>👉 Start by:</strong> Setting up email → Adding contacts → Generating emails → Managing your inbox → Creating invoices → Inviting friends for credits. 
            Need help? Check the navigation menu or ask Wolfy in the chat!
          </p>
        </div>
      ),
      placement: 'center',
      disableBeacon: true,
      disableOverlayClose: false,
      spotlightClicks: false,
      spotlightPadding: 8,
    },
  ]);

  // Check if target element exists and is visible
  const checkElementExists = useCallback((targetSelector: string, maxRetries = 20): Promise<boolean> => {
    return new Promise((resolve) => {
      let retries = 0;
      const check = () => {
        const element = document.querySelector(targetSelector);
        if (element) {
          // Check if element is actually visible and has dimensions
          const rect = element.getBoundingClientRect();
          const isVisible = rect.width > 0 && rect.height > 0 && 
                           window.getComputedStyle(element).display !== 'none' &&
                           window.getComputedStyle(element).visibility !== 'hidden';
          
          if (isVisible) {
            // Additional delay to ensure element is fully rendered
            setTimeout(() => resolve(true), 200);
          } else if (retries < maxRetries) {
            retries++;
            setTimeout(check, 300);
          } else {
            resolve(false);
          }
        } else if (retries < maxRetries) {
          retries++;
          setTimeout(check, 300);
        } else {
          resolve(false);
        }
      };
      check();
    });
  }, []);

  // Handle step changes based on route
  useEffect(() => {
    if (!runTour) return;

    const currentStep = steps[stepIndex];
    if (!currentStep) return;

    setIsElementReady(false);
    setNavigationPending(true);

    // Navigate to appropriate page for each step
    // Flow: Dashboard -> Profile -> Contacts -> Dashboard -> Emails -> Invoices -> Pricing (Referrals) -> Dashboard
    const navigateToStep = async () => {
      let targetPath = '';
      switch (stepIndex) {
        case 0:
          targetPath = '/dashboard'; // Welcome
          break;
        case 1:
          targetPath = '/profile'; // Email setup
          break;
        case 2:
          targetPath = '/contacts'; // Add contacts
          break;
        case 3:
          targetPath = '/dashboard'; // Generate & Send
          break;
        case 4:
          targetPath = '/emails'; // Manage emails
          break;
        case 5:
          targetPath = '/invoices'; // Invoice page
          break;
        case 6:
          targetPath = '/pricing'; // Invite Friends & Earn Credits
          break;
        case 7:
          targetPath = '/dashboard'; // End tour
          break;
      }

      if (location.pathname !== targetPath) {
        navigate(targetPath);
        // Wait longer for navigation and page render
        await new Promise(resolve => setTimeout(resolve, 800));
      } else {
        // Even if on correct page, wait a bit for any dynamic content
        await new Promise(resolve => setTimeout(resolve, 300));
      }

      // Special handling for pricing page - switch to referrals tab
      if (targetPath === '/pricing' && stepIndex === 6) {
        // Wait a bit for page to load
        await new Promise(resolve => setTimeout(resolve, 500));
        // Find and click the referrals tab button
        const allButtons = Array.from(document.querySelectorAll('button'));
        const referralsTab = allButtons.find(btn => {
          const text = btn.textContent || '';
          return text.includes('Invite Friends') || text.includes('Earn Credits') || text.includes('referrals');
        });
        if (referralsTab && referralsTab instanceof HTMLElement) {
          referralsTab.click();
          // Wait for tab switch
          await new Promise(resolve => setTimeout(resolve, 400));
        }
      }

      // Wait for element to exist and be fully rendered
      const targetSelector = currentStep.target as string;
      const exists = await checkElementExists(targetSelector, 20);
      
      if (exists) {
        // Double-check element is still valid before showing
        const element = document.querySelector(targetSelector);
        if (element && element.getBoundingClientRect().width > 0) {
          // Additional small delay to ensure Popper can access the element
          await new Promise(resolve => setTimeout(resolve, 100));
          setIsElementReady(true);
          setNavigationPending(false);
        } else {
          // Element disappeared, skip
          console.warn(`Tour target element became invalid: ${targetSelector}`);
          if (stepIndex < steps.length - 1) {
            setStepIndex(stepIndex + 1);
          } else {
            setRunTour(false);
            markTourCompleted();
            onComplete?.();
          }
        }
      } else {
        // If element doesn't exist, skip to next step or end tour
        console.warn(`Tour target element not found: ${targetSelector}`);
        if (stepIndex < steps.length - 1) {
          setStepIndex(stepIndex + 1);
        } else {
          setRunTour(false);
          markTourCompleted();
          onComplete?.();
        }
      }
    };

    navigateToStep();
  }, [stepIndex, runTour, location.pathname, navigate, steps, checkElementExists, onComplete]);

  const handleJoyrideCallback = useCallback((data: CallBackProps) => {
    const { status, type, index } = data;

    // Handle errors gracefully
    if (status === STATUS.SKIPPED) {
      setRunTour(false);
      markTourCompleted();
      onSkip?.();
      return;
    }

    // Check if current step target exists before proceeding
    if (type === 'step:before' && typeof index === 'number') {
      const currentStep = steps[index];
      if (currentStep) {
        const target = document.querySelector(currentStep.target as string);
        if (!target) {
          console.warn(`Tour target element not found before step: ${currentStep.target}`);
          // Skip to next step if element doesn't exist
          if (index < steps.length - 1) {
            setTimeout(() => setStepIndex(index + 1), 100);
          } else {
            setRunTour(false);
            markTourCompleted();
            onComplete?.();
          }
          return;
        }
        // Verify element is still visible
        const rect = target.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
          console.warn(`Tour target element has no dimensions: ${currentStep.target}`);
          if (index < steps.length - 1) {
            setTimeout(() => setStepIndex(index + 1), 100);
          } else {
            setRunTour(false);
            markTourCompleted();
            onComplete?.();
          }
          return;
        }
      }
    }

    if (status === STATUS.FINISHED) {
      setRunTour(false);
      markTourCompleted();
      onComplete?.();
    } else if (type === 'step:after' && typeof index === 'number') {
      setStepIndex(index + 1);
    }
  }, [onComplete, onSkip, steps]);

  // Sync runTour with prop and reset step index when starting
  useEffect(() => {
    setRunTour(run);
    if (run) {
      setStepIndex(0);
      setIsElementReady(false);
      setNavigationPending(false);
    }
  }, [run]);

  // Don't show tour if user is not logged in
  if (!user) {
    return null;
  }

  // Only show tour when element is ready and not navigating
  const shouldRun = runTour && isElementReady && !navigationPending;

  // Use original steps array - element checking is done in callbacks and navigation
  // Filtering steps dynamically can cause index mismatches

  // Only render Joyride if we have a valid current step with existing element
  const currentStep = steps[stepIndex];
  const hasValidTarget = currentStep && document.querySelector(currentStep.target as string) !== null;

  if (!shouldRun || !hasValidTarget) {
    return null;
  }

  return (
    <Joyride
      steps={steps}
      run={shouldRun}
      stepIndex={stepIndex}
      continuous
      showProgress
      showSkipButton
      callback={handleJoyrideCallback}
      disableScrolling={false}
      disableOverlayClose={false}
      spotlightClicks={false}
      disableCloseOnEsc={false}
      hideCloseButton={false}
      floaterProps={{
        disableAnimation: false,
        placement: 'auto',
        styles: {
          arrow: {
            color: '#2563eb',
          },
        },
      }}
      styles={{
        options: {
          primaryColor: '#2563eb', // blue-600
          zIndex: 10000,
          arrowColor: '#2563eb',
        },
        tooltip: {
          borderRadius: '12px',
          padding: '24px',
          fontSize: '15px',
          maxWidth: '400px',
        },
        tooltipContainer: {
          textAlign: 'left',
        },
        tooltipTitle: {
          fontSize: '18px',
          fontWeight: 'bold',
          marginBottom: '12px',
        },
        tooltipContent: {
          padding: '0',
        },
        buttonNext: {
          backgroundColor: '#2563eb',
          fontSize: '14px',
          padding: '10px 20px',
          borderRadius: '6px',
          fontWeight: '600',
        },
        buttonBack: {
          color: '#6b7280',
          fontSize: '14px',
          marginRight: '10px',
          fontWeight: '500',
        },
        buttonSkip: {
          color: '#6b7280',
          fontSize: '14px',
          fontWeight: '500',
        },
        spotlight: {
          borderRadius: '8px',
        },
      }}
      locale={{
        back: '← Back',
        close: '✕',
        last: 'Get Started!',
        next: 'Next →',
        open: 'Open the dialog',
        skip: 'Skip Tour',
      }}
    />
  );
};

export default QuickTour;

