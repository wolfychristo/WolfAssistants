import React from 'react';

interface GradientTextProps {
  children: React.ReactNode;
  variant?: 'default' | 'red';
  className?: string;
}

export const GradientText: React.FC<GradientTextProps> = ({ 
  children, 
  variant = 'default',
  className = '' 
}) => {
  const gradientClass = variant === 'red' ? 'gradient-text-red' : 'gradient-text';
  
  return (
    <span className={`${gradientClass} ${className}`}>
      {children}
    </span>
  );
};
