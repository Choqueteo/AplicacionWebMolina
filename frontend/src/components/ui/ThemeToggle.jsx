import { useTheme } from '../../context/ThemeContext'
import styles from './ThemeToggle.module.css'

export default function ThemeToggle() {
  const { tema, toggleTema } = useTheme()

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={toggleTema}
      aria-label={tema === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      title={tema === 'dark' ? 'Modo claro' : 'Modo oscuro'}
    >
      {tema === 'dark' ? '☀' : '☽'}
    </button>
  )
}
