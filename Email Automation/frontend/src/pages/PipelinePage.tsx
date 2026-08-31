import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Columns, Calendar, User, Building } from 'lucide-react';

interface OppItem {
  id: number;
  prospect_id: number;
  title: string;
  prospect_name: string;
  company_name: string;
  estimated_value: number;
  stage: string;
  meeting_date: string | null;
  notes: string | null;
}

interface PipelineStages {
  [key: string]: OppItem[];
}

const PipelinePage: React.FC = () => {
  const [pipeline, setPipeline] = useState<PipelineStages>({
    'Qualified Opportunity': [],
    'Meeting Booked': [],
    'Proposal': [],
    'Won': [],
    'Lost': []
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchPipeline();
  }, []);

  const fetchPipeline = async () => {
    setIsLoading(true);
    try {
      const res = await axios.get('/api/v1/command-center/pipeline');
      setPipeline(res.data || {});
    } catch (err) {
      console.error('Failed to fetch pipeline', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getStageHeaderColor = (stageName: string) => {
    switch (stageName) {
      case 'Qualified Opportunity': return 'text-blue-700';
      case 'Meeting Booked': return 'text-purple-700';
      case 'Proposal': return 'text-amber-700';
      case 'Won': return 'text-green-700';
      case 'Lost': return 'text-gray-500';
      default: return 'text-gray-700';
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 space-y-6 pt-20 pb-12">
        
        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
              <Columns className="w-8 h-8 text-blue-600" />
              Sales Opportunity Pipeline
            </h1>
            <p className="text-gray-600 mt-1">
              Track qualified sales conversations and deal progression.
            </p>
          </div>
        </div>

        {/* Pipeline Kanban Columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 overflow-x-auto pb-6">
          {Object.entries(pipeline).map(([stageName, items]) => {
            const totalValue = items.reduce((acc, curr) => acc + (curr.estimated_value || 0), 0);

            return (
              <div key={stageName} className="bg-gray-50 border border-gray-200 rounded-lg p-4 flex flex-col h-[calc(100vh-230px)] min-w-[280px]">
                {/* Column Header */}
                <div className="flex items-center justify-between border-b border-gray-200 pb-3 mb-4">
                  <div>
                    <h3 className={`font-bold text-sm ${getStageHeaderColor(stageName)}`}>{stageName}</h3>
                    <span className="text-xs text-gray-500 mt-0.5 block">
                      {items.length} deals · ${totalValue.toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Cards List */}
                <div className="space-y-3 overflow-y-auto flex-1 pr-1">
                  {items.length === 0 ? (
                    <div className="p-8 text-center text-xs text-gray-400 border border-dashed border-gray-200 rounded-lg">
                      No deals in this stage
                    </div>
                  ) : (
                    items.map((card) => (
                      <div
                        key={card.id}
                        className="bg-white border border-gray-200 hover:border-blue-300 rounded-lg p-4 space-y-3 shadow-sm transition-all"
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-gray-900 text-sm">{card.title}</h4>
                          <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-0.5 rounded border border-green-200">
                            ${card.estimated_value?.toLocaleString() || '10,000'}
                          </span>
                        </div>

                        <div className="space-y-1.5 text-xs text-gray-600">
                          <div className="flex items-center gap-1.5">
                            <User className="w-3.5 h-3.5 text-gray-400" />
                            <span>{card.prospect_name}</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Building className="w-3.5 h-3.5 text-gray-400" />
                            <span>{card.company_name}</span>
                          </div>
                          {card.meeting_date && (
                            <div className="flex items-center gap-1.5 text-purple-700">
                              <Calendar className="w-3.5 h-3.5" />
                              <span>{new Date(card.meeting_date).toLocaleDateString()}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
};

export default PipelinePage;
