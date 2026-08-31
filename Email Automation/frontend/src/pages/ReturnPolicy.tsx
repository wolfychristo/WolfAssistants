import React from 'react';
import { Link } from 'react-router-dom';

const ReturnPolicy: React.FC = () => {
  return (
    <div className="min-h-screen py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow-lg rounded-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-brand-red mb-4">Return & Refund Policy</h1>
            <p className="text-gray-600">Last updated: {new Date().toLocaleDateString()}</p>
          </div>

          <div className="prose prose-lg max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">1. Overview</h2>
              <p className="text-gray-700 leading-relaxed">
                At Wolf Assistants, we strive to provide excellent service and customer satisfaction. This Return & Refund Policy outlines the terms and conditions for returns, refunds, and cancellations of our email AI-assisted services.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">2. Service Cancellation</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                You may cancel your subscription at any time through your account dashboard or by contacting our support team. Cancellation will take effect at the end of your current billing period.
              </p>
              
              <h3 className="text-xl font-semibold text-gray-800 mb-3">Cancellation Process</h3>
              <ul className="list-disc list-inside text-gray-700 space-y-2">
                <li>Log into your account dashboard</li>
                <li>Navigate to the billing section</li>
                <li>Click "Cancel Subscription"</li>
                <li>Confirm your cancellation</li>
                <li>You will receive a confirmation email</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">3. Refund Policy</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                We offer refunds under the following circumstances:
              </p>
              
              <h3 className="text-xl font-semibold text-gray-800 mb-3">Eligible for Refund</h3>
              <ul className="list-disc list-inside text-gray-700 space-y-2">
                <li><strong>Service Downtime:</strong> If our service is unavailable for more than 24 consecutive hours</li>
                <li><strong>Billing Errors:</strong> If you were charged incorrectly due to our error</li>
                <li><strong>Duplicate Charges:</strong> If you were charged multiple times for the same service</li>
                <li><strong>Service Failure:</strong> If we fail to deliver the core functionality as aims to helpd</li>
                <li><strong>First 30 Days:</strong> New customers may request a full refund within 30 days of initial subscription</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-800 mb-3 mt-6">Not Eligible for Refund</h3>
              <ul className="list-disc list-inside text-gray-700 space-y-2">
                <li>Change of mind after using the service</li>
                <li>Failure to use the service due to user error</li>
                <li>Violation of our Terms of Service</li>
                <li>Custom development or integration work</li>
                <li>Third-party service fees or charges</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">4. Refund Process</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                To request a refund, please follow these steps:
              </p>
              
              <div className="bg-gray-50 p-6 rounded-lg">
                <ol className="list-decimal list-inside text-gray-700 space-y-3">
                  <li>Contact our support team at info@yourcompany.com</li>
                  <li>Provide your account email and reason for refund</li>
                  <li>Include any relevant documentation or screenshots</li>
                  <li>Our team will review your request within 2-3 business days</li>
                  <li>If approved, refunds will be processed within 5-10 business days</li>
                </ol>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">5. Refund Methods</h2>
              <p className="text-gray-700 leading-relaxed">
                Refunds will be issued using the same payment method used for the original purchase. Processing times may vary depending on your payment provider:
              </p>
              <ul className="list-disc list-inside text-gray-700 mt-4 space-y-2">
                <li><strong>Credit/Debit Cards:</strong> 5-10 business days</li>
                <li><strong>PayPal:</strong> 3-5 business days</li>
                <li><strong>Bank Transfer:</strong> 7-14 business days</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">6. Data Retention After Cancellation</h2>
              <p className="text-gray-700 leading-relaxed">
                After cancellation, we will retain your data for 30 days to allow for account reactivation. After this period, all personal data will be permanently deleted in accordance with our Privacy Policy, unless you request earlier deletion.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">7. Service Credits</h2>
              <p className="text-gray-700 leading-relaxed">
                In some cases, we may offer service credits instead of refunds. Service credits can be used to extend your subscription or upgrade your plan. Credits are non-transferable and expire after 12 months.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">8. Dispute Resolution</h2>
              <p className="text-gray-700 leading-relaxed">
                If you disagree with our refund decision, you may:
              </p>
              <ul className="list-disc list-inside text-gray-700 mt-4 space-y-2">
                <li>Request a review by our management team</li>
                <li>Provide additional documentation to support your case</li>
                <li>Contact our customer success team for assistance</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">9. Changes to This Policy</h2>
              <p className="text-gray-700 leading-relaxed">
                We reserve the right to modify this Return & Refund Policy at any time. Changes will be effective immediately upon posting. We will notify users of significant changes via email or through our service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">10. Contact Information</h2>
              <p className="text-gray-700 leading-relaxed">
                For questions about returns, refunds, or this policy, please contact us:
              </p>
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-700">
                  <strong>Email:</strong> info@yourcompany.com<br />
                  <strong></strong><br />
                  <strong>Business Hours:</strong> Monday - Friday, 9:00 AM - 6:00 PM EST
                </p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-brand-red mb-4">11. Legal Rights</h2>
              <p className="text-gray-700 leading-relaxed">
                This policy does not affect your statutory rights as a consumer. If you are located in a jurisdiction that provides additional consumer protection rights, those rights remain in full force and effect.
              </p>
            </section>
          </div>

          <div className="mt-12 pt-8 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row justify-between items-center">
              <p className="text-gray-600 text-sm">
                We're committed to fair and transparent refund practices.
              </p>
              <div className="mt-4 sm:mt-0">
                <Link 
                  to="/" 
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-brand-red hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-red"
                >
                  Back to Home
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReturnPolicy;
