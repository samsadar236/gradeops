/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Surface scale (Material 3 tonal palette adapted to the spec)
        background: '#F9FAFB',
        surface: {
          DEFAULT: '#FFFFFF',
          subtle: '#F9FAFB',
          muted: '#F3F4F6',
          inset: '#F1F3FF',
        },
        // Strokes
        border: {
          DEFAULT: '#E5E7EB',
          strong: '#D1D5DB',
          subtle: '#F3F4F6',
        },
        // Text
        ink: {
          DEFAULT: '#111827',
          muted: '#4B5563',
          subtle: '#6B7280',
          faint: '#9CA3AF',
        },
        // Brand (indigo)
        brand: {
          DEFAULT: '#4F46E5',
          hover: '#4338CA',
          fg: '#FFFFFF',
          subtle: '#EEF2FF',
          ring: 'rgba(79, 70, 229, 0.12)',
        },
        // Status
        success: { DEFAULT: '#059669', subtle: '#ECFDF5', strong: '#047857' },
        warning: { DEFAULT: '#D97706', subtle: '#FFFBEB', strong: '#B45309' },
        danger:  { DEFAULT: '#DC2626', subtle: '#FEF2F2', strong: '#B91C1C' },
        info:    { DEFAULT: '#2563EB', subtle: '#EFF6FF', strong: '#1D4ED8' },
      },
      fontSize: {
        // Spec-defined scale
        'display-lg': ['48px', { lineHeight: '56px', letterSpacing: '-0.02em', fontWeight: '700' }],
        'headline-lg':['32px', { lineHeight: '40px', letterSpacing: '-0.02em', fontWeight: '600' }],
        'headline-md':['24px', { lineHeight: '32px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline-sm':['20px', { lineHeight: '28px', fontWeight: '600' }],
        'body-lg':    ['18px', { lineHeight: '28px', fontWeight: '400' }],
        'body-md':    ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body-sm':    ['14px', { lineHeight: '20px', fontWeight: '400' }],
        'label-md':   ['14px', { lineHeight: '20px', fontWeight: '500' }],
        'label-sm':   ['12px', { lineHeight: '16px', letterSpacing: '0.01em', fontWeight: '500' }],
      },
      borderRadius: {
        sm: '0.125rem',
        DEFAULT: '0.25rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
      },
      boxShadow: {
        // Soft, low-opacity, large-blur — never aggressive
        card: '0 1px 2px 0 rgba(17, 24, 39, 0.04)',
        elevated: '0 4px 12px -2px rgba(17, 24, 39, 0.08), 0 1px 2px rgba(17, 24, 39, 0.04)',
        popover: '0 8px 24px -6px rgba(17, 24, 39, 0.12), 0 2px 4px rgba(17, 24, 39, 0.04)',
        'focus-ring': '0 0 0 3px rgba(79, 70, 229, 0.18)',
      },
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.2, 0, 0, 1)',
      },
      spacing: {
        '13': '3.25rem',
        '15': '3.75rem',
      },
    },
  },
  plugins: [],
}
