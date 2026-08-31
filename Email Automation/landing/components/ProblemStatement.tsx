import { Clock, TrendingDown, DollarSign } from 'lucide-react';

export const ProblemStatement = () => {
  const stats = [
    {
      number: '47',
      unit: 'HOURS',
      label: 'Response Time',
      sublabel: 'Industry Average',
      icon: Clock,
    },
    {
      number: '68%',
      unit: '',
      label: 'Ghosting Rate',
      sublabel: 'Prospects Go Cold',
      icon: TrendingDown,
    },
    {
      number: '$1.2T',
      unit: '',
      label: 'Lost Annually',
      sublabel: 'Due to Bad Communication',
      icon: DollarSign,
    },
  ];

  return (
    <section className="py-24 px-6 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900 leading-tight">
            You're Losing Deals While
            <br />
            <span className="text-blue-600">Switching Between 7 Tools</span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
            The average founder wastes <span className="text-blue-600 font-semibold">47 hours per month</span> on context switching.
            That's <span className="text-blue-600 font-semibold">11 full work days</span> spent juggling tools instead of closing deals.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div 
                key={index} 
                className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-100 text-blue-600 mb-6">
                  <Icon className="w-6 h-6" />
                </div>
                
                <div className="text-4xl font-bold text-gray-900 mb-2">
                  {stat.number}
                  {stat.unit && (
                    <span className="text-xl text-gray-600 ml-2 font-medium">
                      {stat.unit}
                    </span>
                  )}
                </div>
                
                <div className="text-lg font-semibold text-gray-900 mb-1">
                  {stat.label}
                </div>
                <div className="text-sm text-gray-600">
                  {stat.sublabel}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
