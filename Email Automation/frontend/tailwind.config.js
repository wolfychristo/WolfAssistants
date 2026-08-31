/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Brand Colors - Premium Dark Navy + Crimson Red Theme
        brand: {
          // Navy Colors
          'navy-darkest': '#0B0F1F',
          'navy-dark': '#141A2E',
          'navy-mesh-1': '#1E1B4B',
          // Red Colors
          'red-primary': '#DC2626',
          'red-bright': '#EF4444',
          'red-dark': '#7C2D12',
          // Legacy (keeping for backward compatibility during transition)
          red: '#DC2626',
          black: '#0B0F1F',
          white: '#FFFFFF',
          night: '#141A2E',
        },
        // Navy scale
        navy: {
          50: '#F0F4F8',
          100: '#D9E2EC',
          200: '#BCCCDC',
          300: '#9FB3C8',
          400: '#829AB1',
          500: '#627D98',
          600: '#486581',
          700: '#334E68',
          800: '#243B53',
          900: '#102A43',
          950: '#0B0F1F',
        },
        // Primary color palette based on brand red
        primary: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#e32625', // Brand red
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        // Secondary color palette - simplified
        secondary: {
          50: '#f8f9fa',
          100: '#f1f3f5',
          200: '#e9ecef',
          300: '#dee2e6',
          400: '#ced4da',
          500: '#adb5bd', 
          600: '#868e96',
          700: '#495057',
          800: '#343a40',
          900: '#212529',
        },
        // Neutral colors based on brand black
        neutral: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
        // Accent colors
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        // Accent colors
        accent: {
          blue: '#3B82F6',
          green: '#10B981',
        },
        // Text colors
        text: {
          primary: '#FFFFFF',
          secondary: '#94A3B8',
          tertiary: '#64748B',
        }
      },
      backgroundImage: {
        'gradient-hero': 'linear-gradient(135deg, #DC2626 0%, #7C2D12 50%, #0B0F1F 100%)',
        'gradient-red': 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)',
        'gradient-text': 'linear-gradient(135deg, #FFFFFF 0%, #DC2626 100%)',
        'gradient-text-red': 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)',
        'gradient-card': 'linear-gradient(90deg, #DC2626 0%, rgba(220, 38, 38, 0) 100%)',
      },
      boxShadow: {
        'red': '0 20px 40px rgba(220, 38, 38, 0.5)',
        'red-intense': '0 30px 60px rgba(220, 38, 38, 0.6)',
        'red-glow': '0 0 20px rgba(220, 38, 38, 0.4), 0 0 40px rgba(220, 38, 38, 0.3), 0 0 60px rgba(220, 38, 38, 0.2)',
        'red-glow-intense': '0 0 30px rgba(220, 38, 38, 0.6), 0 0 60px rgba(220, 38, 38, 0.4), 0 0 90px rgba(220, 38, 38, 0.2)',
        'card': '0 8px 32px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'shimmer': 'shimmer 2s infinite',
        'float': 'float 3s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 15s ease infinite',
        'gradient-shift-red': 'gradient-shift-red 10s ease infinite',
        'border-rotate': 'border-rotate 3s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(220, 38, 38, 0.4)' },
          '50%': { boxShadow: '0 0 40px rgba(220, 38, 38, 0.7)' },
        },
        'gradient-shift': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'gradient-shift-red': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'border-rotate': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      }
    },
  },
  plugins: [],
} 