import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { emailSettingsAPI } from '../services/api';
import toast from 'react-hot-toast';
import { useAuth } from './AuthContext';

export interface EmailConfig {
  smtp_host: string;
  smtp_port: string | number | undefined;
  smtp_username: string;
  smtp_password: string;
  smtp_from: string;
  smtp_use_tls: boolean;
  imap_host: string;
  imap_port: string | number | undefined;
  imap_username: string;
  imap_password: string;
  imap_use_ssl: boolean;
  // Auto follow-ups
  auto_followup_enabled?: boolean;
  auto_followup_max_days?: number;
  auto_followup_daily_hour?: number;
  last_auto_followup_run?: string;
  last_auto_followup_sent_count?: number;
}

// Interface for API payloads that allows undefined values
interface EmailConfigPayload {
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_from?: string;
  smtp_use_tls?: boolean;
  imap_host?: string;
  imap_port?: number;
  imap_username?: string;
  imap_password?: string;
  imap_use_ssl?: boolean;
  auto_followup_enabled?: boolean;
  auto_followup_max_days?: number;
  auto_followup_daily_hour?: number;
}

interface EmailConfigContextType {
  emailConfig: EmailConfig | null;
  isConfigured: boolean;
  isLoading: boolean;
  loadEmailConfig: () => Promise<void>;
  updateEmailConfig: (config: EmailConfig) => Promise<boolean>;
  clearEmailConfig: () => void;
}

const EmailConfigContext = createContext<EmailConfigContextType | undefined>(undefined);

export const useEmailConfig = () => {
  const context = useContext(EmailConfigContext);
  if (context === undefined) {
    throw new Error('useEmailConfig must be used within an EmailConfigProvider');
  }
  return context;
};

interface EmailConfigProviderProps {
  children: ReactNode;
}

export const EmailConfigProvider: React.FC<EmailConfigProviderProps> = ({ children }) => {
  const [emailConfig, setEmailConfig] = useState<EmailConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAuth();

  const isConfigured = Boolean(emailConfig !== null && 
    emailConfig.smtp_host && 
    emailConfig.smtp_port && 
    emailConfig.smtp_username && 
    emailConfig.smtp_password && 
    emailConfig.smtp_from &&
    emailConfig.imap_host && 
    emailConfig.imap_port && 
    emailConfig.imap_username && 
    emailConfig.imap_password);

  const loadEmailConfig = async () => {
    try {
      setIsLoading(true);
      const response = await emailSettingsAPI.getMine();
      if (response.data) {
        setEmailConfig(response.data);
      }
    } catch (error) {
      setEmailConfig(null);
    } finally {
      setIsLoading(false);
    }
  };

  const updateEmailConfig = async (config: EmailConfig): Promise<boolean> => {
    try {
      setIsLoading(true);
      
      // Sanitize the config data before sending
      const sanitizedConfig = sanitizeEmailConfig(config);
      
      await emailSettingsAPI.updateMine(sanitizedConfig);
      // Only update local state with non-undefined values
      const updatedConfig = { ...config };
      Object.keys(sanitizedConfig).forEach(key => {
        if (sanitizedConfig[key as keyof EmailConfigPayload] !== undefined) {
          (updatedConfig as any)[key] = sanitizedConfig[key as keyof EmailConfigPayload];
        }
      });
      setEmailConfig(updatedConfig);
      toast.success('Email configuration saved successfully!');
      return true;
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 'Failed to save email configuration';
      toast.error(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const clearEmailConfig = () => {
    setEmailConfig(null);
  };

  // Helper function to sanitize email config data
  const sanitizeEmailConfig = (config: EmailConfig): EmailConfigPayload => {
    return {
      smtp_host: config.smtp_host?.trim() || undefined,
      smtp_port: config.smtp_port ? Number(config.smtp_port) : undefined,
      smtp_username: config.smtp_username?.trim() || undefined,
      smtp_password: config.smtp_password, // Send password as-is, even if empty
      smtp_from: config.smtp_from?.trim() || undefined,
      smtp_use_tls: Boolean(config.smtp_use_tls),
      imap_host: config.imap_host?.trim() || undefined,
      imap_port: config.imap_port ? Number(config.imap_port) : undefined,
      imap_username: config.imap_username?.trim() || undefined,
      imap_password: config.imap_password, // Send password as-is, even if empty
      imap_use_ssl: Boolean(config.imap_use_ssl),
      auto_followup_enabled: config.auto_followup_enabled,
      auto_followup_max_days: typeof config.auto_followup_max_days === 'number' ? config.auto_followup_max_days : undefined,
      auto_followup_daily_hour: typeof config.auto_followup_daily_hour === 'number' ? config.auto_followup_daily_hour : undefined,
    };
  };

  useEffect(() => {
    if (user) {
      loadEmailConfig();
    } else {
      setEmailConfig(null);
      setIsLoading(false);
    }
  }, [user]);

  const value = {
    emailConfig,
    isConfigured,
    isLoading,
    loadEmailConfig,
    updateEmailConfig,
    clearEmailConfig,
  };

  return (
    <EmailConfigContext.Provider value={value}>
      {children}
    </EmailConfigContext.Provider>
  );
};