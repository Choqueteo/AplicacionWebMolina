import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import ThemeToggle from '../components/ui/ThemeToggle'
import Spinner from '../components/ui/Spinner'
import TabReservar from '../components/cliente/TabReservar'
import TabMisCitas from '../components/cliente/TabMisCitas'
import client from '../api/client'
import logoRm from '../assets/logo-rm.png'
import styles from './DashboardCliente.module.css'

export default function DashboardCliente() {
  const { usuario, logout } = useAuth()
  const [pestana, setPestana] = useState('reservar')

  const [servicios, setServicios] = useState([])
  const [horario, setHorario]     = useState([])
  const [cargando, setCargando]   = useState(true)
  const [errorCarga, setErrorCarga] = useState('')

  useEffect(() => {
    Promise.all([
      client.get('/servicios'),
      client.get('/horario'),
    ])
      .then(([sRes, hRes]) => {
        setServicios(sRes.data)
        setHorario(hRes.data)
      })
      .catch(() => setErrorCarga('No se pudieron cargar los datos. Recarga la página.'))
      .finally(() => setCargando(false))
  }, [])

  // Mapa id → servicio para que TabMisCitas cruce nombres sin llamadas extra
  const serviciosMap = Object.fromEntries(servicios.map(s => [s.id, s]))

  // Set de dias_semana con al menos un tramo abierto (0=lunes … 6=domingo)
  const diasAbiertos = new Set(horario.map(h => h.dia_semana))

  return (
    <div className={styles.page}>
      {/* Cabecera */}
      <header className={styles.header}>
        <img src={logoRm} alt="RM Peluquería" className={styles.logo} />
        <span className={styles.nombreUsuario}>
          {usuario?.nombre_completo?.split(' ')[0]}
        </span>
        <div className={styles.headerAcciones}>
          <ThemeToggle />
          <button
            type="button"
            className={styles.btnLogout}
            onClick={logout}
          >
            Salir
          </button>
        </div>
      </header>

      {/* Pestañas */}
      <nav className={styles.tabs} data-tab={pestana} aria-label="Secciones del dashboard">
        <button
          type="button"
          className={`${styles.tab} ${pestana === 'reservar' ? styles.tabActiva : ''}`}
          onClick={() => setPestana('reservar')}
          aria-current={pestana === 'reservar' ? 'page' : undefined}
        >
          Reservar
        </button>
        <button
          type="button"
          className={`${styles.tab} ${pestana === 'mis-citas' ? styles.tabActiva : ''}`}
          onClick={() => setPestana('mis-citas')}
          aria-current={pestana === 'mis-citas' ? 'page' : undefined}
        >
          Mis citas
        </button>
      </nav>

      {/* Contenido */}
      <main className={styles.contenido}>
        {cargando ? (
          <div className={styles.cargandoWrap}>
            <Spinner size={28} />
          </div>
        ) : errorCarga ? (
          <p className={styles.errorCarga}>{errorCarga}</p>
        ) : (
          <div key={pestana} className={styles.tabContent}>
            {pestana === 'reservar' ? (
              <TabReservar
                servicios={servicios}
                diasAbiertos={diasAbiertos}
                onVerMisCitas={() => setPestana('mis-citas')}
              />
            ) : (
              <TabMisCitas
                serviciosMap={serviciosMap}
                onReservar={() => setPestana('reservar')}
              />
            )}
          </div>
        )}
      </main>
    </div>
  )
}
