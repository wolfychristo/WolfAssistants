import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Edit, Trash2, Search, Filter, Download, Upload } from 'lucide-react';
import { contactsAPI } from '../services/api';
import toast from 'react-hot-toast';
import ShareLink from '../components/ShareLink';

interface Contact {
    id: number;
	public_id?: string;
	name: string;
	email: string;
	company: string;
	phone: string;
	position: string;
	status: 'active' | 'inactive' | 'prospect';
    last_contact: string;
	notes: string;
    computed_status?: string | null;
}

const Contacts: React.FC = () => {
    const { publicId } = useParams<{ publicId?: string }>();
    const navigate = useNavigate();
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const fileInputRef = React.useRef<HTMLInputElement | null>(null);
    
    // Load specific contact by public_id if in URL
    useEffect(() => {
        if (publicId) {
            const loadContactByPublicId = async () => {
                try {
                    setIsLoading(true);
                    const res = await contactsAPI.getByPublicId(publicId);
                    setSelectedContact(res.data);
                } catch (e: any) {
                    toast.error('Contact not found');
                    navigate('/contacts');
                } finally {
                    setIsLoading(false);
                }
            };
            loadContactByPublicId();
        }
    }, [publicId, navigate]);
    
    const loadContacts = async () => {
        try {
            setIsLoading(true);
            const res = await contactsAPI.getAll();
            // Check if response status indicates an error (4xx or 5xx)
            if (res.status >= 400) {
                const errorMessage = res.data?.detail || `Request failed with status ${res.status}`;
                toast.error(errorMessage);
                setContacts([]);
                return;
            }
            // Ensure we always set an array
            const contactsData = Array.isArray(res.data) ? res.data : [];
            setContacts(contactsData);
        } catch (e: any) {
            console.error('Error loading contacts:', e);
            const errorMessage = e?.response?.data?.detail || e?.message || 'Failed to load contacts';
            toast.error(errorMessage);
            setContacts([]);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadContacts();
    }, []);

    const handleExport = async () => {
        try {
            const res = await contactsAPI.exportCSV();
            const blob = new Blob([res.data], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'contacts.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            toast.success('Contacts exported');
        } catch (e: any) {
            try {
                const res2 = await contactsAPI.exportCSV2();
                const blob = new Blob([res2.data], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'contacts.csv');
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                toast.success('Contacts exported');
            } catch (err: any) {
                const reason = err?.response?.data || err?.message || 'Failed to export contacts';
                toast.error(typeof reason === 'string' ? reason : 'Failed to export contacts');
            }
        }
    };

    const handleImportButtonClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try {
            const res = await contactsAPI.importCSV(file);
            const { created, updated, skipped } = (res.data || {}) as any;
            toast.success(`Imported ${created || 0}, updated ${updated || 0}, skipped ${skipped || 0}`);
            await loadContacts();
        } catch (err: any) {
            const detail = err?.response?.data?.detail;
            const message = typeof detail === 'string' ? detail : 'Failed to import contacts';
            toast.error(message);
        } finally {
            // Reset input so the same file can be selected again if needed
            e.target.value = '';
        }
    };

	const [searchTerm, setSearchTerm] = useState('');
	const [filterStatus, setFilterStatus] = useState<string>('all');
	const [editingContact, setEditingContact] = useState<Contact | null>(null);
	const [showAddForm, setShowAddForm] = useState(false);
	const [showFilters, setShowFilters] = useState(false);
	const [companyFilter, setCompanyFilter] = useState('');
	const [positionFilter, setPositionFilter] = useState('');
	const [emailDomainFilter, setEmailDomainFilter] = useState('');
	const [dateFrom, setDateFrom] = useState<string>('');
	const [dateTo, setDateTo] = useState<string>('');

	const filteredContacts = Array.isArray(contacts) ? contacts.filter(contact => {
		const effectiveStatus = (contact.computed_status || contact.status || '').toLowerCase();
		const name = (contact.name || '').toLowerCase();
		const email = (contact.email || '').toLowerCase();
		const company = (contact.company || '').toLowerCase();
		const matchesSearch = name.includes(searchTerm.toLowerCase()) ||
						email.includes(searchTerm.toLowerCase()) ||
						company.includes(searchTerm.toLowerCase());
		const matchesFilter = filterStatus === 'all' || effectiveStatus === filterStatus;
		const matchesCompany = !companyFilter || company.includes(companyFilter.toLowerCase());
		const matchesPosition = !positionFilter || (contact.position || '').toLowerCase().includes(positionFilter.toLowerCase());
		const matchesDomain = !emailDomainFilter || email.endsWith(emailDomainFilter.toLowerCase());
		let matchesDate = true;
		if (dateFrom) {
			const from = new Date(dateFrom);
			matchesDate = matchesDate && new Date(contact.last_contact) >= from;
		}
		if (dateTo) {
			const to = new Date(dateTo);
			to.setDate(to.getDate() + 1);
			matchesDate = matchesDate && new Date(contact.last_contact) < to;
		}
		return matchesSearch && matchesFilter && matchesCompany && matchesPosition && matchesDomain && matchesDate;
	}) : [];

	// Build a 6-word excerpt of notes with a Read More action that opens the edit popup
	const noteExcerpt = (c: Contact) => {
		const full = (c.notes || '').trim();
		if (!full) return null;
		const words = full.split(/\s+/);
		const needsTruncate = words.length > 6;
		const head = words.slice(0, 6).join(' ');
		return (
			<span>
				{needsTruncate ? `${head}... ` : head}
				{needsTruncate && (
					<button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setEditingContact(c); }} className="text-blue-600 hover:underline">Read More</button>
				)}
			</span>
		);
	};

    type NewContactPayload = {
        name: string;
        email: string;
        company?: string;
        phone?: string;
        position?: string;
        notes?: string;
    };

    const handleAddContact = async (contact: NewContactPayload) => {
        try {
            const res = await contactsAPI.create(contact);
            const currentContacts = Array.isArray(contacts) ? contacts : [];
            setContacts([res.data, ...currentContacts]);
            setShowAddForm(false);
            toast.success('Contact added');
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Failed to add contact');
        }
    };

	const handleEditContact = (contact: Contact) => {
		setEditingContact(contact);
	};

    const handleUpdateContact = async (updatedContact: Contact) => {
        try {
            const { id, last_contact, ...rest } = updatedContact as any;
            const res = await contactsAPI.update(id, rest);
            const currentContacts = Array.isArray(contacts) ? contacts : [];
            setContacts(currentContacts.map(c => c.id === id ? res.data : c));
            setEditingContact(null);
            toast.success('Contact updated');
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Failed to update contact');
        }
    };

    const handleDeleteContact = async (id: number) => {
        if (!window.confirm('Are you sure you want to delete this contact?')) return;
        try {
            await contactsAPI.delete(id);
            const currentContacts = Array.isArray(contacts) ? contacts : [];
            setContacts(currentContacts.filter(c => c.id !== id));
            toast.success('Contact deleted');
        } catch (e) {
            toast.error('Failed to delete contact');
        }
    };

	// If viewing a specific contact by public_id, show detail view
	if (publicId && selectedContact) {
		return (
			<div className="container mx-auto px-4 py-8 pt-20 min-h-screen">
				<div className="rounded-lg border border-gray-200 shadow-sm p-6 max-w-4xl mx-auto">
					<div className="flex justify-between items-start mb-6">
						<div>
							<button
								onClick={() => navigate('/contacts')}
								className="text-blue-600 hover:text-blue-800 mb-4 flex items-center gap-2"
							>
								← Back to Contacts
							</button>
							<h1 className="text-3xl font-bold text-gray-900 mb-2">{selectedContact.name}</h1>
							<p className="text-gray-600">{selectedContact.email}</p>
						</div>
						{selectedContact.public_id && (
							<ShareLink entityType="contact" publicId={selectedContact.public_id} />
						)}
					</div>
					<div className="grid grid-cols-2 gap-6">
						<div>
							<h3 className="text-sm font-semibold text-gray-700 mb-2">Company</h3>
							<p className="text-gray-900">{selectedContact.company || 'N/A'}</p>
						</div>
						<div>
							<h3 className="text-sm font-semibold text-gray-700 mb-2">Position</h3>
							<p className="text-gray-900">{selectedContact.position || 'N/A'}</p>
						</div>
						<div>
							<h3 className="text-sm font-semibold text-gray-700 mb-2">Phone</h3>
							<p className="text-gray-900">{selectedContact.phone || 'N/A'}</p>
						</div>
						<div>
							<h3 className="text-sm font-semibold text-gray-700 mb-2">Status</h3>
							<p className="text-gray-900">{selectedContact.computed_status || selectedContact.status || 'N/A'}</p>
						</div>
						<div className="col-span-2">
							<h3 className="text-sm font-semibold text-gray-700 mb-2">Notes</h3>
							<p className="text-gray-900 whitespace-pre-wrap">{selectedContact.notes || 'No notes'}</p>
						</div>
					</div>
					<div className="mt-6 flex gap-3">
						<button
							onClick={() => handleEditContact(selectedContact)}
							className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
						>
							<Edit className="w-4 h-4" />
							Edit Contact
						</button>
						<button
							onClick={() => handleDeleteContact(selectedContact.id)}
							className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
						>
							<Trash2 className="w-4 h-4" />
							Delete Contact
						</button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="container mx-auto px-4 py-8 pt-20 min-h-screen">
			{/* Header */}
			<div className="flex justify-between items-center mb-6">
				<div>
					<h1 className="text-3xl font-bold text-gray-900 mb-2">Contacts</h1>
					<p className="text-gray-600 text-sm">Manage your business contacts and prospects</p>
				</div>
				<div className="flex space-x-3">
					<button
						onClick={() => setShowAddForm(true)}
						className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 font-medium transition-all quick-tour-add-contact"
						aria-label="Add contact"
						title="Add contact"
					>
						<Plus className="w-5 h-5" aria-hidden="true" />
						<span>Add Contact</span>
					</button>
                    <button
                        onClick={handleImportButtonClick}
                        className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg flex items-center space-x-2 font-medium transition-all"
                        aria-label="Import contacts from CSV"
                        title="Import contacts"
                    >
						<Upload className="w-5 h-5" aria-hidden="true" />
						<span>Import</span>
					</button>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv,text/csv"
                        onChange={handleFileChange}
                        className="hidden"
                    />
                    <button
                        onClick={handleExport}
                        className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg flex items-center space-x-2 font-medium transition-all"
                        aria-label="Export contacts to CSV"
                        title="Export contacts"
                    >
						<Download className="w-5 h-5" aria-hidden="true" />
						<span>Export</span>
					</button>
				</div>
			</div>

			{/* Search and Filters */}
			<div className="rounded-lg border border-gray-200 shadow-sm p-4 mb-6">
				<div className="flex flex-col md:flex-row gap-4">
					<div className="flex-1">
						<div className="relative">
							<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" aria-hidden="true" />
							<input
								type="text"
								placeholder="Search contacts..."
								value={searchTerm}
								onChange={(e) => setSearchTerm(e.target.value)}
								className="w-full pl-10 pr-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
								aria-label="Search contacts"
							/>
						</div>
					</div>
					<div className="flex gap-3">
						<select
							value={filterStatus}
							onChange={(e) => setFilterStatus(e.target.value)}
							className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
							aria-label="Filter by status"
						>
							<option value="all">All Status</option>
							<option value="new">New</option>
							<option value="sent">Sent</option>
							<option value="replied">Replied</option>
							<option value="interested">Interested</option>
							<option value="meeting_scheduled">Meeting scheduled</option>
							<option value="follow_up_1">Follow-up 1</option>
							<option value="follow_up_2">Follow-up 2</option>
							<option value="follow_up_3">Follow-up 3</option>
							<option value="prospect">Prospect</option>
							<option value="active">Active</option>
							<option value="inactive">Inactive</option>
						</select>
						<button onClick={() => setShowFilters(!showFilters)} className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg flex items-center space-x-2 font-medium transition-all" aria-label="Show more filters" title="More Filters">
							<Filter className="w-5 h-5" aria-hidden="true" />
							<span>More Filters</span>
						</button>
					</div>
				</div>

				{showFilters && (
					<div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-3">
						<input value={companyFilter} onChange={(e)=>setCompanyFilter(e.target.value)} placeholder="Company" className="px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" aria-label="Filter by company" />
						<input value={positionFilter} onChange={(e)=>setPositionFilter(e.target.value)} placeholder="Position" className="px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						<input value={emailDomainFilter} onChange={(e)=>setEmailDomainFilter(e.target.value)} placeholder="Email domain" className="px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" aria-label="Filter by email domain" />
						<div className="flex items-center space-x-2">
							<label className="text-sm text-gray-700">From</label>
							<input type="date" value={dateFrom} onChange={(e)=>setDateFrom(e.target.value)} className="px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" aria-label="Filter from date" />
						</div>
						<div className="flex items-center space-x-2">
							<label className="text-sm text-gray-700">To</label>
							<input type="date" value={dateTo} onChange={(e)=>setDateTo(e.target.value)} className="px-3 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" aria-label="Filter to date" />
						</div>
					</div>
				)}
			</div>

			{/* Loading State */}
			{isLoading && (
				<div className="rounded-lg border border-gray-200 shadow-sm p-12 text-center">
					<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
					<p className="mt-4 text-gray-600">Loading contacts...</p>
				</div>
			)}

			{/* Spreadsheet Table */}
			{!isLoading && (
			<div className="rounded-lg border border-gray-200 shadow-sm overflow-hidden">
				<div className="overflow-x-auto">
					<table className="w-full">
						<thead className="border-b border-gray-200">
							<tr>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Name</th>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Email</th>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Company</th>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Position</th>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Phone</th>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Status</th>
								<th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Actions</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-gray-200">
							{filteredContacts.map((contact) => (
								<tr 
									key={contact.id} 
									className="transition-colors cursor-pointer"
									onClick={() => contact.public_id && navigate(`/contacts/${contact.public_id}`)}
								>
									<td className="px-6 py-4 whitespace-nowrap">
										<div>
											<div className="text-sm font-medium text-gray-900">{contact.name}</div>
											<div className="text-xs text-gray-500 mt-1">{noteExcerpt(contact)}</div>
										</div>
									</td>
									<td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{contact.email}</td>
								<td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{contact.company || ''}</td>
								<td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{contact.position || ''}</td>
								<td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{contact.phone || ''}</td>
								<td className="px-6 py-4 whitespace-nowrap">
						{(() => {
							const s = (contact.computed_status || contact.status || 'prospect').toLowerCase();
							let cls = 'bg-gray-100 text-gray-700';
							let displayText = s;
							
							if (s.startsWith('follow_up')) {
								cls = 'bg-yellow-100 text-yellow-800';
							} else if (s === 'replied') {
								cls = 'bg-blue-100 text-blue-800';
							} else if (s === 'interested' || s === 'meeting_scheduled') {
								cls = 'bg-green-100 text-green-800';
							} else if (s === 'sent') {
								cls = 'bg-gray-100 text-gray-700';
							} else if (s === 'new') {
								cls = 'bg-purple-100 text-purple-800';
							} else if (s === 'active') {
								cls = 'bg-green-100 text-green-800';
							} else if (s === 'prospect') {
								cls = 'bg-gray-100 text-gray-700';
							} else if (s === 'inactive') {
								cls = 'bg-gray-100 text-gray-700';
							}
							
							if (s.startsWith('follow_up')) {
								const num = s.replace('follow_up_', '');
								displayText = `Follow-up ${num}`;
							} else if (s === 'meeting_scheduled') {
								displayText = 'Meeting Scheduled';
							}
							
							return (
								<span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${cls}`} title="Auto-computed from recent activity">
									{displayText}
								</span>
							);
						})()}
								</td>
								<td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
									<div className="flex space-x-2">
										<button
											onClick={() => handleEditContact(contact)}
											className="text-gray-600 hover:text-blue-600 transition-colors p-1.5 hover:bg-blue-50 rounded"
											aria-label={`Edit contact ${contact.name}`}
											title={`Edit ${contact.name}`}
										>
											<Edit className="w-5 h-5" aria-hidden="true" />
										</button>
										<button
											onClick={() => handleDeleteContact(contact.id)}
											className="text-gray-600 hover:text-red-600 transition-colors p-1.5 hover:bg-red-50 rounded"
											aria-label={`Delete contact ${contact.name}`}
											title={`Delete ${contact.name}`}
										>
											<Trash2 className="w-5 h-5" aria-hidden="true" />
										</button>
									</div>
								</td>
							</tr>
							))}
						</tbody>
					</table>
				</div>
				
				{filteredContacts.length === 0 && (
					<div className="text-center py-16">
						<p className="text-gray-600 font-black uppercase tracking-widest">No contacts found</p>
					</div>
				)}
			</div>
			)}

			{/* Add/Edit Contact Modal */}
			{(showAddForm || editingContact) && (
			<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
				<div className="rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
					{/* Header */}
					<div className="px-6 py-4 border-b border-gray-200">
						<h3 className="text-lg font-semibold text-gray-800">
								{editingContact ? 'Edit Contact' : 'Add New Contact'}
							</h3>
						</div>
						<ContactForm
							contact={editingContact}
							onSubmit={(payload) => {
								if (editingContact) {
									handleUpdateContact({ ...editingContact, ...payload });
								} else {
									handleAddContact(payload);
								}
							}}
							onCancel={() => {
								setShowAddForm(false);
								setEditingContact(null);
							}}
						/>
					</div>
				</div>
			)}
		</div>
	);
};

// Contact Form Component
interface ContactFormProps {
	contact?: Contact | null;
    onSubmit: (contact: { name: string; email: string; company?: string; phone?: string; position?: string; notes?: string; }) => void;
	onCancel: () => void;
}

type ContactFormData = {
	name: string;
	email: string;
	company: string;
	phone: string;
	position: string;
	notes: string;
};

const ContactForm: React.FC<ContactFormProps> = ({ contact, onSubmit, onCancel }) => {
	const [formData, setFormData] = useState<ContactFormData>({
		name: '',
		email: '',
		company: '',
		phone: '',
		position: '',
		notes: ''
	});

	// Update form data when contact prop changes
	React.useEffect(() => {
		if (contact) {
			setFormData({
				name: contact.name,
				email: contact.email,
				company: contact.company,
				phone: contact.phone,
				position: contact.position,
				notes: contact.notes
			});
		} else {
			setFormData({
				name: '',
				email: '',
				company: '',
				phone: '',
				position: '',
				notes: ''
			});
		}
	}, [contact]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		onSubmit(formData);
	};

	return (
		<form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">
					Name <span className="text-red-500">*</span>
				</label>
				<input
					type="text"
					required
					value={formData.name}
					onChange={(e) => setFormData({ ...formData, name: e.target.value })}
					className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>
			
			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">
					Email <span className="text-red-500">*</span>
				</label>
				<input
					type="email"
					required
					value={formData.email}
					onChange={(e) => setFormData({ ...formData, email: e.target.value })}
					className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>
			
			<div className="grid grid-cols-2 gap-4">
				<div>
					<label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
					<input
						type="text"
						value={formData.company}
						onChange={(e) => setFormData({ ...formData, company: e.target.value })}
						className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700 mb-1">Position</label>
					<input
						type="text"
						value={formData.position}
						onChange={(e) => setFormData({ ...formData, position: e.target.value })}
						className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
			</div>
			
			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
				<input
					type="tel"
					value={formData.phone}
					onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
					className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>
			
			<div>
                {/* Status removed: status is auto-computed and read-only */}
            </div>
			
			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
				<textarea
					value={formData.notes}
					onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
					rows={4}
					className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
				/>
			</div>
			
			<div className="flex justify-end gap-3 pt-4">
				<button
					type="button"
					onClick={onCancel}
					className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md font-medium hover:bg-gray-300 transition-colors"
				>
					Cancel
				</button>
				<button
					type="submit"
					className="px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition-colors"
				>
					{contact ? 'Update Contact' : 'Add Contact'}
				</button>
			</div>
		</form>
	);
};

export default Contacts;
