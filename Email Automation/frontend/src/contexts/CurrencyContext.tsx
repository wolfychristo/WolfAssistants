import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

type RatesMap = Record<string, number>;

type CurrencyContextType = {
  countryCode: string | null;
  currencyCode: string;
  currencySymbol: string;
  rates: RatesMap;
  setCountry: (code: string) => void;
  setCurrency: (code: string) => void;
  convert: (amount: number, from: string, to: string) => number;
  currencies: { code: string; symbol: string; name: string }[];
  countries: { code: string; name: string; currency: string }[];
};

const defaultBase = 'USD';

const CURRENCIES: { code: string; symbol: string; name: string }[] = [
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '€', name: 'Euro' },
  { code: 'GBP', symbol: '£', name: 'British Pound' },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee' },
  { code: 'AED', symbol: 'د.إ', name: 'UAE Dirham' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen' },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan' },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar' },
  { code: 'ZAR', symbol: 'R', name: 'South African Rand' },
  { code: 'BRL', symbol: 'R$', name: 'Brazilian Real' },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
];

const COUNTRIES: { code: string; name: string; currency: string }[] = [
  { code: 'US', name: 'United States', currency: 'USD' },
  { code: 'GB', name: 'United Kingdom', currency: 'GBP' },
  { code: 'DE', name: 'Germany', currency: 'EUR' },
  { code: 'FR', name: 'France', currency: 'EUR' },
  { code: 'IN', name: 'India', currency: 'INR' },
  { code: 'AE', name: 'United Arab Emirates', currency: 'AED' },
  { code: 'AU', name: 'Australia', currency: 'AUD' },
  { code: 'JP', name: 'Japan', currency: 'JPY' },
  { code: 'CN', name: 'China', currency: 'CNY' },
  { code: 'SG', name: 'Singapore', currency: 'SGD' },
  { code: 'ZA', name: 'South Africa', currency: 'ZAR' },
  { code: 'BR', name: 'Brazil', currency: 'BRL' },
  { code: 'CA', name: 'Canada', currency: 'CAD' },
];

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export const useCurrency = () => {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error('useCurrency must be used within CurrencyProvider');
  return ctx;
};

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [countryCode, setCountryCode] = useState<string | null>(null);
  const [currencyCode, setCurrencyCode] = useState<string>(defaultBase);
  const [rates, setRates] = useState<RatesMap>({ [defaultBase]: 1 });

  // Fetch latest rates relative to defaultBase using exchangerate-api.com (more reliable)
  useEffect(() => {
    const url = `https://api.exchangerate-api.com/v4/latest/${defaultBase}`;
    let cancelled = false;
    const fetchRates = async () => {
      try {
        // Add timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
        
        const res = await fetch(url, { 
          signal: controller.signal,
          mode: 'cors',
          cache: 'no-cache'
        });
        clearTimeout(timeoutId);
        
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        if (!cancelled && data && data.rates) {
          // Filter only the currencies we need
          const filteredRates: RatesMap = { [defaultBase]: 1 };
          CURRENCIES.forEach(currency => {
            if (data.rates[currency.code]) {
              filteredRates[currency.code] = data.rates[currency.code];
            }
          });
          setRates(filteredRates);
        }
      } catch (error) {
        // Silent error handling for production - use default rates
        console.warn('Currency API fetch failed, using default rates:', error);
        // Set default rates to prevent any issues
        const defaultRates: RatesMap = { [defaultBase]: 1 };
        CURRENCIES.forEach(currency => {
          defaultRates[currency.code] = 1; // Default to 1:1 ratio
        });
        if (!cancelled) {
          setRates(defaultRates);
        }
      }
    };
    
    // Only fetch if we have internet connectivity
    if (navigator.onLine) {
      fetchRates();
      const id = setInterval(fetchRates, 60 * 60 * 1000); // hourly refresh
      return () => { cancelled = true; clearInterval(id); };
    } else {
      // Set default rates if offline
      const defaultRates: RatesMap = { [defaultBase]: 1 };
      CURRENCIES.forEach(currency => {
        defaultRates[currency.code] = 1;
      });
      setRates(defaultRates);
    }
  }, []);

  const currencySymbol = useMemo(() => {
    return CURRENCIES.find(c => c.code === currencyCode)?.symbol || '';
  }, [currencyCode]);

  const convert = (amount: number, from: string, to: string): number => {
    if (!isFinite(amount)) return 0;
    const f = from || defaultBase;
    const t = to || defaultBase;
    if (f === t) return amount;
    const rFrom = rates[f] || 1;
    const rTo = rates[t] || 1;
    if (!rFrom || !rTo) return amount;
    const inBase = amount / rFrom; // to USD
    return inBase * rTo;
  };

  const setCountry = (code: string) => {
    setCountryCode(code);
    const found = COUNTRIES.find(c => c.code === code);
    if (found) setCurrencyCode(found.currency);
  };

  const setCurrency = (code: string) => {
    setCurrencyCode(code);
  };

  const value: CurrencyContextType = {
    countryCode,
    currencyCode,
    currencySymbol,
    rates,
    setCountry,
    setCurrency,
    convert,
    currencies: CURRENCIES,
    countries: COUNTRIES,
  };

  return (
    <CurrencyContext.Provider value={value}>
      {children}
    </CurrencyContext.Provider>
  );
};


