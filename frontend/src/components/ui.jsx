import React, { forwardRef } from 'react'

// ===========================================================================
// Button
// ===========================================================================
export const Button = forwardRef(function Button(
  { variant = 'secondary', size = 'md', className = '', children, disabled, ...rest }, ref
) {
  const base =
    'inline-flex items-center justify-center gap-1.5 font-medium rounded transition-colors duration-150 ease-standard ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 ' +
    'disabled:opacity-40 disabled:cursor-not-allowed select-none whitespace-nowrap'
  const variants = {
    primary:   'bg-brand text-brand-fg hover:bg-brand-hover',
    secondary: 'bg-surface text-ink border border-border hover:bg-surface-subtle',
    ghost:     'text-ink-muted hover:bg-surface-muted hover:text-ink',
    danger:    'bg-surface text-danger border border-border hover:bg-danger-subtle hover:border-danger/30',
    success:   'bg-success text-white hover:bg-success-strong',
    link:      'text-brand hover:text-brand-hover underline-offset-2 hover:underline',
  }
  const sizes = {
    sm: 'h-7 px-2.5 text-label-sm',
    md: 'h-9 px-3.5 text-label-md',
    lg: 'h-11 px-5 text-label-md',
    icon: 'h-9 w-9 text-label-md',
  }
  return (
    <button
      ref={ref}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
})

// ===========================================================================
// Card / Surface
// ===========================================================================
export function Card({ className = '', children, ...rest }) {
  return (
    <div
      className={`bg-surface border border-border rounded-lg shadow-card ${className}`}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, description, action, className = '' }) {
  return (
    <div className={`flex items-start justify-between gap-4 px-5 py-4 border-b border-border ${className}`}>
      <div>
        <h3 className="text-headline-sm text-ink">{title}</h3>
        {description && <p className="mt-0.5 text-body-sm text-ink-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function CardBody({ className = '', children }) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>
}

// ===========================================================================
// Input + TextArea
// ===========================================================================
export const Input = forwardRef(function Input({ className = '', invalid, ...rest }, ref) {
  return (
    <input
      ref={ref}
      className={`block w-full h-9 px-3 text-body-sm text-ink bg-surface border rounded transition-colors duration-150 placeholder:text-ink-faint
        ${invalid ? 'border-danger focus-visible:ring-danger/20 focus-visible:border-danger' : 'border-border focus-visible:ring-brand/30 focus-visible:border-brand'}
        focus-visible:outline-none focus-visible:ring-2 ${className}`}
      {...rest}
    />
  )
})

export const TextArea = forwardRef(function TextArea({ className = '', rows = 3, invalid, ...rest }, ref) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={`block w-full px-3 py-2 text-body-sm text-ink bg-surface border rounded transition-colors duration-150 resize-y placeholder:text-ink-faint
        ${invalid ? 'border-danger focus-visible:ring-danger/20 focus-visible:border-danger' : 'border-border focus-visible:ring-brand/30 focus-visible:border-brand'}
        focus-visible:outline-none focus-visible:ring-2 ${className}`}
      {...rest}
    />
  )
})

export function Select({ className = '', children, ...rest }) {
  return (
    <select
      className={`block w-full h-9 px-3 text-body-sm text-ink bg-surface border border-border rounded transition-colors duration-150
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 focus-visible:border-brand ${className}`}
      {...rest}
    >
      {children}
    </select>
  )
}

// ===========================================================================
// Field — label + control + hint pattern
// ===========================================================================
export function Field({ label, hint, error, required, children, className = '' }) {
  return (
    <label className={`block ${className}`}>
      {label && (
        <div className="mb-1.5 flex items-baseline gap-1">
          <span className="text-label-sm uppercase tracking-wide text-ink-muted">{label}</span>
          {required && <span className="text-danger text-label-sm">*</span>}
        </div>
      )}
      {children}
      {error
        ? <p className="mt-1 text-label-sm text-danger">{error}</p>
        : hint && <p className="mt-1 text-label-sm text-ink-subtle">{hint}</p>}
    </label>
  )
}

// ===========================================================================
// Badge / Pill
// ===========================================================================
export function Badge({ variant = 'neutral', children, className = '' }) {
  const variants = {
    neutral: 'bg-surface-muted text-ink-muted border-border',
    brand:   'bg-brand-subtle text-brand border-brand/15',
    success: 'bg-success-subtle text-success-strong border-success/15',
    warning: 'bg-warning-subtle text-warning-strong border-warning/15',
    danger:  'bg-danger-subtle text-danger-strong border-danger/15',
    info:    'bg-info-subtle text-info-strong border-info/15',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 h-5 rounded-full border text-label-sm ${variants[variant]} ${className}`}>
      {children}
    </span>
  )
}

// ===========================================================================
// Stat — used in the audit metrics row
// ===========================================================================
export function Stat({ label, value, hint, accent }) {
  return (
    <Card>
      <div className="px-5 py-4">
        <div className="text-label-sm uppercase tracking-wide text-ink-muted">{label}</div>
        <div className={`mt-1 text-headline-md ${accent || 'text-ink'}`}>{value}</div>
        {hint && <div className="mt-0.5 text-label-sm text-ink-subtle">{hint}</div>}
      </div>
    </Card>
  )
}

// ===========================================================================
// Empty state
// ===========================================================================
export function EmptyState({ title, description, action, icon }) {
  return (
    <Card>
      <div className="px-10 py-16 text-center">
        {icon && <div className="mx-auto mb-3 h-10 w-10 text-ink-faint">{icon}</div>}
        <p className="text-body-md text-ink font-medium">{title}</p>
        {description && <p className="mt-1 text-body-sm text-ink-muted max-w-md mx-auto">{description}</p>}
        {action && <div className="mt-5">{action}</div>}
      </div>
    </Card>
  )
}

// ===========================================================================
// PageHeader
// ===========================================================================
export function PageHeader({ title, description, actions }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-headline-lg text-ink">{title}</h1>
        {description && <p className="mt-1 text-body-md text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

// ===========================================================================
// Keyboard hint chip
// ===========================================================================
export function Kbd({ children }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded border border-border-strong bg-surface-muted text-label-sm text-ink-muted font-medium">
      {children}
    </kbd>
  )
}
