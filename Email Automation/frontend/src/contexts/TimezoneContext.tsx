import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

type TimezoneContextValue = {
  timeZone: string;
  setTimeZone: (tz: string) => void;
};

const TimezoneContext = createContext<TimezoneContextValue | null>(null as any);

export const TimezoneProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const defaultTz = useMemo(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';
    } catch {
      return 'Asia/Kolkata';
    }
  }, []);

  const [timeZone, setTimeZoneState] = useState<string>(() => localStorage.getItem('app.timeZone') || defaultTz);

  const setTimeZone = (tz: string) => {
    setTimeZoneState(tz);
    localStorage.setItem('app.timeZone', tz);
  };

  useEffect(() => {
    // no-op, retained for potential side effects later
  }, [timeZone]);

  return (
    <TimezoneContext.Provider value={{ timeZone, setTimeZone }}>
      {children}
    </TimezoneContext.Provider>
  );
};

export const useTimezone = (): TimezoneContextValue => {
  const ctx = useContext(TimezoneContext);
  if (!ctx) throw new Error('useTimezone must be used within TimezoneProvider');
  return ctx;
};


