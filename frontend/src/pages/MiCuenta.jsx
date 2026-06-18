import { useNavigate } from 'react-router-dom'
import ThemeToggle from '../components/ui/ThemeToggle'
import FormularioPerfil from '../components/cuenta/FormularioPerfil'
import FormularioPassword from '../components/cuenta/FormularioPassword'
import styles from './MiCuenta.module.css'

export default function MiCuenta() {
  const navigate = useNavigate()

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button
          type="button"
          className={styles.btnVolver}
          onClick={() => navigate(-1)}
          aria-label="Volver al dashboard"
        >
          ← Volver
        </button>
        <span className={styles.titulo}>Mi cuenta</span>
        <ThemeToggle />
      </header>
      <main className={styles.contenido}>
        <FormularioPerfil />
        <FormularioPassword />
      </main>
    </div>
  )
}
