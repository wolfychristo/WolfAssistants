import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Shield, TrendingUp, RefreshCw, Copy, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface SPFDKIMStatus {
  domain: string;
  spf: {
    configured: boolean;
    error: string | null;
    last_checked: string | null;
  };
  dkim: {
    configured: boolean;
    error: string | null;
    last_checked: string | null;
    selector_used?: string | null;
  };
  setup_guide: {
    spf: {
      description: string;
      record_type: string;
      name: string;
      value: string;
      ttl: string;
      common_providers?: { [key: string]: string };
      instructions: string[];
    } | string; // Support both old string format and new object format
    dkim: {
      description: string;
      record_type: string;
      common_selectors: string[];
      instructions: string[];
      provider_links?: { [key: string]: string };
    } | string; // Support both old string format and new object format
  };
}

interface ReputationMetrics {
  mailbox: string;
  reputation_score: number;
  metrics: {
    total_sent: number;
    total_delivered: number;
    total_bounced: number;
    total_complained: number;
    delivery_rate: number;
    bounce_rate: number;
    complaint_rate: number;
  };
  rate_limiting: {
    cold_sends_today: number;
    max_cold_sends_per_day: number;
    recommended_limit: number;
  };
  status: {
    is_throttled: boolean;
    throttle_reason: string | null;
    throttle_until: string | null;
  };
  spf_dkim: {
    spf_configured: boolean;
    dkim_configured: boolean;
  };
  last_updated: string | null;
}

