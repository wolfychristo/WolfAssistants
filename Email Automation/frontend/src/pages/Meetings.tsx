import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Calendar, Clock, MapPin, Users, Edit, Trash2, Video, Phone, ChevronLeft, ChevronRight } from 'lucide-react';
import { meetingsAPI } from '../services/api';
import { contactsAPI } from '../services/api';
import toast from 'react-hot-toast';
import ShareLink from '../components/ShareLink';

// Timezone conversion utilities
function utcToLocalDateTimeLocal(utcString: string): string {
  if (!utcString) return '';
  
  try {
    const utcDate = new Date(utcString);
    if (isNaN(utcDate.getTime())) return '';
    
    const year = utcDate.getFullYear();
    const month = String(utcDate.getMonth() + 1).padStart(2, '0');
    const day = String(utcDate.getDate()).padStart(2, '0');
    const hours = String(utcDate.getHours()).padStart(2, '0');
    const minutes = String(utcDate.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  } catch (error) {
    console.error('Error converting UTC to local datetime-local:', error);
    return '';
  }
}

function localDateTimeLocalToUtc(localString: string): string {
  if (!localString) return '';
  
  try {
    const localDate = new Date(localString);
    if (isNaN(localDate.getTime())) return '';
    return localDate.toISOString();
  } catch (error) {
    console.error('Error converting local datetime-local to UTC:', error);
    return '';
  }
}

type Meeting = {
	id: number;
	public_id?: string;
	title: string;
	description?: string | null;
	start_time: string;
	end_time?: string | null;
	location?: string | null;
	attendees?: string[];
	type?: string | null;
	status?: string | null;
	notes?: string | null;
	meeting_link?: string | null;
};

type MeetingPayload = Omit<Meeting, 'id'>;

type MeetingFormData = {
	title: string;
	description: string;
	start_time: string;
	end_time: string;
	location: string;
	attendees: string[];
	type: string;
	status: Meeting['status'];
	notes: string;
	meeting_link?: string;
};

const Meetings: React.FC = () => {
    const { publicId } = useParams<{ publicId?: string }>();
    const navigate = useNavigate();
    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
    
    // Load specific meeting by public_id if in URL
    useEffect(() => {
        if (publicId) {
            const loadMeetingByPublicId = async () => {
                try {
                    const res = await meetingsAPI.getByPublicId(publicId);
                    setSelectedMeeting(res.data);
                } catch (e: any) {
                    toast.error('Meeting not found');
                    navigate('/meetings');
                }
            };
            loadMeetingByPublicId();
        }
    }, [publicId, navigate]);

    const loadMeetings = async () => {
        try {
            const res = await meetingsAPI.getAll();
            const data = res.data.map((m: any) => ({
                ...m,
                attendees: Array.isArray(m.attendees) ? m.attendees : (m.attendees ? String(m.attendees).split(',').map((x: string) => x.trim()).filter(Boolean) : []),
            }));
            setMeetings(data);
        } catch {
            toast.error('Failed to load meetings');
        }
    };

    useEffect(() => { loadMeetings(); }, []);

    // Contacts for attendees dropdown
    const [contacts, setContacts] = useState<any[]>([]);
    useEffect(() => {
        (async () => {
            try {
                const res = await contactsAPI.getAll();
                setContacts(res.data || []);
            } catch {}
        })();
    }, []);

	const [selectedDate, setSelectedDate] = useState(new Date());
	const [showAddForm, setShowAddForm] = useState(false);
	const [editingMeeting, setEditingMeeting] = useState<Meeting | null>(null);
	const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');

    const handleAddMeeting = async (meeting: MeetingPayload) => {
        try {
            const res = await meetingsAPI.create(meeting);
            const saved = { ...res.data, attendees: Array.isArray(res.data.attendees) ? res.data.attendees : (res.data.attendees ? String(res.data.attendees).split(',').map((x: string) => x.trim()).filter(Boolean) : []) };
            setMeetings([saved, ...meetings]);
            setShowAddForm(false);
            toast.success('Meeting scheduled');
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Failed to schedule meeting');
        }
    };

	const handleEditMeeting = (meeting: Meeting) => {
		setEditingMeeting(meeting);
	};

    const handleUpdateMeeting = async (prev: Meeting, payload: Omit<Meeting, 'id'> | any) => {
        try {
            const res = await meetingsAPI.update(prev.id, payload);
            const updated = { ...res.data, attendees: Array.isArray(res.data.attendees) ? res.data.attendees : (res.data.attendees ? String(res.data.attendees).split(',').map((x: string) => x.trim()).filter(Boolean) : []) };
            setMeetings(meetings.map(m => m.id === prev.id ? updated : m));
            setEditingMeeting(null);
            toast.success('Meeting updated');
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Failed to update meeting');
        }
    };

    const handleDeleteMeeting = async (id: number) => {
        if (!window.confirm('Are you sure you want to delete this meeting?')) return;
        try {
            await meetingsAPI.delete(id);
            setMeetings(meetings.filter(m => m.id !== id));
            toast.success('Meeting deleted');
        } catch (e: any) {
            toast.error(e?.response?.data?.detail || 'Failed to delete meeting');
        }
    };

	// Calendar navigation
	const goToPreviousMonth = () => {
		setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() - 1, 1));
	};

	const goToNextMonth = () => {
		setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() + 1, 1));
	};

	// Get calendar days
	const getCalendarDays = () => {
		const year = selectedDate.getFullYear();
		const month = selectedDate.getMonth();
		const firstDay = new Date(year, month, 1);
		const lastDay = new Date(year, month + 1, 0);
		const daysInMonth = lastDay.getDate();
		const startingDayOfWeek = firstDay.getDay();

		const days: (Date | null)[] = [];
		
		// Add empty cells for days before the first day of the month
		for (let i = 0; i < startingDayOfWeek; i++) {
			days.push(null);
		}
		
		// Add all days of the month
		for (let day = 1; day <= daysInMonth; day++) {
			days.push(new Date(year, month, day));
		}
		
		return days;
	};

	// Get meetings for a specific date
	const getMeetingsForDate = (date: Date | null): Meeting[] => {
		if (!date) return [];
		const dateStr = date.toISOString().split('T')[0];
		return meetings.filter(m => {
			const meetingDate = new Date(m.start_time).toISOString().split('T')[0];
			return meetingDate === dateStr;
		});
	};

	// Check if date is today
	const isToday = (date: Date | null): boolean => {
		if (!date) return false;
		const today = new Date();
		return date.toDateString() === today.toDateString();
	};

	const getMeetingIcon = (type: string | null | undefined) => {
		switch (type?.toLowerCase()) {
			case 'video': return <Video className="w-4 h-4" />;
			case 'phone': return <Phone className="w-4 h-4" />;
			default: return <MapPin className="w-4 h-4" />;
		}
	};

	// If viewing a specific meeting by public_id, show detail view
	if (publicId && selectedMeeting) {
		return (
			<div className="container mx-auto px-4 py-8 pt-20 min-h-screen">
				<div className="rounded-lg border border-gray-200 shadow-sm p-6 max-w-4xl mx-auto">
					<div className="flex justify-between items-start mb-6">
						<div>
							<button
								onClick={() => navigate('/meetings')}
								className="text-blue-600 hover:text-blue-800 mb-4 flex items-center gap-2"
							>
								← Back to Meetings
							</button>
							<h1 className="text-3xl font-bold text-gray-900 mb-2">{selectedMeeting.title}</h1>
							{selectedMeeting.description && (
								<p className="text-gray-600">{selectedMeeting.description}</p>
							)}
						</div>
						{selectedMeeting.public_id && (
							<ShareLink entityType="meeting" publicId={selectedMeeting.public_id} />
						)}
					</div>
					<div className="grid grid-cols-2 gap-6">
						<div>
							<h3 className="text-sm font-semibold text-gray-700 mb-2">Start Time</h3>
							<p className="text-gray-900">
								{new Date(selectedMeeting.start_time).toLocaleString('en-US', {
									month: 'short',
									day: 'numeric',
									year: 'numeric',
									hour: 'numeric',
									minute: '2-digit',
									timeZoneName: 'short'
								})}
							</p>
						</div>
						{selectedMeeting.end_time && (
							<div>
								<h3 className="text-sm font-semibold text-gray-700 mb-2">End Time</h3>
								<p className="text-gray-900">
									{new Date(selectedMeeting.end_time).toLocaleString('en-US', {
										month: 'short',
										day: 'numeric',
										year: 'numeric',
										hour: 'numeric',
										minute: '2-digit',
										timeZoneName: 'short'
									})}
								</p>
							</div>
						)}
						{selectedMeeting.location && (
							<div>
								<h3 className="text-sm font-semibold text-gray-700 mb-2">Location</h3>
								<p className="text-gray-900">{selectedMeeting.location}</p>
							</div>
						)}
						{selectedMeeting.type && (
							<div>
								<h3 className="text-sm font-semibold text-gray-700 mb-2">Type</h3>
								<p className="text-gray-900">{selectedMeeting.type}</p>
							</div>
						)}
						{selectedMeeting.status && (
							<div>
								<h3 className="text-sm font-semibold text-gray-700 mb-2">Status</h3>
								<p className="text-gray-900">{selectedMeeting.status}</p>
							</div>
						)}
						{selectedMeeting.attendees && selectedMeeting.attendees.length > 0 && (
							<div className="col-span-2">
								<h3 className="text-sm font-semibold text-gray-700 mb-2">Attendees</h3>
								<p className="text-gray-900">{Array.isArray(selectedMeeting.attendees) ? selectedMeeting.attendees.join(', ') : selectedMeeting.attendees}</p>
							</div>
						)}
						{selectedMeeting.notes && (
							<div className="col-span-2">
								<h3 className="text-sm font-semibold text-gray-700 mb-2">Notes</h3>
								<p className="text-gray-900 whitespace-pre-wrap">{selectedMeeting.notes}</p>
							</div>
						)}
					</div>
					<div className="mt-6 flex gap-3">
						<button
							onClick={() => handleEditMeeting(selectedMeeting)}
							className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
						>
							<Edit className="w-4 h-4" />
							Edit Meeting
						</button>
						<button
							onClick={() => handleDeleteMeeting(selectedMeeting.id)}
							className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
						>
							<Trash2 className="w-4 h-4" />
							Delete Meeting
						</button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="container mx-auto px-4 py-8 pt-20 min-h-screen">
			{/* Header */}
			<div className="flex justify-between items-center mb-8">
				<div>
					<h1 className="text-3xl font-bold text-gray-900 mb-2">Calendar & Meetings</h1>
					<p className="text-gray-600 mt-2 font-medium">Schedule and manage your business meetings</p>
				</div>
				<div className="flex space-x-4">
					<button
						onClick={() => setShowAddForm(true)}
						className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg flex items-center space-x-2 font-semibold transition-all"
						aria-label="Schedule meeting"
						title="Schedule meeting"
					>
						<Plus className="w-5 h-5" aria-hidden="true" />
						<span>Schedule Meeting</span>
					</button>
					<div className="flex border border-gray-300 rounded-lg overflow-hidden">
						<button
							onClick={() => setViewMode('calendar')}
							className={`px-6 py-3 font-semibold transition-all ${
								viewMode === 'calendar' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
							}`}
							aria-label="Switch to calendar view"
							title="Calendar view"
						>
							<Calendar className="w-5 h-5 inline mr-2" aria-hidden="true" />
							Calendar
						</button>
						<button
							onClick={() => setViewMode('list')}
							className={`px-6 py-3 font-semibold transition-all ${
								viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
							}`}
							aria-label="Switch to list view"
							title="List view"
						>
							<Clock className="w-5 h-5 inline mr-2" aria-hidden="true" />
							List
						</button>
					</div>
				</div>
			</div>

			{/* Month Navigation */}
			<div className="flex justify-between items-center mb-6">
				<button
					onClick={goToPreviousMonth}
					className="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100 transition-all"
				>
					<ChevronLeft className="w-5 h-5 inline mr-2" />
					Previous
				</button>
				<h2 className="text-3xl font-bold text-brand-black">
					{selectedDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
				</h2>
				<button
					onClick={goToNextMonth}
					className="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100 transition-all"
				>
					Next
					<ChevronRight className="w-5 h-5 inline ml-2" />
				</button>
			</div>

			{/* Calendar View */}
			{viewMode === 'calendar' && (
				<div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8">
					<div className="grid grid-cols-7 gap-2 mb-4">
						{['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
							<div key={day} className="text-center font-semibold text-gray-700 text-sm py-2">
								{day}
							</div>
						))}
					</div>
					<div className="grid grid-cols-7 gap-2">
						{getCalendarDays().map((date, index) => {
							const dayMeetings = getMeetingsForDate(date);
							const isCurrentDay = isToday(date);
							const isOtherMonth = date && (
								date.getMonth() !== selectedDate.getMonth() || 
								date.getFullYear() !== selectedDate.getFullYear()
							);
							
							return (
								<div
									key={index}
									className={`min-h-[100px] p-2 border ${
										date 
											? isCurrentDay 
												? 'bg-blue-50 border-blue-300' 
												: isOtherMonth
												? 'bg-gray-50 border-gray-200'
												: 'bg-white border-gray-200'
											: 'bg-gray-50 border-gray-200'
									} rounded-lg`}
								>
									{date && (
										<>
											<div className={`text-sm font-semibold mb-2 ${isCurrentDay ? 'text-blue-600' : isOtherMonth ? 'text-gray-400' : 'text-gray-700'}`}>
												{date.getDate()}
											</div>
											<div className="space-y-1">
												{dayMeetings.slice(0, 2).map(meeting => (
													<div
														key={meeting.id}
														className="bg-blue-100 text-blue-900 p-1.5 rounded text-xs font-medium truncate cursor-pointer hover:bg-blue-200 transition-colors flex items-center justify-between group"
														onClick={() => {
															if (meeting.public_id) {
																navigate(`/meetings/${meeting.public_id}`);
															} else {
																handleEditMeeting(meeting);
															}
														}}
														title={meeting.title}
													>
														<div className="flex items-center gap-1 flex-1 min-w-0">
															{getMeetingIcon(meeting.type)}
															<span className="truncate">{meeting.title}</span>
														</div>
														<button
															onClick={(e) => {
																e.stopPropagation();
																handleDeleteMeeting(meeting.id);
															}}
															className="opacity-0 group-hover:opacity-100 ml-1 text-blue-700 hover:text-red-600 transition-opacity"
															aria-label="Delete meeting"
														>
															<Trash2 className="w-3 h-3" />
														</button>
													</div>
												))}
												{dayMeetings.length > 2 && (
													<div className="text-xs font-medium text-gray-500">
														+{dayMeetings.length - 2} more
													</div>
												)}
											</div>
										</>
									)}
								</div>
							);
						})}
					</div>
				</div>
			)}

			{/* List View */}
			{viewMode === 'list' && (
				<div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8">
					<div className="space-y-4">
						{meetings.length === 0 ? (
							<div className="text-center py-12">
								<p className="text-gray-600 font-medium">No meetings scheduled</p>
							</div>
						) : (
							meetings.map(meeting => (
								<div
									key={meeting.id}
									className="p-6 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
									onClick={() => {
										if (meeting.public_id) {
											navigate(`/meetings/${meeting.public_id}`);
										} else {
											handleEditMeeting(meeting);
										}
									}}
								>
									<div className="flex items-start justify-between">
										<div className="flex-1">
											<div className="flex items-center gap-3 mb-2">
												{getMeetingIcon(meeting.type)}
												<h3 className="text-xl font-semibold text-gray-900">{meeting.title}</h3>
											</div>
											{meeting.description && (
												<p className="text-sm text-gray-600 mb-2">{meeting.description}</p>
											)}
											<div className="flex flex-wrap gap-4 text-sm text-gray-600">
												{meeting.start_time && (
													<div className="flex items-center gap-2">
														<Clock className="w-4 h-4 text-blue-600" />
														<span>
															{new Date(meeting.start_time).toLocaleString('en-US', {
																month: 'short',
																day: 'numeric',
																year: 'numeric',
																hour: 'numeric',
																minute: '2-digit',
																hour12: true
															})}
														</span>
													</div>
												)}
												{meeting.location && (
													<div className="flex items-center gap-2">
														<MapPin className="w-4 h-4 text-blue-600" />
														<span>{meeting.location}</span>
													</div>
												)}
												{meeting.attendees && meeting.attendees.length > 0 && (
													<div className="flex items-center gap-2">
														<Users className="w-4 h-4 text-blue-600" />
														<span>{meeting.attendees.length} attendee(s)</span>
													</div>
												)}
											</div>
										</div>
										<div className="flex space-x-3 ml-4">
											<button 
												onClick={() => handleEditMeeting(meeting)} 
												className="p-3 text-gray-600 hover:text-blue-600 hover:bg-blue-50 transition-colors rounded-lg border border-gray-200 hover:border-blue-300" 
												aria-label="Edit meeting" 
												title="Edit meeting"
											>
												<Edit className="w-5 h-5" aria-hidden="true" />
											</button>
											<button 
												onClick={() => handleDeleteMeeting(meeting.id)} 
												className="p-3 text-gray-600 hover:text-red-600 hover:bg-red-50 transition-colors rounded-lg border border-gray-200 hover:border-red-300" 
												aria-label="Delete meeting" 
												title="Delete meeting"
											>
												<Trash2 className="w-5 h-5" aria-hidden="true" />
											</button>
										</div>
									</div>
								</div>
							))
						)}
					</div>
				</div>
			)}

			{/* Add/Edit Meeting Modal */}
			{(showAddForm || editingMeeting) && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
					<div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
						<div className="px-8 py-6 border-b border-gray-200">
							<h3 className="text-2xl font-semibold text-gray-900">
								{editingMeeting ? 'Edit Meeting' : 'Schedule New Meeting'}
							</h3>
						</div>
						<MeetingForm
							meeting={editingMeeting}
							contacts={contacts}
							onSubmit={(payload) => {
								if (editingMeeting) {
									handleUpdateMeeting(editingMeeting, payload);
								} else {
									handleAddMeeting(payload);
								}
							}}
							onCancel={() => {
								setShowAddForm(false);
								setEditingMeeting(null);
							}}
						/>
					</div>
				</div>
			)}
		</div>
	);
};

