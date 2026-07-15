import { Link } from 'react-router-dom'
import styles from './LegalLayout.module.css'

export default function LegalLayout({ titulo, children }) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link to="/" className={styles.volver}>← Inicio</Link>
      </header>
      <main className={styles.contenido}>
        <h1 className={styles.titulo}>{titulo}</h1>
        {children}
      </main>
    </div>
  )
}