const DeliverabilityDashboard: React.FC = () => {
  const [spfDkimStatus, setSpfDkimStatus] = useState<SPFDKIMStatus | null>(null);
  const [reputation, setReputation] = useState<ReputationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingSpfDkim, setCheckingSpfDkim] = useState(false);
  const [expandedSpf, setExpandedSpf] = useState(false);
  const [expandedDkim, setExpandedDkim] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [reputationRes, spfDkimRes] = await Promise.all([
        api.get('/deliverability/reputation').catch((error: any) => {
          if (error?.response?.status === 400) {
            toast.error(error?.response?.data?.detail || 'SMTP from address not configured. Please configure your email settings first.');
          }
          return { data: null };
        }),
        api.get('/deliverability/spf-dkim-status').catch((error: any) => {
          if (error?.response?.status === 400) {
            toast.error(error?.response?.data?.detail || 'SMTP from address not configured. Please configure your email settings first.');
          }
          return { data: null };
        })
      ]);
      
      if (reputationRes.data) {
        setReputation(reputationRes.data);
      }
      if (spfDkimRes.data && spfDkimRes.data.spf && spfDkimRes.data.dkim) {
        setSpfDkimStatus(spfDkimRes.data);
      }
    } catch (error: any) {
      toast.error('Failed to load deliverability data');
    } finally {
      setLoading(false);
    }
  };

  const checkSpfDkim = async () => {
    try {
      setCheckingSpfDkim(true);
      const res = await api.get('/deliverability/spf-dkim-status');
      setSpfDkimStatus(res.data);
      toast.success('SPF/DKIM status updated');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to check SPF/DKIM status');
    } finally {
      setCheckingSpfDkim(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getReputationColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50';
    if (score >= 60) return 'text-yellow-600 bg-yellow-50';
    if (score >= 40) return 'text-orange-600 bg-orange-50';
    return 'text-red-600 bg-red-50';
  };

  const getReputationLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Poor';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Email Deliverability</h2>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center space-x-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Show message if SMTP is not configured */}
      {!spfDkimStatus && !reputation && !loading && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <h3 className="font-medium text-yellow-900 mb-1">Email Settings Required</h3>
              <p className="text-sm text-yellow-700">
                Please configure your SMTP email settings in your profile to view deliverability metrics and SPF/DKIM status.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SPF/DKIM Status */}
      {spfDkimStatus && spfDkimStatus.spf && spfDkimStatus.dkim && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
              <Shield className="w-5 h-5" />
              <span>SPF/DKIM Configuration</span>
            </h3>
            <button
              onClick={checkSpfDkim}
              disabled={checkingSpfDkim}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {checkingSpfDkim ? 'Checking...' : 'Check Status'}
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* SPF Card */}
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {spfDkimStatus.spf?.configured ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <span className="font-medium">SPF Record</span>
                </div>
                {!spfDkimStatus.spf?.configured && spfDkimStatus.setup_guide?.spf && typeof spfDkimStatus.setup_guide.spf === 'object' && (
                  <button
                    onClick={() => setExpandedSpf(!expandedSpf)}
                    className="text-blue-600 hover:text-blue-700 text-sm flex items-center space-x-1"
                  >
                    <span>Setup Guide</span>
                    {expandedSpf ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                )}
              </div>
              {spfDkimStatus.spf?.configured ? (
                <div>
                  <p className="text-sm text-gray-600">Configured ✓</p>
                  {spfDkimStatus.spf?.last_checked && (
                    <p className="text-xs text-gray-500 mt-1">
                      Last checked: {new Date(spfDkimStatus.spf.last_checked).toLocaleString()}
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <p className="text-sm text-red-600 mb-2">{spfDkimStatus.spf?.error || 'Not configured'}</p>
                  {typeof spfDkimStatus.setup_guide?.spf === 'string' ? (
                    <p className="text-xs text-gray-500">{spfDkimStatus.setup_guide.spf}</p>
                  ) : expandedSpf && spfDkimStatus.setup_guide?.spf && typeof spfDkimStatus.setup_guide.spf === 'object' ? (
                    <div className="mt-3 space-y-3 text-sm">
                      <div className="bg-gray-50 p-3 rounded border">
                        <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                          <div><strong>Type:</strong> {spfDkimStatus.setup_guide.spf.record_type}</div>
                          <div><strong>Name:</strong> {spfDkimStatus.setup_guide.spf.name}</div>
                          <div><strong>TTL:</strong> {spfDkimStatus.setup_guide.spf.ttl}</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <code className="flex-1 bg-white p-2 rounded border text-xs break-all">
                            {typeof spfDkimStatus.setup_guide.spf === 'object' ? spfDkimStatus.setup_guide.spf.value : ''}
                          </code>
                          {typeof spfDkimStatus.setup_guide.spf === 'object' && (
                            <button
                              onClick={() => {
                                const spfGuide = spfDkimStatus.setup_guide.spf;
                                if (typeof spfGuide === 'object' && spfGuide.value) {
                                  navigator.clipboard.writeText(spfGuide.value);
                                  toast.success('SPF record copied to clipboard');
                                }
                              }}
                              className="p-2 hover:bg-gray-200 rounded"
                              title="Copy SPF record"
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                      {spfDkimStatus.setup_guide.spf.common_providers && (
                        <div>
                          <p className="font-medium mb-2">Common Provider Examples:</p>
                          <div className="space-y-1">
                            {Object.entries(spfDkimStatus.setup_guide.spf.common_providers).map(([provider, value]) => (
                              <div key={provider} className="flex items-center justify-between bg-white p-2 rounded border text-xs">
                                <span className="capitalize">{provider}:</span>
                                <code className="text-xs">{value}</code>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <div>
                        <p className="font-medium mb-2">Step-by-Step Instructions:</p>
                        <ol className="list-decimal list-inside space-y-1 text-xs text-gray-700">
                          {spfDkimStatus.setup_guide.spf.instructions?.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          )) || <li>No instructions available</li>}
                        </ol>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
            
            {/* DKIM Card */}
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {spfDkimStatus.dkim?.configured ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <span className="font-medium">DKIM Record</span>
                </div>
                {!spfDkimStatus.dkim?.configured && spfDkimStatus.setup_guide?.dkim && typeof spfDkimStatus.setup_guide.dkim === 'object' && (
                  <button
                    onClick={() => setExpandedDkim(!expandedDkim)}
                    className="text-blue-600 hover:text-blue-700 text-sm flex items-center space-x-1"
                  >
                    <span>Setup Guide</span>
                    {expandedDkim ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                )}
              </div>
              {spfDkimStatus.dkim?.configured ? (
                <div>
                  <p className="text-sm text-gray-600">Configured ✓</p>
                  {spfDkimStatus.dkim?.selector_used && (
                    <p className="text-xs text-gray-500 mt-1">
                      Selector: <code className="bg-gray-100 px-1 rounded">{spfDkimStatus.dkim.selector_used}</code>
                    </p>
                  )}
                  {spfDkimStatus.dkim?.last_checked && (
                    <p className="text-xs text-gray-500 mt-1">
                      Last checked: {new Date(spfDkimStatus.dkim.last_checked).toLocaleString()}
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <p className="text-sm text-red-600 mb-2">{spfDkimStatus.dkim?.error || 'Not configured'}</p>
                  {typeof spfDkimStatus.setup_guide?.dkim === 'string' ? (
                    <p className="text-xs text-gray-500">{spfDkimStatus.setup_guide.dkim}</p>
                  ) : expandedDkim && spfDkimStatus.setup_guide?.dkim && typeof spfDkimStatus.setup_guide.dkim === 'object' ? (
                    <div className="mt-3 space-y-3 text-sm">
                      <div className="bg-gray-50 p-3 rounded border">
                        <p className="text-xs mb-2"><strong>Record Type:</strong> {spfDkimStatus.setup_guide.dkim.record_type}</p>
                        <p className="text-xs mb-2"><strong>Common Selectors:</strong> {spfDkimStatus.setup_guide.dkim.common_selectors?.join(', ') || 'N/A'}</p>
                        <p className="text-xs text-gray-600">
                          Contact your email provider to get your DKIM public key. The record name will be: <code>[selector]._domainkey.{spfDkimStatus.domain}</code>
                        </p>
                      </div>
                      {spfDkimStatus.setup_guide.dkim.provider_links && (
                        <div>
                          <p className="font-medium mb-2">Provider Documentation:</p>
                          <div className="space-y-1">
                            {Object.entries(spfDkimStatus.setup_guide.dkim.provider_links).map(([provider, url]) => (
                              <a
                                key={provider}
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 text-xs"
                              >
                                <span className="capitalize">{provider} DKIM Setup</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                      <div>
                        <p className="font-medium mb-2">Step-by-Step Instructions:</p>
                        <ol className="list-decimal list-inside space-y-1 text-xs text-gray-700">
                          {spfDkimStatus.setup_guide.dkim.instructions?.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          )) || <li>No instructions available</li>}
                        </ol>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Reputation Metrics */}
      {reputation && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
            <TrendingUp className="w-5 h-5" />
            <span>Sender Reputation</span>
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">Reputation Score</span>
                <span className={`px-2 py-1 rounded text-sm font-medium ${getReputationColor(reputation.reputation_score)}`}>
                  {getReputationLabel(reputation.reputation_score)}
                </span>
              </div>
              <div className="text-3xl font-bold text-gray-900">{reputation.reputation_score.toFixed(1)}</div>
              <div className="text-xs text-gray-500 mt-1">out of 100</div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <div className="text-sm text-gray-600 mb-2">Delivery Rate</div>
              <div className="text-3xl font-bold text-green-600">{reputation.metrics.delivery_rate.toFixed(1)}%</div>
              <div className="text-xs text-gray-500 mt-1">
                {reputation.metrics.total_delivered.toLocaleString()} / {reputation.metrics.total_sent.toLocaleString()} delivered
              </div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <div className="text-sm text-gray-600 mb-2">Bounce Rate</div>
              <div className={`text-3xl font-bold ${reputation.metrics.bounce_rate > 5 ? 'text-red-600' : reputation.metrics.bounce_rate > 2 ? 'text-yellow-600' : 'text-green-600'}`}>
                {reputation.metrics.bounce_rate.toFixed(2)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {reputation.metrics.total_bounced.toLocaleString()} bounced
              </div>
            </div>
          </div>

          {/* Rate Limiting */}
          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 mb-3">Daily Cold Send Limits</h4>
            <div className="flex items-center space-x-4">
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Used today</span>
                  <span className="font-medium">
                    {reputation.rate_limiting.cold_sends_today} / {reputation.rate_limiting.max_cold_sends_per_day}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      (reputation.rate_limiting.cold_sends_today / reputation.rate_limiting.max_cold_sends_per_day) > 0.8
                        ? 'bg-red-500'
                        : (reputation.rate_limiting.cold_sends_today / reputation.rate_limiting.max_cold_sends_per_day) > 0.6
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{
                      width: `${Math.min(100, (reputation.rate_limiting.cold_sends_today / reputation.rate_limiting.max_cold_sends_per_day) * 100)}%`
                    }}
                  />
                </div>
              </div>
            </div>
            {reputation.rate_limiting.recommended_limit !== reputation.rate_limiting.max_cold_sends_per_day && (
              <p className="text-xs text-gray-500 mt-2">
                Recommended limit: {reputation.rate_limiting.recommended_limit} per day (based on reputation)
              </p>
            )}
          </div>

          {/* Throttle Status */}
          {reputation.status.is_throttled && (
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
                <div>
                  <p className="font-medium text-yellow-900">Sending Temporarily Paused</p>
                  <p className="text-sm text-yellow-700">{reputation.status.throttle_reason}</p>
                  {reputation.status.throttle_until && (
                    <p className="text-xs text-yellow-600 mt-1">
                      Resumes: {new Date(reputation.status.throttle_until).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DeliverabilityDashboard;

