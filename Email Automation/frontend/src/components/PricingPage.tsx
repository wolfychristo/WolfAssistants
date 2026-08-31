import React, { useState } from 'react';
import { Check, Star, Zap, Shield, Users, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const PricingPage: React.FC = () => {
  const [isAnnual, setIsAnnual] = useState(false);
  const navigate = useNavigate();

  const tiers = [
    {
      name: 'Free',
      price: { monthly: 0, annual: 0 },
      description: 'Perfect for trying out WolfAssistants',
      features: [
        '20 contacts',
        '20 emails using Wolfy AI per month',
        '50 Wolfy prompts per month',
        '5 meetings per month',
        'Basic AI-assisted email',
        'Community support'
      ],
      limitations: [
        'Limited AI capacity',
        'Basic features only',
        'No advanced analytics'
      ],
      popular: false,
      buttonText: 'Start for Free',
      buttonVariant: 'default' as const,
      buttonAction: 'navigate' as const,
      buttonTarget: '/register?plan=free'
    },
    {
      name: 'Starter',
      price: { monthly: 5, annual: 50 }, // 2 months free with annual
      description: 'Ideal for small businesses',
      features: [
        '500 AI requests per month',
        '50 emails per day',
        '200 contacts',
        '25 meetings per month',
        'AI-powered email generation',
        'Contact management',
        'Email scheduling',
        'Basic analytics',
        'Priority support'
      ],
      limitations: [],
      popular: false,
      buttonText: 'Join Beta',
      buttonVariant: 'default' as const,
      buttonAction: 'navigate' as const,
      buttonTarget: '/register?plan=starter'
    },
    {
      name: 'Professional',
      price: { monthly: 20, annual: 200 }, // 2 months free with annual
      description: 'For growing companies',
      features: [
        '2,000 AI requests per month',
        '200 emails per day',
        '1,000 contacts',
        '100 meetings per month',
        'Priority AI processing',
        'Advanced conversation memory',
        'Team collaboration',
        'Advanced analytics',
        'Meeting AI-assisted'
      ],
      limitations: [],
      popular: true,
      buttonText: 'Join Beta',
      buttonVariant: 'default' as const,
      buttonAction: 'navigate' as const,
      buttonTarget: '/register?plan=professional'
    },
    {
      name: 'Enterprise',
      price: { monthly: 99, annual: 990 }, // 2 months free with annual
      description: 'For large organizations',
      features: [
        '10,000 AI requests per month',
        '1,000 emails per day',
        '5,000 contacts',
        '500 meetings per month',
        'Custom AI training',
        'White-label options',
        'Dedicated account manager',
        'Custom integrations',
        'SLA aims to helps',
        'Advanced security'
      ],
      limitations: [],
      popular: false,
      buttonText: 'Talk to Sales',
      buttonVariant: 'outline' as const,
      buttonAction: 'mailto' as const,
      buttonTarget: 'sales@yourcompany.com'
    }
  ];

  const getPrice = (tier: typeof tiers[0]) => {
    const price = isAnnual ? tier.price.annual : tier.price.monthly;
    return isAnnual ? Math.round(price / 12) : price;
  };

  const getSavings = (tier: typeof tiers[0]) => {
    if (!isAnnual || tier.name === 'Free') return 0;
    const monthlyTotal = tier.price.monthly * 12;
    return monthlyTotal - tier.price.annual;
  };

  const handleTierClick = (tier: (typeof tiers)[number]) => {
    if (!tier?.buttonAction) return;
    if (tier.buttonAction === 'navigate' && tier.buttonTarget) {
      navigate(tier.buttonTarget);
      return;
    }
    if (tier.buttonAction === 'mailto' && tier.buttonTarget) {
      window.location.href = `mailto:${tier.buttonTarget}`;
    }
  };

  return (
    <div className="bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-base font-semibold leading-7 text-indigo-600">
            Pricing
          </h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Choose the right plan for your Business
          </p>
          <p className="mt-6 text-lg leading-8 text-gray-600">
            Start free and scale as you grow. All plans include our core AI features.
          </p>

          {/* Annual/Monthly Toggle */}
          <div className="mt-8 flex items-center justify-center space-x-4">
            <span className={isAnnual ? 'text-gray-500' : 'text-gray-900 font-semibold'}>
              Monthly
            </span>
            <button
              onClick={() => setIsAnnual(!isAnnual)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                isAnnual ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isAnnual ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={isAnnual ? 'text-gray-900 font-semibold' : 'text-gray-500'}>
              Annual
            </span>
            <span className="text-sm font-medium text-green-600 bg-green-100 px-2 py-1 rounded">
              Save up to 17%
            </span>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="mx-auto mt-16 grid max-w-lg grid-cols-1 gap-y-6 sm:mt-20 lg:mx-0 lg:max-w-none lg:grid-cols-4 lg:gap-x-8">
          {tiers.map((tier, tierIdx) => (
            <div
              key={tier.name}
              className={`relative rounded-2xl bg-white p-8 shadow-sm ring-1 ring-gray-200 ${
                tier.popular ? 'ring-2 ring-indigo-600 scale-105' : ''
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="inline-flex items-center rounded-full bg-indigo-600 px-4 py-1 text-sm font-medium text-white">
                    <Star className="w-4 h-4 mr-1" />
                    Most Popular
                  </span>
                </div>
              )}

              <div className="mb-8">
                <h3 className="text-lg font-semibold leading-8 text-gray-900">
                  {tier.name}
                </h3>
                <p className="mt-4 text-sm leading-6 text-gray-600">
                  {tier.description}
                </p>

                <div className="mt-6 flex items-baseline gap-x-1">
                  <span className="text-4xl font-bold tracking-tight text-gray-900">
                    ${getPrice(tier)}
                  </span>
                  <span className="text-sm font-semibold leading-6 text-gray-600">
                    /month
                  </span>
                </div>

                {isAnnual && getSavings(tier) > 0 && (
                  <p className="text-sm text-green-600 font-medium">
                    Save ${getSavings(tier)} annually
                  </p>
                )}
              </div>

              <div className="mb-8">
                <button
                  type="button"
                  className={`w-full rounded-md px-3 py-2 text-sm font-semibold shadow-sm ${
                    tier.buttonVariant === 'default'
                      ? 'bg-indigo-600 text-white hover:bg-indigo-500'
                      : 'border border-gray-300 text-gray-900 hover:bg-gray-50'
                  }`}
                  onClick={() => handleTierClick(tier)}
                >
                  {tier.buttonText}
                </button>
              </div>

              <ul className="space-y-3 text-sm leading-6 text-gray-600">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex gap-x-3">
                    <Check className="h-5 w-5 flex-none text-green-600" />
                    {feature}
                  </li>
                ))}
              </ul>

              {tier.limitations.length > 0 && (
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <p className="text-xs font-medium text-gray-500 mb-2">Limitations:</p>
                  <ul className="space-y-2 text-xs text-gray-400">
                    {tier.limitations.map((limitation) => (
                      <li key={limitation} className="flex gap-x-2">
                        <span className="text-red-400">•</span>
                        {limitation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Feature Comparison */}
        <div className="mx-auto mt-24 max-w-7xl">
          <h3 className="text-2xl font-bold text-center text-gray-900 mb-16">
            Compare Features
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-4 px-6 text-sm font-semibold text-gray-900">
                    Features
                  </th>
                  {tiers.map((tier) => (
                    <th
                      key={tier.name}
                      className="text-center py-4 px-6 text-sm font-semibold text-gray-900"
                    >
                      {tier.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {[
                  { feature: 'Wolfy Prompts per Month', values: ['50', '500', '2,000', '10,000'] },
                  { feature: 'Gemini Emails per Month', values: ['20', 'Unlimited', 'Unlimited', 'Unlimited'] },
                  { feature: 'Contact Storage', values: ['20', '200', '1,000', '5,000'] },
                  { feature: 'Meetings per Month', values: ['5', '25', '100', '500'] },
                  { feature: 'AI Email Generation', values: ['❌', '✅', '✅', '✅'] },
                  { feature: 'Priority Processing', values: ['❌', '❌', '✅', '✅'] },
                  { feature: 'Team Collaboration', values: ['❌', '❌', '✅', '✅'] },
                  { feature: 'API Access', values: ['❌', '❌', '✅', '✅'] },
                  { feature: 'Custom Integrations', values: ['❌', '❌', '❌', '✅'] },
                  { feature: 'Dedicated Support', values: ['❌', '❌', '❌', '✅'] }
                ].map((row, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="py-4 px-6 text-sm font-medium text-gray-900">
                      {row.feature}
                    </td>
                    {row.values.map((value, valueIndex) => (
                      <td
                        key={valueIndex}
                        className="py-4 px-6 text-center text-sm text-gray-600"
                      >
                        {value}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mx-auto mt-24 max-w-2xl">
          <h3 className="text-2xl font-bold text-center text-gray-900 mb-16">
            Frequently Asked Questions
          </h3>

          <dl className="space-y-8">
            {[
              {
                question: 'Can I change plans anytime?',
                answer: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately, and billing is prorated.'
              },
              {
                question: 'What happens if I exceed my limits?',
                answer: 'You\'ll receive a notification when approaching limits. You can either upgrade or wait until the next billing cycle.'
              },
              {
                question: 'Do you offer refunds?',
                answer: 'We offer a 30-day money-back refund policy for all paid plans. No questions asked.'
              },
              {
                question: 'Is there a setup fee?',
                answer: 'No setup fees for any plan. Start using Wolfy immediately after signing up.'
              },
              {
                question: 'What payment methods do you accept?',
                answer: 'We accept all major credit cards, PayPal, and bank transfers for annual plans.'
              }
            ].map((faq, index) => (
              <div key={index}>
                <dt className="text-sm font-semibold leading-6 text-gray-900">
                  {faq.question}
                </dt>
                <dd className="mt-2 text-sm text-gray-600">
                  {faq.answer}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
