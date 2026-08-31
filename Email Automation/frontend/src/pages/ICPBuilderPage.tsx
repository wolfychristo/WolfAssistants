import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Sparkles, Save, Target, Building2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface BusinessProfile {
  product_description: string;
  target_market: string;
  geographic_market: string;
  price_range: string;
  value_proposition: string;
  brand_voice: string;
  approved_case_studies: string;
  exclusions: string;
}

interface ICPConfig {
  name: string;
  raw_prompt: string;
  structured_criteria: any;
  scoring_weights: any;
}

const ICPBuilderPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'icp' | 'business'>('icp');
  const [icpPrompt, setIcpPrompt] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [icpResult, setIcpResult] = useState<ICPConfig | null>(null);

  const [profile, setProfile] = useState<BusinessProfile>({
    product_description: '',
    target_market: '',
    geographic_market: '',
    price_range: '',
    value_proposition: '',
    brand_voice: 'Professional',
    approved_case_studies: '',
    exclusions: ''
  });
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchActiveICP();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await axios.get('/api/v1/sales-agent/profile');
      if (res.data) {
        setProfile(res.data);
      }
    } catch (err) {
      console.error('Failed to fetch business profile', err);
    }
  };

  const fetchActiveICP = async () => {
    try {
      const res = await axios.get('/api/v1/sales-agent/icp');
      if (res.data && res.data.structured_criteria) {
        setIcpResult({
          name: res.data.name,
          raw_prompt: res.data.raw_prompt,
          structured_criteria: res.data.structured_criteria,
          scoring_weights: res.data.scoring_weights
        });
        setIcpPrompt(res.data.raw_prompt || '');
      }
    } catch (err) {
      console.error('Failed to fetch ICP', err);
    }
  };

  const handleParseICP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!icpPrompt.trim()) {
      toast.error('Please describe your target prospect criteria');
      return;
    }

    setIsParsing(true);
    try {
      const res = await axios.post('/api/v1/sales-agent/icp/parse', { prompt: icpPrompt });
      setIcpResult({
        name: res.data.name,
        raw_prompt: res.data.raw_prompt,
        structured_criteria: res.data.structured_criteria,
        scoring_weights: res.data.scoring_weights
      });
      toast.success('ICP targeting parameters created successfully!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to generate ICP criteria');
    } finally {
      setIsParsing(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      await axios.post('/api/v1/sales-agent/profile', profile);
      toast.success('Business context & sales memory saved!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to save business profile');
    } finally {
      setIsSavingProfile(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 pt-20 pb-12">
        
        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
              <Target className="w-8 h-8 text-blue-600" />
              Ideal Customer Profile (ICP) Builder
            </h1>
            <p className="text-gray-600 mt-1">
              Configure your ideal customer parameters and sales business context.
            </p>
          </div>

          <div className="flex bg-gray-100 p-1 rounded-lg border border-gray-200 self-start md:self-auto">
            <button
              onClick={() => setActiveTab('icp')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === 'icp'
                  ? 'bg-white text-blue-600 shadow-sm font-semibold'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              ICP Builder
            </button>
            <button
              onClick={() => setActiveTab('business')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === 'business'
                  ? 'bg-white text-blue-600 shadow-sm font-semibold'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Business Context
            </button>
          </div>
        </div>

        {/* Tab 1: ICP Builder */}
        {activeTab === 'icp' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-6 space-y-6">
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-2 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-blue-600" />
                  Describe Your Target Customer
                </h2>
                <p className="text-gray-600 text-sm mb-4">
                  Describe your ideal prospects in plain text. Criteria will be parsed into industry, role, size, and scoring rules.
                </p>

                <form onSubmit={handleParseICP} className="space-y-4">
                  <textarea
                    rows={6}
                    value={icpPrompt}
                    onChange={(e) => setIcpPrompt(e.target.value)}
                    placeholder="E.g., B2B SaaS companies in the US or India with 10-100 employees, targeting Founders, CTOs, or VPs of Sales looking to automate outreach..."
                    className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />

                  <button
                    type="submit"
                    disabled={isParsing}
                    className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  >
                    {isParsing ? (
                      <>
                        <Sparkles className="w-5 h-5 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        Build ICP Criteria
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>

            {/* Results Column */}
            <div className="lg:col-span-6">
              {icpResult ? (
                <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-6">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                    <div>
                      <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Active ICP Profile</span>
                      <h3 className="text-xl font-bold text-gray-900 mt-1">{icpResult.name}</h3>
                    </div>
                    <span className="px-3 py-1 bg-green-50 text-green-700 border border-green-200 text-xs font-semibold rounded-full">
                      Active
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                      <span className="text-gray-500 text-xs block mb-1">Target Roles</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {(icpResult.structured_criteria?.target_roles || ['CTO', 'Founder']).map((r: string, idx: number) => (
                          <span key={idx} className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-100 rounded text-xs">
                            {r}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                      <span className="text-gray-500 text-xs block mb-1">Company Size</span>
                      <span className="text-gray-900 font-medium">{icpResult.structured_criteria?.company_size || '10-100 employees'}</span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-gray-700">0–100 Scoring Weights</h4>
                    <div className="space-y-2">
                      {Object.entries(icpResult.scoring_weights || {}).map(([key, weight]) => (
                        <div key={key} className="flex items-center justify-between text-xs bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
                          <span className="text-gray-600 capitalize">{key.replace('_', ' ')} Fit</span>
                          <span className="font-semibold text-blue-600">+{String(weight)} pts</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-12 text-center text-gray-500 space-y-3">
                  <Target className="w-12 h-12 mx-auto text-gray-400" />
                  <p className="text-sm">No active ICP generated yet. Enter your criteria on the left to begin.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Business Profile */}
        {activeTab === 'business' && (
          <form onSubmit={handleSaveProfile} className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-600" />
              Business Context & Memory
            </h2>
            <p className="text-gray-600 text-sm mb-6">
              Configure factual background on your offer and brand voice.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                  Product / Service Description
                </label>
                <textarea
                  rows={3}
                  value={profile.product_description}
                  onChange={(e) => setProfile({ ...profile, product_description: e.target.value })}
                  placeholder="E.g., Custom software development, B2B sales automation..."
                  className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                  Value Proposition
                </label>
                <textarea
                  rows={3}
                  value={profile.value_proposition}
                  onChange={(e) => setProfile({ ...profile, value_proposition: e.target.value })}
                  placeholder="E.g., Increase conversion rate by 40% with zero extra SDR headcount..."
                  className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                  Price Range
                </label>
                <input
                  type="text"
                  value={profile.price_range}
                  onChange={(e) => setProfile({ ...profile, price_range: e.target.value })}
                  placeholder="E.g., $5,000 - $25,000"
                  className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                  Brand Voice
                </label>
                <select
                  value={profile.brand_voice}
                  onChange={(e) => setProfile({ ...profile, brand_voice: e.target.value })}
                  className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="Professional">Professional & Direct</option>
                  <option value="Consultative">Consultative & Helpful</option>
                  <option value="Casual">Casual & Friendly</option>
                  <option value="Executive">Executive & Authoritative</option>
                </select>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100 flex justify-end">
              <button
                type="submit"
                disabled={isSavingProfile}
                className="py-2.5 px-6 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm flex items-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                {isSavingProfile ? 'Saving...' : 'Save Context'}
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
};

export default ICPBuilderPage;
