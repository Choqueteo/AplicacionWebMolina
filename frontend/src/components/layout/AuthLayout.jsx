import logoRm from '../../assets/logo-rm.png'
import ThemeToggle from '../ui/ThemeToggle'
import styles from './AuthLayout.module.css'

export default function AuthLayout({ children }) {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <img
            src={logoRm}
            alt="RM — Peluquería · Barbería"
            className={styles.logo}
          />
          <ThemeToggle />
        </div>
        <div className={styles.cardBody}>
          {children}
        </div>
      </div>
    </div>
  )
}
