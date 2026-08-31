/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          'navy-darkest': '#0B0F1F',
          'navy-dark': '#141A2E',
          'navy-mesh-1': '#1E1B4B',
          'red-primary': '#DC2626',
          'red-bright': '#EF4444',
          'red-dark': '#7C2D12',
          red: '#DC2626',
          black: '#0B0F1F',
          white: '#FFFFFF',
          night: '#141A2E',
        },
      },
    },
  },
  plugins: [],
}
