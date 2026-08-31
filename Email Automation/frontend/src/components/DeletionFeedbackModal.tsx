import React, { useState } from 'react';
import { X, Star, AlertCircle, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

interface DeletionFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (feedback: DeletionFeedback) => void;
}

interface DeletionFeedback {
  category: string;
  custom_category?: string;
  rating: number;
  details: string;
  improvements?: string;
  competitor?: string;
  contact_consent: boolean;
  contact_method?: string;
}

const DeletionFeedbackModal: React.FC<DeletionFeedbackModalProps> = ({
  isOpen,
  onClose,
  onSubmit
}) => {
  const [feedback, setFeedback] = useState<DeletionFeedback>({
    category: '',
    custom_category: '',
    rating: 0,
    details: '',
    improvements: '',
    competitor: '',
    contact_consent: false,
    contact_method: ''
  });

  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const categories = [
    { value: 'pricing', label: 'Pricing', description: 'Too expensive or not worth the cost' },
    { value: 'features', label: 'Missing Features', description: 'Lacks functionality I need' },
    { value: 'support', label: 'Poor Support', description: 'Customer service issues' },
    { value: 'usability', label: 'Hard to Use', description: 'Interface or workflow problems' },
    { value: 'performance', label: 'Performance Issues', description: 'Slow or unreliable' },
    { value: 'other', label: 'Other', description: 'Different reason' }
  ];

  const handleSubmit = async () => {
    if (!feedback.category || !feedback.details.trim()) {
      toast.error('Please select a category and provide details');
      return;
    }

    if (feedback.category === 'other' && !feedback.custom_category?.trim()) {
      toast.error('Please specify the reason for leaving');
      return;
    }

    if (feedback.rating === 0) {
      toast.error('Please provide a rating');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(feedback);
      toast.success('Thank you for your feedback!');
      onClose();
    } catch (error) {
      toast.error('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRatingClick = (rating: number) => {
    setFeedback(prev => ({ ...prev, rating }));
  };

  const renderStars = () => {
    return (
      <div className="flex space-x-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => handleRatingClick(star)}
            className={`p-1 rounded ${
              star <= feedback.rating
                ? 'text-yellow-400 hover:text-yellow-500'
                : 'text-gray-300 hover:text-gray-400'
            }`}
          >
            <Star className="w-6 h-6 fill-current" />
          </button>
        ))}
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-bold text-gray-900">
            Help Us Improve
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="mb-6">
          <div className="flex items-center mb-4">
            <AlertCircle className="w-5 h-5 text-brand-red mr-2" />
            <p className="text-gray-700">
              We're sorry to see you go! Before you delete your account, please help us understand why you're leaving.
            </p>
          </div>
        </div>

        {/* Step 1: Category Selection */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              What's the main reason for leaving?
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {categories.map((category) => (
                <button
                  key={category.value}
                  onClick={() => setFeedback(prev => ({ ...prev, category: category.value }))}
                  className={`p-4 text-left border rounded-lg transition-colors ${
                    feedback.category === category.value
                      ? 'border-brand-red bg-red-50 text-brand-red'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="font-medium">{category.label}</div>
                  <div className="text-sm text-gray-600">{category.description}</div>
                </button>
              ))}
            </div>
            
            {/* Custom Category Input */}
            {feedback.category === 'other' && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Please specify the reason for leaving
                </label>
                <input
                  type="text"
                  value={feedback.custom_category || ''}
                  onChange={(e) => setFeedback(prev => ({ ...prev, custom_category: e.target.value }))}
                  placeholder="e.g., Found a better solution, changing business direction, etc."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-red"
                />
              </div>
            )}
          </div>
        )}

        {/* Step 2: Rating */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              How would you rate your overall experience?
            </h4>
            <div className="text-center">
              {renderStars()}
              <p className="text-sm text-gray-600 mt-2">
                {feedback.rating === 0 && 'Click a star to rate'}
                {feedback.rating === 1 && 'Very Poor'}
                {feedback.rating === 2 && 'Poor'}
                {feedback.rating === 3 && 'Average'}
                {feedback.rating === 4 && 'Good'}
                {feedback.rating === 5 && 'Excellent'}
              </p>
            </div>
          </div>
        )}

        {/* Step 3: Details */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              Please tell us more about your experience
            </h4>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What specific issues did you encounter? *
                </label>
                <textarea
                  value={feedback.details}
                  onChange={(e) => setFeedback(prev => ({ ...prev, details: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-red"
                  rows={4}
                  placeholder="Please describe the specific problems or issues you experienced..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What could we improve? (Optional)
                </label>
                <textarea
                  value={feedback.improvements}
                  onChange={(e) => setFeedback(prev => ({ ...prev, improvements: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-red"
                  rows={3}
                  placeholder="What changes would make you reconsider staying?"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Are you switching to a competitor? (Optional)
                </label>
                <input
                  type="text"
                  value={feedback.competitor}
                  onChange={(e) => setFeedback(prev => ({ ...prev, competitor: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-red"
                  placeholder="Which service are you switching to?"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Contact Consent */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              Stay in touch?
            </h4>
            <div className="space-y-4">
              <div className="flex items-start">
                <input
                  type="checkbox"
                  id="contact-consent"
                  checked={feedback.contact_consent}
                  onChange={(e) => setFeedback(prev => ({ ...prev, contact_consent: e.target.checked }))}
                  className="mt-1 h-4 w-4 text-brand-red focus:ring-brand-red border-gray-300 rounded"
                />
                <label htmlFor="contact-consent" className="ml-3 text-sm text-gray-700">
                  I'd like to be contacted if you make improvements based on my feedback
                </label>
              </div>

              {feedback.contact_consent && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Preferred contact method
                  </label>
                  <select
                    value={feedback.contact_method}
                    onChange={(e) => setFeedback(prev => ({ ...prev, contact_method: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-red"
                  >
                    <option value="">Select method</option>
                    <option value="email">Email</option>
                    <option value="phone">Phone</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-8">
          <button
            onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
            disabled={currentStep === 1}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          <div className="flex space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              Cancel
            </button>
            
            {currentStep < 4 ? (
              <button
                onClick={() => setCurrentStep(currentStep + 1)}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-red rounded-md hover:bg-primary-600"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-red rounded-md hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Submitting...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Submit & Delete Account
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Progress Indicator */}
        <div className="mt-6">
          <div className="flex items-center justify-center space-x-2">
            {[1, 2, 3, 4].map((step) => (
              <div
                key={step}
                className={`w-3 h-3 rounded-full ${
                  step <= currentStep ? 'bg-brand-red' : 'bg-gray-300'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            Step {currentStep} of 4
          </p>
        </div>
      </div>
    </div>
  );
};

export default DeletionFeedbackModal;
