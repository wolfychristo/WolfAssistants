import React, { useState, useEffect, useCallback } from 'react';
import { Search, Trash2, UserPlus, Users, ExternalLink, CheckCircle, XCircle, Edit2, Save, X } from 'lucide-react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface ScrapedLead {
    id: number;
    email: string | null;
    name: string | null;
    position: string | null;
    company: string | null;
    phone: string | null;
    address: string | null;
    notes: string | null;
    source_url: string;
    source_type: string;
    platform: string;
    company_data: any;
    validation_data: any;
    transferred: boolean;
    transferred_at: string | null;
    created_at: string;
}

const ScrapedLeads: React.FC = () => {
    const [leads, setLeads] = useState<ScrapedLead[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterTransferred, setFilterTransferred] = useState<string>('all');
    const [filterPlatform, setFilterPlatform] = useState<string>('all');
    const [selectedLeads, setSelectedLeads] = useState<number[]>([]);
    const [showDetails, setShowDetails] = useState<number | null>(null);
    const [editingNotes, setEditingNotes] = useState<number | null>(null);
    const [notesValue, setNotesValue] = useState<string>('');

    const loadLeads = useCallback(async () => {
        try {
            setIsLoading(true);
            const params: any = {};
            if (filterTransferred !== 'all') {
                params.transferred = filterTransferred === 'transferred';
            }
            if (filterPlatform !== 'all') {
                params.platform = filterPlatform;
            }
            
            const res = await api.get('/scraped-leads/', { params });
            const leadsData = Array.isArray(res.data) ? res.data : [];
            setLeads(leadsData);
            setSelectedLeads([]);
        } catch (e: any) {
            toast.error('Failed to load scraped leads');
            setLeads([]);
        } finally {
            setIsLoading(false);
        }
    }, [filterTransferred, filterPlatform]);

    useEffect(() => {
        loadLeads();
    }, [loadLeads]);

    const handleTransfer = async (leadIds: number[]) => {
        try {
            const res = await api.post('/scraped-leads/transfer', {
                lead_ids: leadIds,
                status: 'prospect'
            });
            
            const { transferred_count, skipped_count } = res.data;
            toast.success(`Transferred ${transferred_count} lead(s) to contacts${skipped_count > 0 ? `, skipped ${skipped_count}` : ''}`);
            await loadLeads();
        } catch (e: any) {
            const errorMsg = e?.response?.data?.detail || 'Failed to transfer leads';
            toast.error(errorMsg);
        }
    };

    const handleDelete = async (leadIds: number[]) => {
        if (!window.confirm(`Delete ${leadIds.length} lead(s)?`)) return;
        
        try {
            if (leadIds.length === 1) {
                await api.delete(`/scraped-leads/${leadIds[0]}`);
            } else {
                await api.post('/scraped-leads/delete-multiple', leadIds);
            }
            toast.success(`Deleted ${leadIds.length} lead(s)`);
            await loadLeads();
        } catch (e: any) {
            const errorMsg = e?.response?.data?.detail || 'Failed to delete leads';
            toast.error(errorMsg);
        }
    };

    const toggleSelectLead = (leadId: number) => {
        setSelectedLeads(prev => 
            prev.includes(leadId) 
                ? prev.filter(id => id !== leadId)
                : [...prev, leadId]
        );
    };

    const toggleSelectAll = () => {
        const nonTransferredLeads = filteredLeads.filter(l => !l.transferred).map(l => l.id);
        if (selectedLeads.length === nonTransferredLeads.length) {
            setSelectedLeads([]);
        } else {
            setSelectedLeads(nonTransferredLeads);
        }
    };

    const filteredLeads = leads.filter(lead => {
        const matchesSearch = !searchTerm || 
            (lead.name?.toLowerCase().includes(searchTerm.toLowerCase())) ||
            (lead.email?.toLowerCase().includes(searchTerm.toLowerCase())) ||
            (lead.company?.toLowerCase().includes(searchTerm.toLowerCase())) ||
            (lead.notes?.toLowerCase().includes(searchTerm.toLowerCase()));
        return matchesSearch;
    });

    const platforms = Array.from(new Set(leads.map(l => l.platform)));

    const handleEditNotes = (lead: ScrapedLead) => {
        setEditingNotes(lead.id);
        setNotesValue(lead.notes || '');
    };

    const handleSaveNotes = async (leadId: number) => {
        try {
            await api.patch(`/scraped-leads/${leadId}/notes`, {
                notes: notesValue
            });
            toast.success('Notes updated successfully');
            setEditingNotes(null);
            await loadLeads();
        } catch (e: any) {
            const errorMsg = e?.response?.data?.detail || 'Failed to update notes';
            toast.error(errorMsg);
        }
    };

    const handleCancelEdit = () => {
        setEditingNotes(null);
        setNotesValue('');
    };

    return (
        <div className="min-h-screen pt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Scraped Leads</h1>
                    <p className="text-gray-600">Review and transfer scraped leads to your contacts</p>
                </div>

                {/* Filters and Actions */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
                    <div className="flex flex-col lg:flex-row gap-4">
                        {/* Search */}
                        <div className="flex-1">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                <input
                                    type="text"
                                    placeholder="Search by name, email, or company..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                        </div>

                        {/* Filters */}
                        <div className="flex gap-2">
                            <select
                                value={filterTransferred}
                                onChange={(e) => setFilterTransferred(e.target.value)}
                                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="all">All Leads</option>
                                <option value="pending">Pending</option>
                                <option value="transferred">Transferred</option>
                            </select>

                            <select
                                value={filterPlatform}
                                onChange={(e) => setFilterPlatform(e.target.value)}
                                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="all">All Platforms</option>
                                {platforms.map(platform => (
                                    <option key={platform} value={platform}>
                                        {platform.charAt(0).toUpperCase() + platform.slice(1)}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Bulk Actions */}
                    {selectedLeads.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-gray-200 flex gap-2">
                            <button
                                onClick={() => handleTransfer(selectedLeads)}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                <Users className="w-4 h-4" />
                                Transfer {selectedLeads.length} Lead(s)
                            </button>
                            <button
                                onClick={() => handleDelete(selectedLeads)}
                                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                            >
                                <Trash2 className="w-4 h-4" />
                                Delete {selectedLeads.length} Lead(s)
                            </button>
                        </div>
                    )}
                </div>

                {/* Leads Table */}
                {isLoading ? (
                    <div className="text-center py-12">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <p className="mt-4 text-gray-600">Loading leads...</p>
                    </div>
                ) : filteredLeads.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                        <p className="text-gray-600">No scraped leads found</p>
                        <p className="text-sm text-gray-500 mt-2">Use the WolfAssistants extension to scrape leads</p>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left">
                                            <input
                                                type="checkbox"
                                                checked={selectedLeads.length === filteredLeads.filter(l => !l.transferred).length && filteredLeads.filter(l => !l.transferred).length > 0}
                                                onChange={toggleSelectAll}
                                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Platform</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {filteredLeads.map((lead) => (
                                        <tr key={lead.id} className={lead.transferred ? 'bg-gray-50 opacity-75' : 'hover:bg-gray-50'}>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {!lead.transferred && (
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedLeads.includes(lead.id)}
                                                        onChange={() => toggleSelectLead(lead.id)}
                                                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                    />
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm font-medium text-gray-900">{lead.name || '—'}</div>
                                                {lead.position && (
                                                    <div className="text-sm text-gray-500">{lead.position}</div>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-900">{lead.email || '—'}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-900">{lead.company || '—'}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                                                    {lead.platform}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {lead.transferred ? (
                                                    <span className="flex items-center gap-1 text-green-600">
                                                        <CheckCircle className="w-4 h-4" />
                                                        <span className="text-sm">Transferred</span>
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1 text-orange-600">
                                                        <XCircle className="w-4 h-4" />
                                                        <span className="text-sm">Pending</span>
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {new Date(lead.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <div className="flex items-center justify-end gap-2">
                                                    {showDetails === lead.id ? (
                                                        <button
                                                            onClick={() => setShowDetails(null)}
                                                            className="text-blue-600 hover:text-blue-900"
                                                        >
                                                            Hide
                                                        </button>
                                                    ) : (
                                                        <>
                                                            <button
                                                                onClick={() => setShowDetails(lead.id)}
                                                                className="text-blue-600 hover:text-blue-900"
                                                            >
                                                                Details
                                                            </button>
                                                            {!lead.transferred && (
                                                                <>
                                                                    <button
                                                                        onClick={() => handleTransfer([lead.id])}
                                                                        className="text-green-600 hover:text-green-900 flex items-center gap-1"
                                                                    >
                                                                        <UserPlus className="w-4 h-4" />
                                                                        Transfer
                                                                    </button>
                                                                    <button
                                                                        onClick={() => handleDelete([lead.id])}
                                                                        className="text-red-600 hover:text-red-900"
                                                                    >
                                                                        <Trash2 className="w-4 h-4" />
                                                                    </button>
                                                                </>
                                                            )}
                                                        </>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Lead Details */}
                        {showDetails !== null && (
                            <div className="border-t border-gray-200 p-6 bg-gray-50">
                                {(() => {
                                    const lead = leads.find(l => l.id === showDetails);
                                    if (!lead) return null;
                                    return (
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <h3 className="font-semibold text-gray-900 mb-3">Contact Information</h3>
                                                <dl className="space-y-2">
                                                    {lead.name && <div><dt className="text-sm text-gray-500">Name:</dt><dd className="text-sm text-gray-900">{lead.name}</dd></div>}
                                                    {lead.email && <div><dt className="text-sm text-gray-500">Email:</dt><dd className="text-sm text-gray-900">{lead.email}</dd></div>}
                                                    {lead.phone && <div><dt className="text-sm text-gray-500">Phone:</dt><dd className="text-sm text-gray-900">{lead.phone}</dd></div>}
                                                    {lead.position && <div><dt className="text-sm text-gray-500">Position:</dt><dd className="text-sm text-gray-900">{lead.position}</dd></div>}
                                                    {lead.company && <div><dt className="text-sm text-gray-500">Company:</dt><dd className="text-sm text-gray-900">{lead.company}</dd></div>}
                                                    {lead.address && <div><dt className="text-sm text-gray-500">Address:</dt><dd className="text-sm text-gray-900">{lead.address}</dd></div>}
                                                </dl>
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-gray-900 mb-3">Source Information</h3>
                                                <dl className="space-y-2">
                                                    <div>
                                                        <dt className="text-sm text-gray-500">Platform:</dt>
                                                        <dd className="text-sm text-gray-900 capitalize">{lead.platform}</dd>
                                                    </div>
                                                    <div>
                                                        <dt className="text-sm text-gray-500">Source Type:</dt>
                                                        <dd className="text-sm text-gray-900">{lead.source_type}</dd>
                                                    </div>
                                                    <div>
                                                        <dt className="text-sm text-gray-500">Source URL:</dt>
                                                        <dd className="text-sm text-gray-900 break-all">
                                                            <a href={lead.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center gap-1">
                                                                {lead.source_url}
                                                                <ExternalLink className="w-3 h-3" />
                                                            </a>
                                                        </dd>
                                                    </div>
                                                    <div>
                                                        <dt className="text-sm text-gray-500">Scraped:</dt>
                                                        <dd className="text-sm text-gray-900">{new Date(lead.created_at).toLocaleString()}</dd>
                                                    </div>
                                                </dl>
                                            </div>
                                            <div className="md:col-span-2">
                                                <div className="flex items-center justify-between mb-3">
                                                    <h3 className="font-semibold text-gray-900">Notes</h3>
                                                    {editingNotes !== lead.id && (
                                                        <button
                                                            onClick={() => handleEditNotes(lead)}
                                                            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-900"
                                                        >
                                                            <Edit2 className="w-4 h-4" />
                                                            Edit
                                                        </button>
                                                    )}
                                                </div>
                                                {editingNotes === lead.id ? (
                                                    <div className="space-y-2">
                                                        <textarea
                                                            value={notesValue}
                                                            onChange={(e) => setNotesValue(e.target.value)}
                                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                                            rows={6}
                                                            placeholder="Add notes about this lead..."
                                                        />
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => handleSaveNotes(lead.id)}
                                                                className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                                                            >
                                                                <Save className="w-4 h-4" />
                                                                Save
                                                            </button>
                                                            <button
                                                                onClick={handleCancelEdit}
                                                                className="flex items-center gap-1 px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm"
                                                            >
                                                                <X className="w-4 h-4" />
                                                                Cancel
                                                            </button>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="bg-white p-4 rounded border border-gray-200">
                                                        {lead.notes ? (
                                                            <pre className="text-sm text-gray-900 whitespace-pre-wrap font-sans">
                                                                {lead.notes}
                                                            </pre>
                                                        ) : (
                                                            <p className="text-sm text-gray-500 italic">No notes added yet</p>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                            {lead.company_data && (
                                                <div className="md:col-span-2">
                                                    <h3 className="font-semibold text-gray-900 mb-3">Company Data</h3>
                                                    <pre className="bg-white p-4 rounded border border-gray-200 text-xs overflow-auto">
                                                        {JSON.stringify(lead.company_data, null, 2)}
                                                    </pre>
                                                </div>
                                            )}
                                            {lead.validation_data && (
                                                <div className="md:col-span-2">
                                                    <h3 className="font-semibold text-gray-900 mb-3">Validation Results</h3>
                                                    <pre className="bg-white p-4 rounded border border-gray-200 text-xs overflow-auto">
                                                        {JSON.stringify(lead.validation_data, null, 2)}
                                                    </pre>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })()}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ScrapedLeads;

