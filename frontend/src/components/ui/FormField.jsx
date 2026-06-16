import styles from './FormField.module.css'

export default function FormField({
  label,
  name,
  type = 'text',
  error,
  ayuda,
  suffix,
  className = '',
  ...inputProps
}) {
  const id      = inputProps.id || name
  const ayudaId = ayuda ? `${id}-ayuda` : null
  const errorId = error ? `${id}-error` : null
  const describedBy = [ayudaId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={`${styles.field} ${error ? styles.hasError : ''} ${className}`}>
      <label className={styles.label} htmlFor={id}>{label}</label>
      <div className={styles.inputWrap}>
        <input
          id={id}
          name={name}
          type={type}
          className={styles.input}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          {...inputProps}
        />
        {suffix && <span className={styles.suffix}>{suffix}</span>}
      </div>
      {ayuda && (
        <span id={ayudaId} className={styles.ayudaMsg}>
          {ayuda}
        </span>
      )}
      {error && (
        <span id={errorId} className={styles.errorMsg} role="alert">
          {error}
        </span>
      )}
    </div>
  )
}
