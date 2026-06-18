import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from '../components/ui/ThemeToggle'
import Spinner from '../components/ui/Spinner'
import TabAgenda from '../components/admin/TabAgenda'
import TabServicios from '../components/admin/TabServicios'
import TabHorario from '../components/admin/TabHorario'
import TabClientes from '../components/admin/TabClientes'
import client from '../api/client'
import logoRm from '../assets/logo-rm.png'
import styles from './DashboardAdmin.module.css'

function fechaAString(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function PanelAdmin() {
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()
  const [seccion, setSeccion] = useState('agenda')

  const [fecha, setFecha] = useState(() => fechaAString(new Date()))
  const [citas, setCitas] = useState([])
  const [cargandoCitas, setCargandoCitas] = useState(true)

  const [clientesMap, setClientesMap] = useState({})
  const [serviciosMap, setServiciosMap] = useState({})
  const [cargandoBase, setCargandoBase] = useState(true)
  const [errorBase, setErrorBase] = useState('')

  useEffect(() => {
    Promise.all([
      client.get('/usuarios'),
      client.get('/servicios', { params: { incluir_inactivos: true } }),
    ])
      .then(([uRes, sRes]) => {
        setClientesMap(Object.fromEntries(uRes.data.map(u => [u.id, u])))
        setServiciosMap(Object.fromEntries(sRes.data.map(s => [s.id, s])))
      })
      .catch(() => setErrorBase('Error al cargar datos. Recarga la página.'))
      .finally(() => setCargandoBase(false))
  }, [])

  const cargarCitas = useCallback((f) => {
    setCargandoCitas(true)
    client.get('/citas', { params: { fecha: f } })
      .then(r => setCitas(r.data))
      .catch(() => setCitas([]))
      .finally(() => setCargandoCitas(false))
  }, [])

  useEffect(() => {
    cargarCitas(fecha)
  }, [fecha, cargarCitas])

  const NAV_ITEMS = [
    { id: 'agenda',    label: 'Agenda',    icon: '▦' },
    { id: 'servicios', label: 'Servicios', icon: '✂' },
    { id: 'horario',   label: 'Horario',   icon: '◷' },
    { id: 'clientes',  label: 'Clientes',  icon: '♟' },
  ]

  if (cargandoBase) {
    return (
      <div className={styles.page}>
        <div className={styles.centrado}><Spinner size={28} /></div>
      </div>
    )
  }

  if (errorBase) {
    return (
      <div className={styles.page}>
        <p className={styles.errorCarga}>{errorBase}</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      {/* Cabecera */}
      <header className={styles.header}>
        <img src={logoRm} alt="RM Peluquería" className={styles.logo} />
        <button
          type="button"
          className={styles.btnMiCuenta}
          onClick={() => navigate('/mi-cuenta')}
          title="Mi cuenta"
        >
          {usuario?.nombre_completo?.split(' ')[0]}
        </button>
        <div className={styles.headerAcciones}>
          <ThemeToggle />
          <button type="button" className={styles.btnLogout} onClick={logout}>
            Salir
          </button>
        </div>
      </header>

      {/* Contenido */}
      <main className={styles.contenido}>
        {seccion === 'agenda' && (
          <TabAgenda
            key={fecha}
            citas={citas}
            clientesMap={clientesMap}
            serviciosMap={serviciosMap}
            fecha={fecha}
            onFechaChange={setFecha}
            cargando={cargandoCitas}
          />
        )}
        {seccion === 'servicios' && <TabServicios />}
        {seccion === 'horario'   && <TabHorario />}
        {seccion === 'clientes'  && <TabClientes />}
      </main>

      {/* Barra inferior fija */}
      <nav className={styles.bottomNav} aria-label="Secciones del panel">
        {NAV_ITEMS.map(({ id, label, icon }) => (
          <button
            key={id}
            type="button"
            className={`${styles.navItem} ${seccion === id ? styles.navItemActivo : ''}`}
            onClick={() => setSeccion(id)}
            aria-current={seccion === id ? 'page' : undefined}
          >
            <span className={styles.navIcon} aria-hidden="true">{icon}</span>
            <span className={styles.navLabel}>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