// Meeting Form Component
interface MeetingFormProps {
	meeting?: Meeting | null;
	contacts: any[];
	onSubmit: (payload: MeetingPayload) => void;
	onCancel: () => void;
}

const MeetingForm: React.FC<MeetingFormProps> = ({ meeting, contacts, onSubmit, onCancel }) => {
	const [formData, setFormData] = useState<MeetingFormData>({
		title: '',
		description: '',
		start_time: '',
		end_time: '',
		location: '',
		attendees: [],
		type: 'in-person',
		status: 'scheduled',
		notes: '',
		meeting_link: '',
	});

	useEffect(() => {
		if (meeting) {
			setFormData({
				title: meeting.title || '',
				description: meeting.description || '',
				start_time: utcToLocalDateTimeLocal(meeting.start_time),
				end_time: meeting.end_time ? utcToLocalDateTimeLocal(meeting.end_time) : '',
				location: meeting.location || '',
				attendees: meeting.attendees || [],
				type: meeting.type || 'in-person',
				status: meeting.status || 'scheduled',
				notes: meeting.notes || '',
				meeting_link: meeting.meeting_link || '',
			});
		}
	}, [meeting]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		const payload: MeetingPayload = {
			title: formData.title,
			description: formData.description || null,
			start_time: localDateTimeLocalToUtc(formData.start_time),
			end_time: formData.end_time ? localDateTimeLocalToUtc(formData.end_time) : null,
			location: formData.location || null,
			attendees: formData.attendees,
			type: formData.type || null,
			status: formData.status || 'scheduled',
			notes: formData.notes || null,
			meeting_link: formData.meeting_link || null,
		};
		onSubmit(payload);
	};

	return (
		<form onSubmit={handleSubmit} className="px-8 py-6 space-y-6">
			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">
					Title <span className="text-red-500">*</span>
				</label>
				<input
					type="text"
					required
					value={formData.title}
					onChange={(e) => setFormData({ ...formData, title: e.target.value })}
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">Description</label>
				<textarea
					value={formData.description}
					onChange={(e) => setFormData({ ...formData, description: e.target.value })}
					rows={3}
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
				/>
			</div>

			<div className="grid grid-cols-2 gap-4">
				<div>
					<label className="block text-sm font-semibold text-gray-700 mb-2">
						Start Time <span className="text-red-500">*</span>
					</label>
					<input
						type="datetime-local"
						required
						value={formData.start_time}
						onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
						className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
				<div>
					<label className="block text-sm font-semibold text-gray-700 mb-2">
						End Time <span className="text-red-500">*</span>
					</label>
					<input
						type="datetime-local"
						required
						value={formData.end_time}
						onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
						className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
			</div>

			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">Location</label>
				<input
					type="text"
					value={formData.location}
					onChange={(e) => setFormData({ ...formData, location: e.target.value })}
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">Type</label>
				<select
					value={formData.type}
					onChange={(e) => setFormData({ ...formData, type: e.target.value })}
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				>
					<option value="in-person">In Person</option>
					<option value="video">Video</option>
					<option value="phone">Phone</option>
				</select>
			</div>

			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">Attendees</label>
				<select
					multiple
					value={formData.attendees}
					onChange={(e) => {
						const selected = Array.from(e.target.selectedOptions, option => option.value);
						setFormData({ ...formData, attendees: selected });
					}}
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[120px]"
				>
					{contacts.map(contact => (
						<option key={contact.id} value={contact.email}>
							{contact.name} ({contact.email})
						</option>
					))}
				</select>
				<p className="text-xs text-gray-500 mt-2">Hold Ctrl/Cmd to select multiple</p>
			</div>

			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">Meeting Link</label>
				<input
					type="url"
					value={formData.meeting_link}
					onChange={(e) => setFormData({ ...formData, meeting_link: e.target.value })}
					placeholder="https://meet.google.com/..."
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<div>
				<label className="block text-sm font-semibold text-gray-700 mb-2">Notes</label>
				<textarea
					value={formData.notes}
					onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
					rows={3}
					className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
				/>
			</div>

			<div className="flex gap-4 pt-4">
				<button
					type="button"
					onClick={onCancel}
					className="flex-1 px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-all"
				>
					Cancel
				</button>
				<button
					type="submit"
					className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all"
				>
					{meeting ? 'Update' : 'Schedule'} Meeting
				</button>
			</div>
		</form>
	);
};

export default Meetings;