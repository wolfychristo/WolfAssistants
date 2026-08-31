import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useCurrency } from '../contexts/CurrencyContext';
import { invoiceClientsAPI, api } from '../services/api';
import toast from 'react-hot-toast';
import { Trash2, Plus } from 'lucide-react';
// duplicate import removed

// GSTIN validation (regex + Luhn mod-36 check digit) – client-side
const GSTINFORMAT_REGEX = /^[0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}[1-9A-Za-z]{1}Z[0-9A-Za-z]{1}$/;
const GSTN_CODEPOINT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

const getGSTINWithCheckDigit = (gstinWO: string): string => {
  const chars = GSTN_CODEPOINT_CHARS.split('');
  const input = (gstinWO || '').trim().toUpperCase().split('');
  const mod = chars.length;
  let factor = 2;
  let sum = 0;
  for (let i = input.length - 1; i >= 0; i--) {
    const codePoint = chars.indexOf(input[i]);
    if (codePoint < 0) return '';
    let digit = factor * codePoint;
    factor = factor === 2 ? 1 : 2;
    digit = Math.floor(digit / mod) + (digit % mod);
    sum += digit;
  }
  const checkCodePoint = (mod - (sum % mod)) % mod;
  return gstinWO + chars[checkCodePoint];
};

const validateGSTINLocal = (value: string): boolean => {
  const v = (value || '').trim();
  if (!GSTINFORMAT_REGEX.test(v)) return false;
  return v.toUpperCase() === getGSTINWithCheckDigit(v.slice(0, -1));
};

type LineItem = {
  description: string;
  quantity: number;
  unitPrice: number;
  discountPct?: number;
  taxPct?: number;
};

type InvoiceClient = {
  id: number;
  public_id?: string;
  name: string;
  business_name?: string | null;
  address?: string | null;
  email?: string | null;
  phone?: string | null;
  tax_id?: string | null;
  country_code?: string | null;
};

const currencyFormat = (currency: string, amount: number) => {
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
};

// Tax ID validation functions
const validateGSTNumber = (gst: string): boolean => {
  // Use the existing comprehensive GST validation
  return validateGSTINLocal(gst);
};

const validateVATNumber = (vat: string): boolean => {
  // Basic VAT validation: 9 or 12 digits
  const vatRegex = /^[0-9]{9}$|^[0-9]{12}$/;
  return vatRegex.test(vat.replace(/\s/g, ''));
};

const hasValidTaxId = (country: string | null, taxId: string): boolean => {
  if (!taxId || !country) return false;
  const countryCode = country.toUpperCase();
  const cleanTaxId = taxId.trim();
  
  if (countryCode === 'IN') {
    return validateGSTNumber(cleanTaxId);
  }
  if (countryCode === 'GB') {
    return validateVATNumber(cleanTaxId);
  }
  // For other countries, consider any non-empty tax ID as valid
  return cleanTaxId.length > 0;
};

// Determine what tax field should be shown based on country
const getTaxFieldInfo = (country: string | null) => {
  if (!country) return { show: false, name: '', label: '' };
  
  const countryCode = country.toUpperCase();
  if (countryCode === 'IN') {
    return { show: true, name: 'GST', label: 'GST No (optional)' };
  }
  // For all other countries, show VAT field
  return { show: true, name: 'VAT', label: 'VAT No (optional)' };
};

// Local fallback tax rules (mirrors backend) to avoid UI blocking if backend not yet restarted
const fallbackCompute = (cc?: string | null, sec?: string | null, hasValidTaxId?: boolean) => {
  // If no valid tax ID is provided, return 0% tax
  if (!hasValidTaxId) {
    return { tax_percent: 0, tax_name: 'NONE' } as const;
  }
  
  const C = (cc || '').toUpperCase();
  const S = (sec || 'other').toLowerCase();
  if (C === 'IN') {
    if (S === 'saas') return { tax_percent: 18, tax_name: 'GST' } as const;
    if (S === 'education') return { tax_percent: 12, tax_name: 'GST' } as const;
    if (S === 'healthcare') return { tax_percent: 5, tax_name: 'GST' } as const;
    return { tax_percent: 18, tax_name: 'GST' } as const;
  }
  if (C === 'GB') {
    return { tax_percent: 20, tax_name: 'VAT' } as const;
  }
  return { tax_percent: 0, tax_name: 'NONE' } as const;
};

