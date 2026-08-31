import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface ShareLinkProps {
  entityType: 'email' | 'contact' | 'meeting' | 'chat';
  publicId: string;
  className?: string;
}

const ShareLink: React.FC<ShareLinkProps> = ({ entityType, publicId, className = '' }) => {
  const [copied, setCopied] = useState(false);
  
  const generateLink = () => {
    const baseUrl = window.location.origin;
    // Map entity types to URL paths
    const pathMap: Record<typeof entityType, string> = {
      email: 'emails',
      contact: 'contacts',
      meeting: 'meetings',
      chat: 'chat'
    };
    
    return `${baseUrl}/${pathMap[entityType]}/${publicId}`;
  };
  
  const shareableLink = generateLink();
  
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareableLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy link:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = shareableLink;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy failed:', fallbackErr);
      }
      document.body.removeChild(textArea);
    }
  };
  
  return (
    <button
      onClick={copyToClipboard}
      className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors ${
        copied 
          ? 'bg-green-100 text-green-700 hover:bg-green-200' 
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      } ${className}`}
      title={copied ? 'Link copied!' : 'Copy link'}
    >
      {copied ? (
        <>
          <Check className="w-4 h-4" />
          <span>Copied!</span>
        </>
      ) : (
        <>
          <Copy className="w-4 h-4" />
          <span>Copy Link</span>
        </>
      )}
    </button>
  );
};

export default ShareLink;
