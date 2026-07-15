import { Link } from 'react-router-dom'
import styles from './Footer.module.css'

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <nav className={styles.links} aria-label="Páginas legales">
        <Link to="/aviso-legal"         className={styles.link}>Aviso legal</Link>
        <span className={styles.sep} aria-hidden="true">·</span>
        <Link to="/politica-privacidad" className={styles.link}>Política de privacidad</Link>
        <span className={styles.sep} aria-hidden="true">·</span>
        <Link to="/politica-cookies"    className={styles.link}>Política de cookies</Link>
      </nav>
    </footer>
  )
}
