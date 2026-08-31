import React from 'react';

interface SmoothTransitionProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

const SmoothTransition: React.FC<SmoothTransitionProps> = ({ 
  children, 
  className = '',
  delay = 0 
}) => {
  return (
    <div 
      className={`transition-all duration-500 ease-in-out ${className}`}
      style={{ 
        animationDelay: `${delay}ms`,
        animation: 'fadeInUp 0.6s ease-out forwards'
      }}
    >
      {children}
    </div>
  );
};

export default SmoothTransition;
