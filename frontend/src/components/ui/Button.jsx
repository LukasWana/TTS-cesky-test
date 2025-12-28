import React from 'react'
import { useSectionColor } from '../../contexts/SectionColorContext'
import './ui.css'

function Button({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  disabled = false,
  type = 'button',
  className = '',
  icon,
  iconPosition = 'left',
  fullWidth = false,
  ...props
}) {
  const { color, rgb } = useSectionColor()
  const baseClass = 'ui-button'
  const variantClass = `ui-button-${variant}`
  const sizeClass = `ui-button-${size}`
  const fullWidthClass = fullWidth ? 'ui-button-full-width' : ''
  const combinedClass = `${baseClass} ${variantClass} ${sizeClass} ${fullWidthClass} ${className}`.trim()

  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

  return (
    <button
      type={type}
      className={combinedClass}
      onClick={onClick}
      disabled={disabled}
      style={style}
      {...props}
    >
      {icon && iconPosition === 'left' && <span className="ui-button-icon ui-button-icon-left">{icon}</span>}
      {children && <span className="ui-button-content">{children}</span>}
      {icon && iconPosition === 'right' && <span className="ui-button-icon ui-button-icon-right">{icon}</span>}
    </button>
  )
}

export default Button

