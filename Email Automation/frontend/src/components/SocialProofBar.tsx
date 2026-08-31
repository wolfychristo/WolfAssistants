import React from 'react';

export const SocialProofBar: React.FC = () => {
  const stats = [
    { label: '500+', sublabel: 'Users' },
    { label: '10,000+', sublabel: 'Emails Sent' },
    { label: '99.9%', sublabel: 'Delivery' },
    { label: '$2M+', sublabel: 'Revenue Generated' },
  ];

  return (
    <section className="py-12 border-t border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-center gap-12">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <div className="text-2xl font-bold text-blue-600 mb-1">
                {stat.label}
              </div>
              <div className="text-sm text-gray-600 font-medium">
                {stat.sublabel}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
