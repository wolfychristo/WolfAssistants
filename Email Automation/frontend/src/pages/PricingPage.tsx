/**
 * Pricing Page with Referral Form
 * 
 * A comprehensive pricing page that includes the referral form card.
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import ReferralForm from '../components/ReferralForm';

const PricingPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'pricing' | 'referrals'>('pricing');

  const pricingPlans = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      description: 'Perfect for getting started',
      features: [
        '50 AI requests per month',
        '1 email account',
        'Community support',
        'Basic analytics'
      ],
      limitations: [
        'Limited to 50 requests/month',
        'Basic support only'
      ],
      popular: false,
      cta: 'Get Started Free',
      ctaVariant: 'outline' as const,
      ctaAction: 'navigate' as const,
      ctaTarget: '/register?plan=free'
    },
    {
      name: 'Starter',
      price: '$5',
      period: 'per month',
      description: 'Great for small businesses',
      features: [
        '500 AI requests per month',
        '1 email account',
        'Priority support',
        'Advanced analytics',
        'AI-assisted email'
      ],
      limitations: [],
      popular: true,
      cta: 'Join Beta',
      ctaVariant: 'primary' as const,
      ctaAction: 'navigate' as const,
      ctaTarget: '/register?plan=starter'
    },
    {
      name: 'Professional',
      price: '$20',
      period: 'per month',
      description: 'For growing businesses',
      features: [
        '2,000 AI requests per month',
        '1 email account',
        '24/7 support',
        'Advanced analytics',
        'Full AI-assisted email'
      ],
      limitations: [],
      popular: false,
      cta: 'Join Beta',
      ctaVariant: 'outline' as const,
      ctaAction: 'navigate' as const,
      ctaTarget: '/register?plan=professional'
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: 'per month',
      description: 'For large organizations',
      features: [
        '10,000 AI requests per month',
        '1 email account',
        'Dedicated support',
        'Custom analytics',
        'Advanced security'
      ],
      limitations: [],
      popular: false,
      cta: 'Talk to Sales',
      ctaVariant: 'outline' as const,
      ctaAction: 'mailto' as const,
      ctaTarget: 'sales@yourcompany.com'
    }
  ];

  const getCtaClasses = (variant: 'primary' | 'outline') => {
    const baseClasses = "w-full py-3 px-6 rounded-lg font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2";
    
    if (variant === 'primary') {
      return `${baseClasses} bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700 focus:ring-purple-500`;
    } else {
      return `${baseClasses} border-2 border-gray-300 text-gray-700 hover:border-purple-500 hover:text-purple-600 focus:ring-purple-500`;
    }
  };

  const handlePlanCta = (plan: (typeof pricingPlans)[number]) => {
    if (!plan?.ctaAction) {
      return;
    }
    if (plan.ctaAction === 'navigate' && plan.ctaTarget) {
      navigate(plan.ctaTarget);
      return;
    }
    if (plan.ctaAction === 'mailto' && plan.ctaTarget) {
      window.location.href = `mailto:${plan.ctaTarget}`;
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-3xl font-bold text-gray-900">🐺 Wolfy</h1>
            </div>
            <div className="flex items-center space-x-4">
              {user ? (
                <div className="flex items-center space-x-4">
                  <span className="text-gray-700">Welcome, {user.name || user.email}</span>
                  <button className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors">
                    Dashboard
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-4">
                  <button className="text-gray-700 hover:text-purple-600 transition-colors">
                    Sign In
                  </button>
                  <button className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors">
                    Get Started
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('pricing')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'pricing'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Pricing Plans
            </button>
            <button
              onClick={() => setActiveTab('referrals')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'referrals'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Invite Friends & Earn Credits
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {activeTab === 'pricing' ? (
          <>
            {/* Pricing Header */}
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Choose Your Perfect Plan
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Start with our free plan and scale as you grow. All plans include our core AI-powered features.
              </p>
            </div>

            {/* Pricing Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
              {pricingPlans.map((plan, index) => (
                <div
                  key={plan.name}
                  className={`relative bg-white rounded-2xl shadow-lg p-8 ${
                    plan.popular ? 'ring-2 ring-purple-500 scale-105' : ''
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                      <span className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-full text-sm font-semibold">
                        Most Popular
                      </span>
                    </div>
                  )}
                  
                  <div className="text-center mb-8">
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                    <div className="mb-2">
                      <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                      <span className="text-gray-600 ml-2">{plan.period}</span>
                    </div>
                    <p className="text-gray-600">{plan.description}</p>
                  </div>

                  <ul className="space-y-4 mb-8">
                    {plan.features.map((feature, featureIndex) => (
                      <li key={featureIndex} className="flex items-start">
                        <svg className="w-5 h-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-gray-700">{feature}</span>
                      </li>
                    ))}
                    {plan.limitations.map((limitation, limitationIndex) => (
                      <li key={limitationIndex} className="flex items-start">
                        <svg className="w-5 h-5 text-red-500 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                        <span className="text-gray-500">{limitation}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    type="button"
                    className={getCtaClasses(plan.ctaVariant)}
                    onClick={() => handlePlanCta(plan)}
                  >
                    {plan.cta}
                  </button>
                </div>
              ))}
            </div>

            {/* FAQ Section */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-8 text-center">Frequently Asked Questions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">Can I change plans anytime?</h4>
                  <p className="text-gray-600">Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately.</p>
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">Is there a free trial?</h4>
                  <p className="text-gray-600">Yes! All paid plans come with a 14-day free trial. No credit card required.</p>
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">What happens to my data?</h4>
                  <p className="text-gray-600">Your data is always yours. You can export it anytime, even if you cancel.</p>
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">Do you offer refunds?</h4>
                  <p className="text-gray-600">Yes! We offer a 30-day money-back refund policy on all paid plans.</p>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Referral Tab */
          <div className="max-w-4xl mx-auto quick-tour-referral">
            <ReferralForm />
          </div>
        )}
      </div>
    </div>
  )}
export default PricingPage;
