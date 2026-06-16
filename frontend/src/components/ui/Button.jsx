import Spinner from './Spinner'
import styles from './Button.module.css'

export default function Button({
  children,
  loading = false,
  variant = 'primary',
  type = 'button',
  className = '',
  ...props
}) {
  return (
    <button
      type={type}
      className={`${styles.btn} ${styles[variant]} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <Spinner size={16} />}
      <span>{children}</span>
    </button>
  )
}