const Invoices: React.FC = () => {
  // Seller (no bank details per request)
  const [sellerName, setSellerName] = useState('Your Name');
  const [sellerLogoUrl, setSellerLogoUrl] = useState('');
  const [sellerSignatureUrl, setSellerSignatureUrl] = useState('');
  const [sellerAddress, setSellerAddress] = useState('123 Main St, City, ST 12345, Country');
  const [sellerEmail, setSellerEmail] = useState('billing@yourbusiness.com');
  const [sellerPhone, setSellerPhone] = useState('+1 555-0100');
  const [sellerGSTNo, setSellerGSTNo] = useState('');
  const [gstValid, setGstValid] = useState<boolean | null>(null);
  const [sellerBusinessName, setSellerBusinessName] = useState('Your Business LLC');

  // Buyer
  const [buyerName, setBuyerName] = useState('Client Name');
  const [buyerAddress, setBuyerAddress] = useState('456 Market Ave, City, ST 67890, Country');
  const [buyerEmail, setBuyerEmail] = useState('ap@client.com');
  const [buyerPhone, setBuyerPhone] = useState('+1 555-0101');
  const [buyerTaxId, setBuyerTaxId] = useState('');
  const [poNumber, setPoNumber] = useState('');
  const [buyerBusinessName, setBuyerBusinessName] = useState('Client Company Inc.');
  const [buyerSignatureUrl, setBuyerSignatureUrl] = useState('');
  const [invoiceClients, setInvoiceClients] = useState<InvoiceClient[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | ''>('');
  const [isSavingClient, setIsSavingClient] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'form'>('grid');

  // Invoice meta
  const todayIso = new Date().toISOString().slice(0, 10);
  const in30 = new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  const [invoiceNumber, setInvoiceNumber] = useState('INV-2025-0001');
  const [issueDate, setIssueDate] = useState(todayIso);
  const [dueDate, setDueDate] = useState(in30);
  // Currency management comes from context
  const { currencyCode, setCurrency, currencies, convert, countryCode, countries, setCountry } = useCurrency() as any;
  const [sector, setSector] = useState<'saas' | 'education' | 'healthcare' | 'other'>('saas');
  const [autoTax, setAutoTax] = useState({ taxPercent: 0, taxName: 'NONE' });
  const [serviceFrom, setServiceFrom] = useState('');
  const [serviceTo, setServiceTo] = useState('');
  const [notes, setNotes] = useState('Payment due within 30 days. Thank you for your business.');
  const [amountPaid, setAmountPaid] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);

  // Items
  const [items, setItems] = useState<LineItem[]>([
    { description: 'Consulting – Setup/Onboarding', quantity: 10, unitPrice: 100, discountPct: 0, taxPct: 10 },
    { description: 'Subscription – Pro Plan (Monthly)', quantity: 1, unitPrice: 299, discountPct: 0, taxPct: 10 },
  ]);

  const addItem = () => {
    setItems([
      ...items,
      { description: '', quantity: 1, unitPrice: 0, discountPct: 0, taxPct: 0 },
    ]);
  };

  const removeItem = (idx: number) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const updateItem = (idx: number, patch: Partial<LineItem>) => {
    setItems(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  };

  // Totals with global tax engine (backend compute for accuracy/future Stripe Tax)
  const totals = useMemo(() => {
    let subtotal = 0;
    for (const it of items) {
      const line = (Number(it.quantity) || 0) * (Number(it.unitPrice) || 0);
      subtotal += line;
    }
    // Prefer auto tax if available; fallback to 0 if GST validation is required locally
    const taxPercent = autoTax.taxPercent || 0;
    const tax = subtotal * (taxPercent / 100);
    const discount = Number(discountAmount) || 0;
    const total = subtotal + tax - discount;
    const amountPaidValue = Number(amountPaid) || 0;

    const subtotalC = convert(subtotal, 'USD', currencyCode);
    const taxC = convert(tax, 'USD', currencyCode);
    const discountC = convert(discount, 'USD', currencyCode);
    const totalC = convert(total, 'USD', currencyCode);
    const amountPaidC = convert(amountPaidValue, 'USD', currencyCode);
    const amountDueC = Math.max(0, totalC - amountPaidC);
    return { subtotal: subtotalC, tax: taxC, discount: discountC, total: totalC, amountDue: amountDueC, taxPercent, taxName: autoTax.taxName };
  }, [items, discountAmount, amountPaid, currencyCode, convert, autoTax]);


  // Auto compute tax when country, sector, or tax ID changes
  useEffect(() => {
    const compute = async () => {
      try {
        // Use current subtotal for compute
        let subtotal = 0;
        for (const it of items) {
          subtotal += (Number(it.quantity) || 0) * (Number(it.unitPrice) || 0);
        }
        
        // Check if we have a valid tax ID
        const validTaxId = hasValidTaxId(countryCode, sellerGSTNo || buyerTaxId);
        
        if (!isFinite(subtotal) || subtotal <= 0) {
          const fb0 = fallbackCompute(countryCode, sector, validTaxId);
          setAutoTax({ taxPercent: fb0.tax_percent, taxName: fb0.tax_name });
          return;
        }
        
        // If no valid tax ID, set tax to 0%
        if (!validTaxId) {
          setAutoTax({ taxPercent: 0, taxName: 'NONE' });
          return;
        }
        
        const params = new URLSearchParams();
        params.set('price', String(subtotal));
        if (countryCode) params.set('country_code', countryCode);
        if (sector) params.set('sector', sector);
        if (sellerGSTNo) params.set('tax_id', sellerGSTNo);
        else if (buyerTaxId) params.set('tax_id', buyerTaxId);
        const res = await api.get(`/tax/compute?${params.toString()}`);
        const ok = (res as any)?.status === 200;
        const data = (res as any)?.data || {};
        if (!ok || typeof data.tax_percent !== 'number') {
          const fb = fallbackCompute(countryCode, sector, validTaxId);
          setAutoTax({ taxPercent: fb.tax_percent, taxName: fb.tax_name });
          return;
        } else {
          setAutoTax({ taxPercent: data.tax_percent || 0, taxName: data.tax_name || 'NONE' });
        }
      } catch {
        const validTaxId = hasValidTaxId(countryCode, sellerGSTNo || buyerTaxId);
        const fb = fallbackCompute(countryCode, sector, validTaxId);
        setAutoTax({ taxPercent: fb.tax_percent, taxName: fb.tax_name });
        return;
      }
    };
    compute();
  }, [countryCode, sector, items, sellerGSTNo, buyerTaxId]);

  // PDF Download via html2pdf (CDN if missing)
  const previewRef = useRef<HTMLDivElement>(null);

  const ensureHtml2Pdf = async () => {
    const w = window as any;
    if (w.html2pdf) return w.html2pdf;
    await new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load html2pdf.js'));
      document.body.appendChild(script);
    });
    return (window as any).html2pdf;
  };

  const downloadPdf = async () => {
    try {
      const html2pdf = await ensureHtml2Pdf();
      const element = previewRef.current;
      if (!element) return;
      const file = `invoice-${invoiceNumber || 'draft'}.pdf`;
      const opt = {
        margin: 0,
        filename: file,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      };
      html2pdf().set(opt).from(element).save();
    } catch (e: any) {
      toast.error(e?.message || 'Failed to generate PDF');
    }
  };

  // Logo image upload
  const onLogoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Please choose an image file');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setSellerLogoUrl(String(reader.result || ''));
    reader.readAsDataURL(file);
  };

  const onSellerSigFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Please choose an image file');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setSellerSignatureUrl(String(reader.result || ''));
    reader.readAsDataURL(file);
  };

  const onBuyerSigFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Please choose an image file');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setBuyerSignatureUrl(String(reader.result || ''));
    reader.readAsDataURL(file);
  };

  const loadInvoiceClients = async () => {
    try {
      const res = await invoiceClientsAPI.getAll();
      setInvoiceClients(Array.isArray(res.data) ? res.data : []);
    } catch {
      toast.error('Failed to load saved clients');
    }
  };

  useEffect(() => {
    loadInvoiceClients();
  }, []);

  const applyClient = (client: InvoiceClient) => {
    setBuyerName(client.name || '');
    setBuyerBusinessName(client.business_name || '');
    setBuyerAddress(client.address || '');
    setBuyerEmail(client.email || '');
    setBuyerPhone(client.phone || '');
    setBuyerTaxId(client.tax_id || '');
    if (client.country_code) {
      setCountry(client.country_code);
    }
  };

  const handleSaveClient = async () => {
    if (!buyerName?.trim()) {
      toast.error('Buyer name is required');
      return;
    }
    setIsSavingClient(true);
    try {
      const payload = {
        name: buyerName.trim(),
        business_name: buyerBusinessName?.trim() || null,
        address: buyerAddress?.trim() || null,
        email: buyerEmail?.trim() || null,
        phone: buyerPhone?.trim() || null,
        tax_id: buyerTaxId?.trim() || null,
        country_code: countryCode || null,
      };
      const res = await invoiceClientsAPI.create(payload);
      const saved = res.data as InvoiceClient;
      setInvoiceClients((prev) => {
        const existing = prev.find((c) => c.id === saved.id);
        if (existing) {
          return prev.map((c) => (c.id === saved.id ? saved : c));
        }
        return [saved, ...prev];
      });
      setSelectedClientId(saved.id);
      toast.success('Client saved');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to save client');
    } finally {
      setIsSavingClient(false);
    }
  };

  const handleDeleteClient = async () => {
    if (!selectedClientId) return;
    if (!window.confirm('Remove this saved client?')) return;
    try {
      await invoiceClientsAPI.delete(Number(selectedClientId));
      setInvoiceClients((prev) => prev.filter((c) => c.id !== selectedClientId));
      setSelectedClientId('');
      toast.success('Client removed');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to remove client');
    }
  };

  // Preview toggle
  const [showPreview, setShowPreview] = useState(false);

  // Clear tax field and validation when country changes
  useEffect(() => {
    setSellerGSTNo('');
    setGstValid(null);
  }, [countryCode]);

  // Validate GST/VAT locally on change (debounced)
  useEffect(() => {
    const value = sellerGSTNo.trim();
    if (!value) { setGstValid(null); return; }
    if (!countryCode) { setGstValid(null); return; }
    
    const t = setTimeout(() => {
      try {
        if (countryCode === 'IN') {
          // Validate as GST for India
          setGstValid(validateGSTNumber(value));
        } else {
          // Validate as VAT for other countries
          setGstValid(validateVATNumber(value));
        }
      } catch {
        setGstValid(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [sellerGSTNo, countryCode]);


  return (
    <div className="min-h-screen pt-24 pb-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Invoices</h1>
            <p className="text-gray-600 mt-1 text-sm">Create and manage your invoices</p>
          </div>
          <div className="flex items-center gap-3">
            {viewMode === 'form' && (
              <button
                onClick={() => {
                  setViewMode('grid');
                  setShowPreview(false);
                }}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg text-sm font-medium"
              >
                Back to Presets
              </button>
            )}
            <button
              onClick={() => {
                setViewMode('form');
                setShowPreview(false);
              }}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-all flex items-center gap-2 text-sm"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              New
            </button>
            <button
              onClick={() => setShowPreview((v) => !v)}
              className={`px-4 py-2 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg flex items-center gap-2 transition-all text-sm font-medium ${
                viewMode !== 'form' ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              disabled={viewMode !== 'form'}
            >
              {showPreview ? 'Edit' : 'Preview'}
            </button>
            <button
              onClick={downloadPdf}
              className={`px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all flex items-center gap-2 text-sm ${
                viewMode !== 'form' ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              disabled={viewMode !== 'form'}
            >
              Download PDF
            </button>
          </div>
        </div>

        {viewMode === 'grid' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Client Presets</h2>
              <button
                onClick={() => {
                  setViewMode('form');
                  setShowPreview(false);
                }}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-all flex items-center gap-2 text-sm"
              >
                <Plus className="w-4 h-4" aria-hidden="true" />
                New
              </button>
            </div>
            {invoiceClients.length === 0 ? (
              <div className="text-sm text-gray-600">
                No saved clients yet. Click “New” to create an invoice and save a client.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {invoiceClients.map((client) => (
                  <button
                    key={client.id}
                    onClick={() => {
                      setSelectedClientId(client.id);
                      applyClient(client);
                      setViewMode('form');
                      setShowPreview(false);
                    }}
                    className="text-left border border-gray-200 rounded-xl p-4 hover:border-purple-300 hover:shadow-sm transition-all"
                  >
                    <div className="text-lg font-semibold text-gray-900 truncate">
                      {client.name}
                    </div>
                    {client.business_name && (
                      <div className="text-sm text-gray-600 truncate">{client.business_name}</div>
                    )}
                    <div className="text-xs text-gray-500 mt-2 truncate">
                      {client.email || client.phone || client.address || 'No contact details'}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6">
          {/* Form Section */}
          <div className={`${showPreview ? 'hidden' : 'block'} space-y-6 ${viewMode !== 'form' ? 'hidden' : ''}`}>
            {/* Seller Info */}
            <div className="bg-yellow-50 rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Seller Name <span className="text-red-500">*</span></label>
                  <input value={sellerName} onChange={(e)=>setSellerName(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Logo Image (optional)</label>
                  <div className="flex items-center gap-2">
                    <input type="file" accept="image/*" onChange={onLogoFileChange} className="text-sm text-gray-600" />
                    {sellerLogoUrl && (
                      <div className="flex items-center gap-2">
                        <img src={sellerLogoUrl} className="h-8 w-8 object-contain rounded" alt="Logo" />
                        <button onClick={()=>setSellerLogoUrl('')} className="text-sm text-red-600 hover:text-red-700">Remove</button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="md:col-span-2 space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Seller Address <span className="text-red-500">*</span></label>
                  <input value={sellerAddress} onChange={(e)=>setSellerAddress(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Business Name <span className="text-red-500">*</span></label>
                  <input value={sellerBusinessName} onChange={(e)=>setSellerBusinessName(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Seller Email <span className="text-red-500">*</span></label>
                  <input value={sellerEmail} onChange={(e)=>setSellerEmail(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Seller Phone <span className="text-red-500">*</span></label>
                  <input value={sellerPhone} onChange={(e)=>setSellerPhone(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                {getTaxFieldInfo(countryCode).show && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      {getTaxFieldInfo(countryCode).label}
                    </label>
                    <input
                      type="text"
                      value={sellerGSTNo}
                      onChange={(e) => {
                        setSellerGSTNo(e.target.value);
                        // Clear validation state when user starts typing
                        if (gstValid === false) setGstValid(null);
                      }}
                      placeholder={countryCode === 'IN' ? 'Enter GST Number' : 'Enter VAT Number'}
                      className={`w-full px-3 py-2 bg-white border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none ${
                        gstValid === false ? 'border-red-500' : 'border-gray-300'
                      }`}
                    />
                    {gstValid === false && (
                      <p className="text-xs text-red-600 mt-1">
                        {countryCode === 'IN' ? 'Invalid GST Number format' : 'Invalid VAT Number format'}
                      </p>
                    )}
                    {gstValid === true && (
                      <p className="text-xs text-green-600 mt-1">
                        Valid {countryCode === 'IN' ? 'GST' : 'VAT'} Number
                      </p>
                    )}
                  </div>
                )}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Seller Signature (optional)</label>
                  <input type="file" accept="image/*" onChange={onSellerSigFileChange} className="text-sm text-gray-600" />
                </div>
              </div>
            </div>

            {/* Tax Settings */}
            <div className="bg-yellow-50 rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Tax Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Country</label>
                  <select
                    value={countryCode || ''}
                    onChange={(e) => setCountry(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="">Select Country</option>
                    {countries.map((c: any) => (
                      <option key={c.code} value={c.code}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Business Sector</label>
                  <select
                    value={sector}
                    onChange={(e) => setSector(e.target.value as any)}
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="saas">SaaS / Software</option>
                    <option value="education">Education</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-3">Select your country and sector to auto-apply the correct tax (e.g., GST in India, VAT in the UK). The tax is used for totals and saved with the invoice.</p>
            </div>

            {/* Buyer Info */}
            <div className="bg-yellow-50 rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Bill To</h3>
              <div className="flex flex-col md:flex-row md:items-end gap-3 mb-4">
                <div className="flex-1 space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Saved Clients</label>
                  <select
                    value={selectedClientId}
                    onChange={(e) => {
                      const raw = e.target.value;
                      if (!raw) {
                        setSelectedClientId('');
                        return;
                      }
                      const id = Number(raw);
                      setSelectedClientId(id);
                      const match = invoiceClients.find((c) => c.id === id);
                      if (match) {
                        applyClient(match);
                      }
                    }}
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="">Select a client</option>
                    {invoiceClients.map((client) => (
                      <option key={client.id} value={client.id}>
                        {client.name}{client.business_name ? ` — ${client.business_name}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleSaveClient}
                    disabled={isSavingClient}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isSavingClient ? 'Saving...' : 'Save Client'}
                  </button>
                  {selectedClientId && (
                    <button
                      type="button"
                      onClick={handleDeleteClient}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Buyer Name <span className="text-red-500">*</span></label>
                  <input value={buyerName} onChange={(e)=>setBuyerName(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Buyer Email <span className="text-red-500">*</span></label>
                  <input value={buyerEmail} onChange={(e)=>setBuyerEmail(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="md:col-span-2 space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Buyer Address <span className="text-red-500">*</span></label>
                  <input value={buyerAddress} onChange={(e)=>setBuyerAddress(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Buyer Business Name <span className="text-red-500">*</span></label>
                  <input value={buyerBusinessName} onChange={(e)=>setBuyerBusinessName(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Buyer Phone <span className="text-red-500">*</span></label>
                  <input value={buyerPhone} onChange={(e)=>setBuyerPhone(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">PO Number <span className="text-red-500">*</span></label>
                  <input value={poNumber} onChange={(e)=>setPoNumber(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Buyer Signature (optional)</label>
                  <input type="file" accept="image/*" onChange={onBuyerSigFileChange} className="text-sm text-gray-600" />
                </div>
              </div>
            </div>

            {/* Invoice Metadata */}
            <div className="bg-yellow-50 rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Invoice</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Invoice Number <span className="text-red-500">*</span></label>
                  <input value={invoiceNumber} onChange={(e)=>setInvoiceNumber(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Currency <span className="text-red-500">*</span></label>
                  <select
                    value={currencyCode}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    {currencies.map((c: any) => (
                      <option key={c.code} value={c.code}>{c.symbol} {c.code} — {c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Issue Date <span className="text-red-500">*</span></label>
                  <input type="date" value={issueDate} onChange={(e)=>setIssueDate(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Due Date <span className="text-red-500">*</span></label>
                  <input type="date" value={dueDate} onChange={(e)=>setDueDate(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Service Period Start (optional)</label>
                  <input type="date" value={serviceFrom} onChange={(e)=>setServiceFrom(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Service Period End (optional)</label>
                  <input type="date" value={serviceTo} onChange={(e)=>setServiceTo(e.target.value)} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="md:col-span-2 space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Notes / Terms <span className="text-red-500">*</span></label>
                  <textarea value={notes} onChange={(e)=>setNotes(e.target.value)} rows={3} className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none" />
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-3">Tip: Use Service Period to show the date range you delivered the work. Leave blank for one-time invoices.</p>
            </div>

            {/* Line Items */}
            <div className="bg-yellow-50 rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Line Items</h3>
              <div className="space-y-3">
                {items.map((it, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200">
                    <input
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                      placeholder="Item description..."
                      value={it.description}
                      onChange={(e)=>updateItem(idx, { description: e.target.value })}
                    />
                    <input
                      type="number"
                      className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm text-center"
                      placeholder="Qty"
                      value={it.quantity}
                      onChange={(e)=>updateItem(idx, { quantity: Number(e.target.value) })}
                    />
                    <input
                      type="number"
                      className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm text-right"
                      placeholder="Amount"
                      value={it.unitPrice}
                      onChange={(e)=>updateItem(idx, { unitPrice: Number(e.target.value) })}
                    />
                    <button onClick={()=>removeItem(idx)} className="p-2 text-gray-400 hover:text-red-600 transition-colors">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={addItem}
                  className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg transition-all text-sm font-medium"
                >
                  <Plus className="w-4 h-4" />
                  Add Item
                </button>
              </div>

              {/* Summary / Totals */}
              <div className="mt-6 flex justify-end">
                <div className="w-full md:w-80 p-6 bg-gray-100 rounded-lg space-y-3">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-700">Subtotal</span>
                    <span className="font-medium">{currencyFormat(currencyCode, totals.subtotal)}</span>
                  </div>
                  {totals.taxName !== 'NONE' && (
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-700">{totals.taxName} ({totals.taxPercent}%)</span>
                      <span className="font-medium">{currencyFormat(currencyCode, totals.tax)}</span>
                    </div>
                  )}
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-700">Discount</span>
                    <input type="number" className="w-24 px-2 py-1 border border-gray-300 rounded text-sm text-right" value={discountAmount} onChange={(e)=>setDiscountAmount(Number(e.target.value))} />
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t border-gray-300">
                    <span className="font-semibold text-gray-900">Total</span>
                    <span className="text-xl font-bold">{currencyFormat(currencyCode, totals.total)}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-700">Amount Paid</span>
                    <input type="number" className="w-24 px-2 py-1 border border-gray-300 rounded text-sm text-right" value={amountPaid} onChange={(e)=>setAmountPaid(Number(e.target.value))} />
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t border-gray-300">
                    <span className="font-semibold text-gray-900">Amount Due</span>
                    <span className="text-lg font-bold text-red-600">{currencyFormat(currencyCode, totals.amountDue)}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">Example: Price {currencyCode} {totals.subtotal.toFixed(2)} + Tax ({totals.taxPercent}%) {currencyCode} {totals.tax.toFixed(2)} = Total {currencyCode} {totals.total.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Preview Section */}
          <div className={`${showPreview ? 'block' : 'hidden'} animate-in zoom-in-95 duration-700`}>
            <div className="flex justify-center p-10 bg-brand-gray/50 rounded-[3rem] border border-dashed border-gray-200">
              <div
                ref={previewRef}
                className="bg-brand-white p-12 shadow-2xl overflow-hidden rounded-sm"
                style={{ width: '210mm', height: '297mm' }}
              >
                {/* PDF Header */}
                <div className="flex justify-between items-start border-b border-gray-200 pb-8 mb-8">
                  <div className="flex items-center gap-4">
                    {sellerLogoUrl ? (
                      <img src={sellerLogoUrl} alt="Logo" className="h-16 w-16 object-contain" />
                    ) : (
                      <div className="h-16 w-16 bg-gray-900 flex items-center justify-center rounded">
                        <span className="text-white font-semibold text-xl">W</span>
                      </div>
                    )}
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">{sellerName}</h2>
                      <p className="text-xs text-gray-500">Billing</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <h1 className="text-4xl font-semibold tracking-tight text-gray-900">Invoice</h1>
                    <p className="text-sm font-medium text-gray-600 mt-1">{invoiceNumber}</p>
                  </div>
                </div>

                {/* Billing Parties */}
                <div className="grid grid-cols-2 gap-12 mb-12">
                  <div className="space-y-4">
                    <h4 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-gray-500">Bill From</h4>
                    <div className="text-sm font-semibold text-gray-900">{sellerBusinessName}</div>
                    <div className="text-xs font-medium text-gray-600 leading-relaxed whitespace-pre-line">{sellerAddress}</div>
                    <div className="text-xs font-medium text-gray-700">{sellerEmail}</div>
                  </div>
                  <div className="space-y-4 text-right">
                    <h4 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-gray-500">Bill To</h4>
                    <div className="text-sm font-semibold text-gray-900">{buyerBusinessName}</div>
                    <div className="text-xs font-medium text-gray-600 leading-relaxed whitespace-pre-line">{buyerAddress}</div>
                    <div className="text-xs font-medium text-gray-700">{buyerEmail}</div>
                  </div>
                </div>

                {/* Invoice Details */}
                <div className="grid grid-cols-4 gap-6 py-6 border-y border-gray-200 mb-10">
                  <div>
                    <span className="block text-[9px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Issue Date</span>
                    <span className="text-xs font-semibold text-gray-900">{issueDate}</span>
                  </div>
                  <div>
                    <span className="block text-[9px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Due Date</span>
                    <span className="text-xs font-semibold text-gray-900">{dueDate}</span>
                  </div>
                  <div>
                    <span className="block text-[9px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Currency</span>
                    <span className="text-xs font-semibold text-gray-900">{currencyCode}</span>
                  </div>
                  <div>
                    <span className="block text-[9px] font-semibold uppercase tracking-widest text-gray-500 mb-1">PO Number</span>
                    <span className="text-xs font-semibold text-gray-900">{poNumber || 'N/A'}</span>
                  </div>
                </div>

                {/* Line Items */}
                <table className="w-full mb-10">
                  <thead>
                    <tr className="bg-gray-900 text-white">
                      <th className="text-left p-4 text-[10px] font-semibold uppercase tracking-widest">Description</th>
                      <th className="text-center p-4 text-[10px] font-semibold uppercase tracking-widest w-20">Qty</th>
                      <th className="text-right p-4 text-[10px] font-semibold uppercase tracking-widest w-32">Unit Price</th>
                      <th className="text-right p-4 text-[10px] font-semibold uppercase tracking-widest w-32">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {items.map((it, i) => (
                      <tr key={i} className="group">
                        <td className="p-4">
                          <div className="text-xs font-semibold text-gray-900">{it.description}</div>
                        </td>
                        <td className="p-4 text-center text-xs font-medium text-gray-600">{it.quantity}</td>
                        <td className="p-4 text-right text-xs font-medium text-gray-600">{currencyFormat(currencyCode, it.unitPrice)}</td>
                        <td className="p-4 text-right text-xs font-semibold text-gray-900">{currencyFormat(currencyCode, it.quantity * it.unitPrice)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Totals + Notes */}
                <div className="grid grid-cols-2 gap-12 mt-auto">
                  <div className="space-y-8">
                    {notes && (
                      <div>
                        <h4 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-gray-500 mb-2">Notes</h4>
                        <p className="text-[10px] font-medium text-gray-600 leading-relaxed">{notes}</p>
                      </div>
                    )}
                    <div className="flex gap-12 pt-12">
                      <div className="space-y-4">
                        <h4 className="text-[8px] font-semibold uppercase tracking-widest text-gray-400">Authorized Signature</h4>
                        <div className="h-16 w-32 border-b border-gray-900 flex items-end pb-2">
                          {sellerSignatureUrl ? <img src={sellerSignatureUrl} className="max-h-12 object-contain" alt="Sig" /> : null}
                        </div>
                      </div>
                      <div className="space-y-4">
                        <h4 className="text-[8px] font-semibold uppercase tracking-widest text-gray-400">Client Signature</h4>
                        <div className="h-16 w-32 border-b border-gray-900 flex items-end pb-2">
                          {buyerSignatureUrl ? <img src={buyerSignatureUrl} className="max-h-12 object-contain" alt="Sig" /> : null}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gray-50 p-8 space-y-4 border border-gray-200">
                    <div className="flex justify-between items-center text-[10px] font-semibold uppercase tracking-widest text-gray-500">
                      <span>Subtotal</span>
                      <span className="text-gray-900">{currencyFormat(currencyCode, totals.subtotal)}</span>
                    </div>
                    {totals.taxName !== 'NONE' && (
                      <div className="flex justify-between items-center text-[10px] font-semibold uppercase tracking-widest text-gray-500">
                        <span>{totals.taxName} ({totals.taxPercent}%)</span>
                        <span className="text-gray-900">{currencyFormat(currencyCode, totals.tax)}</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-gray-200 pb-4">
                      <span>Discount</span>
                      <span className="text-gray-900">-{currencyFormat(currencyCode, discountAmount)}</span>
                    </div>
                    <div className="flex justify-between items-center pt-2">
                      <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-600">Total</span>
                      <span className="text-2xl font-semibold text-gray-900 tracking-tight">{currencyFormat(currencyCode, totals.total)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Invoices;


