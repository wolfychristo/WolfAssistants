import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Trash2, ArrowLeft } from 'lucide-react';
import { toast } from 'react-hot-toast';
import DeletionFeedbackModal from '../components/DeletionFeedbackModal';

interface DeletionFeedback {
  category: string;
  rating: number;
  details: string;
  improvements?: string;
  competitor?: string;
  contact_consent: boolean;
  contact_method?: string;
}

const DeleteAccount: React.FC = () => {
  const navigate = useNavigate();
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteClick = () => {
    setShowFeedbackModal(true);
  };

  const handleFeedbackSubmit = async (feedback: DeletionFeedback) => {
    try {
      // Submit feedback first
      const feedbackResponse = await fetch('/api/v1/user-feedback/deletion-feedback', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedback),
      });

      if (!feedbackResponse.ok) {
        throw new Error('Failed to submit feedback');
      }

      // Then delete the account
      setIsDeleting(true);
      const deleteResponse = await fetch('/api/v1/user-feedback/account', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!deleteResponse.ok) {
        throw new Error('Failed to delete account');
      }

      // Clear local storage and redirect
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      toast.success('Account deleted successfully. Thank you for your feedback!');
      navigate('/');
    } catch (error) {
      console.error('Error deleting account:', error);
      toast.error('Failed to delete account. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="min-h-screen pt-16">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="text-center mb-8">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Delete Account</h1>
            <p className="text-gray-600">
              This action cannot be undone. All your data will be permanently removed.
            </p>
          </div>

          <div className="space-y-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-red-800 mb-2">What happens when you delete your account:</h3>
              <ul className="text-sm text-red-700 space-y-1">
                <li>• All your emails, contacts, and meetings will be permanently deleted</li>
                <li>• Your account and all associated data will be removed from our servers</li>
                <li>• You will lose access to all features and services</li>
                <li>• This action cannot be reversed</li>
              </ul>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-blue-800 mb-2">Before you go:</h3>
              <p className="text-sm text-blue-700">
                We'd love to understand why you're leaving so we can improve our service. 
                When you click "Delete Account", we'll ask you a few quick questions about your experience.
              </p>
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="flex-1 flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Go Back
              </button>
              <button
                onClick={handleDeleteClick}
                disabled={isDeleting}
                className="flex-1 flex items-center justify-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {isDeleting ? 'Deleting...' : 'Delete Account'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <DeletionFeedbackModal
        isOpen={showFeedbackModal}
        onClose={() => setShowFeedbackModal(false)}
        onSubmit={handleFeedbackSubmit}
      />
    </div>
  );
};

export default DeleteAccount;
