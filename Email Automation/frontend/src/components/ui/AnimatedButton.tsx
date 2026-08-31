import React from 'react';
import { motion } from 'framer-motion';
import { Button } from './button';

interface AnimatedButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  disabled?: boolean;
}

export const AnimatedButton: React.FC<AnimatedButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
}) => {
  const baseClasses = 'relative overflow-hidden font-black uppercase tracking-tighter transition-all duration-300';
  
  const variantClasses = {
    primary: 'bg-gradient-red text-white hover:shadow-red-glow-intense',
    secondary: 'bg-transparent border-2 border-brand-red-primary text-brand-red-primary hover:bg-brand-red-primary hover:text-white',
  };
  
  const sizeClasses = {
    sm: 'px-6 py-3 text-sm',
    md: 'px-8 py-4 text-base',
    lg: 'px-16 py-5 text-2xl h-20',
  };
  
  return (
    <motion.div
      whileHover={{ scale: 1.05, y: -2 }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
    >
      <Button
        onClick={onClick}
        disabled={disabled}
        className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className} btn-primary`}
      >
        {children}
      </Button>
    </motion.div>
  );
};
