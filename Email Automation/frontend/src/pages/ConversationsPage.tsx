import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MessageSquare, Send, CheckCircle2, AlertTriangle, HelpCircle, Sparkles, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

interface Conversation {
  id: number;
  prospect: {
    id: number;
    name: string;
    email: string;
    company: string;
    title: string;
    icp_score: number;
    stage: string;
  };
  inbound_message: string;
  intent: string;
  confidence_score: number;
  recommended_action: string;
  suggested_reply: string;
  approval_status: string;
  created_at: string;
}

const ConversationsPage: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [editedReply, setEditedReply] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isApproving, setIsApproving] = useState(false);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    setIsLoading(true);
    try {
      const res = await axios.get('/api/v1/replies/conversations');
      const data = Array.isArray(res.data) ? res.data : [];
      setConversations(data);
      if (data.length > 0) {
        setSelectedConv(data[0]);
        setEditedReply(data[0]?.suggested_reply || '');
      } else {
        setSelectedConv(null);
        setEditedReply('');
      }
    } catch (err) {
      console.error('Failed to fetch conversations', err);
      toast.error('Failed to load conversations');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (conv: Conversation) => {
    setSelectedConv(conv);
    setEditedReply(conv?.suggested_reply || '');
  };

  const handleApproveAndSend = async () => {
    if (!selectedConv) return;
    setIsApproving(true);
    try {
      await axios.post(`/api/v1/replies/${selectedConv.id}/approve-and-send`, {
        edited_reply: editedReply
      });
      toast.success('Reply approved and sent!');
      fetchConversations();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to approve reply');
    } finally {
      setIsApproving(false);
    }
  };

  const getIntentBadge = (intent: string) => {
    switch (intent) {
      case 'Interested':
        return <span className="px-2.5 py-1 bg-green-50 text-green-700 border border-green-200 text-xs font-semibold rounded-full flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Interested</span>;
      case 'Asking Pricing':
        return <span className="px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold rounded-full flex items-center gap-1"><HelpCircle className="w-3.5 h-3.5" /> Asking Pricing</span>;
      case 'Objection':
        return <span className="px-2.5 py-1 bg-red-50 text-red-700 border border-red-200 text-xs font-semibold rounded-full flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> Objection</span>;
      default:
        return <span className="px-2.5 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full">{intent || 'Interested'}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 pt-20 pb-12">
        
        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
              <MessageSquare className="w-8 h-8 text-blue-600" />
              Conversation Center & Reply Approvals
            </h1>
            <p className="text-gray-600 mt-1">
              Review inbound prospect intent classifications and approve AI response drafts.
            </p>
          </div>

          <button
            onClick={fetchConversations}
            className="p-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg transition-colors shadow-sm"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Content Split Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-230px)]">
          
          {/* Left Panel: Conversation List */}
          <div className="lg:col-span-5 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Inbound Prospects ({conversations.length})
              </span>
            </div>

            <div className="overflow-y-auto divide-y divide-gray-100 flex-1">
              {conversations.length === 0 ? (
                <div className="p-12 text-center text-gray-500">
                  {isLoading ? 'Loading active conversations...' : 'No inbound replies detected yet.'}
                </div>
              ) : (
                conversations.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => handleSelect(c)}
                    className={`p-4 cursor-pointer transition-all hover:bg-gray-50 ${
                      selectedConv?.id === c.id ? 'bg-blue-50/60 border-l-4 border-blue-600' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-gray-900 text-sm">
                        {c.prospect?.name || 'Prospect'}
                      </h4>
                      {getIntentBadge(c.intent)}
                    </div>

                    <p className="text-xs text-gray-500 mb-2 truncate">
                      {c.prospect?.company || 'Company'} · {c.prospect?.title || 'Executive'}
                    </p>

                    <p className="text-xs text-gray-700 line-clamp-2 italic bg-gray-50 p-2.5 rounded-md border border-gray-200">
                      "{c.inbound_message || ''}"
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Right Panel: Detail & Approval Workflow */}
          <div className="lg:col-span-7 bg-white border border-gray-200 rounded-lg shadow-sm p-6 flex flex-col justify-between overflow-y-auto space-y-6">
            {selectedConv ? (
              <>
                <div className="space-y-6">
                  {/* Prospect Card */}
                  <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center font-bold text-base">
                        {selectedConv.prospect?.name ? selectedConv.prospect.name[0].toUpperCase() : 'P'}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-900 text-base">{selectedConv.prospect?.name || 'Prospect'}</h3>
                        <p className="text-xs text-gray-500">
                          {selectedConv.prospect?.title || 'Executive'} at {selectedConv.prospect?.company || 'Company'}
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-gray-500 block">ICP Fit Score</span>
                      <span className="text-sm font-bold text-blue-600">{selectedConv.prospect?.icp_score ?? 80}/100</span>
                    </div>
                  </div>

                  {/* AI Intent & Recommendation Banner */}
                  <div className="bg-blue-50/60 border border-blue-200 p-4 rounded-lg space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-blue-700 uppercase tracking-wider">
                      <Sparkles className="w-4 h-4 text-blue-600" />
                      AI Intent Analysis ({Math.round((selectedConv.confidence_score || 0.9) * 100)}% Confidence)
                    </div>
                    <p className="text-sm text-gray-800">
                      <span className="font-semibold text-gray-900">Recommended Action:</span> {selectedConv.recommended_action || 'Review reply'}
                    </p>
                  </div>

                  {/* Message History Thread */}
                  <div className="space-y-3">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Inbound Message</span>
                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 text-sm text-gray-800 leading-relaxed">
                      {selectedConv.inbound_message || ''}
                    </div>
                  </div>

                  {/* AI Suggested Response Draft */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider block">
                        Suggested Reply Draft
                      </span>
                      <span className="text-xs text-gray-500">Edit text before approving</span>
                    </div>

                    <textarea
                      rows={6}
                      value={editedReply}
                      onChange={(e) => setEditedReply(e.target.value)}
                      className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 leading-relaxed"
                    />
                  </div>
                </div>

                {/* Approve & Send Action Button */}
                <div className="pt-4 border-t border-gray-100 flex justify-end">
                  <button
                    onClick={handleApproveAndSend}
                    disabled={isApproving}
                    className="py-2.5 px-6 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                    {isApproving ? 'Sending...' : 'Approve & Send Reply'}
                  </button>
                </div>
              </>
            ) : (
              <div className="m-auto text-center text-gray-500">
                Select a conversation from the left to view details and approve replies.
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};

export default ConversationsPage;
