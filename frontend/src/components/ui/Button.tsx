import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'dark' | 'ghost' | 'primary'
export type ButtonSize = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export function Button({ variant = 'dark', className = '', children, ...props }: ButtonProps) {
  const variantClass = variant === 'ghost' ? 'ghost-btn' : variant === 'primary' ? 'primary-btn' : ''
  return (
    <button className={`${variantClass} ${className}`.trim()} {...props}>
      {children}
    </button>
  )
}
