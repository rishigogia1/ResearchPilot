/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc7fb',
          400: '#36abf7',
          500: '#0c8fe8',
          600: '#0170c6',
          700: '#0259a0',
          800: '#064c83',
          900: '#0a3f6d',
          950: '#072848',
        },
      },
    },
  },
  plugins: [],
}
