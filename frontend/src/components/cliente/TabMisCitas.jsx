import { useEffect, useState } from 'react'
import client from '../../api/client'
import Spinner from '../ui/Spinner'
import styles from './TabMisCitas.module.css'

function esPasada(cita) {
  const [y, m, d] = cita.fecha.split('-').map(Number)
  const [h, min]  = cita.hora_inicio.split(':').map(Number)
  return new Date(y, m - 1, d, h, min) <= new Date()
}

function calcDuracionMinutos(hora_inicio, hora_fin) {
  const [hi, mi] = hora_inicio.split(':').map(Number)
  const [hf, mf] = hora_fin.split(':').map(Number)
  return (hf * 60 + mf) - (hi * 60 + mi)
}

function formatDuracion(minutos) {
  if (minutos >= 60 && minutos % 60 === 0) return `${minutos / 60} h`
  if (minutos >= 60) return `${Math.floor(minutos / 60)} h ${minutos % 60} min`
  return `${minutos} min`
}

function formatFecha(fechaStr) {
  const [y, m, d] = fechaStr.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

function derivarEtiqueta(cita) {
  if (cita.estado === 'cancelada')   return { texto: 'Cancelada',  clase: 'etiquetaCancelada'  }
  if (cita.estado === 'no_asistida') return { texto: 'No asistió', clase: 'etiquetaNoAsistio'  }
  if (esPasada(cita))                return { texto: 'Realizada',  clase: 'etiquetaRealizada'  }
  return                                    { texto: 'Reservada',  clase: 'etiquetaReservada'  }
}

function ordenarCitas(citas) {
  const proximas = citas.filter(c => c.estado === 'activa' && !esPasada(c))
  const resto    = citas.filter(c => !(c.estado === 'activa' && !esPasada(c)))
  return [...proximas, ...resto]
}

export default function TabMisCitas({ serviciosMap, onReservar }) {
  const [citas, setCitas]               = useState([])
  const [cargando, setCargando]         = useState(true)
  const [errorCarga, setErrorCarga]     = useState('')
  const [cancelando, setCancelando]     = useState(null)   // id de la cita con modal abierto
  const [cargandoCancel, setCargandoCancel] = useState(false)
  const [errorCancel, setErrorCancel]   = useState('')

  useEffect(() => {
    client.get('/citas/mias')
      .then(r => setCitas(r.data))
      .catch(() => setErrorCarga('No se pudieron cargar tus citas. Recarga la página.'))
      .finally(() => setCargando(false))
  }, [])

  const abrirModal = (id) => {
    setErrorCancel('')
    setCancelando(id)
  }

  const cerrarModal = () => {
    setCancelando(null)
    setErrorCancel('')
  }

  const confirmarCancelacion = async (id) => {
    setErrorCancel('')
    setCargandoCancel(true)
    try {
      const r = await client.patch(`/citas/${id}/cancelar`)
      setCitas(prev => prev.map(c => c.id === id ? r.data : c))
      setCancelando(null)
    } catch (err) {
      const status = err.response?.status
      if (status === 409) {
        setErrorCancel('Esta cita ya estaba cancelada.')
      } else if (status === 422) {
        setErrorCancel('No se puede cancelar una cita pasada.')
      } else {
        setErrorCancel('No se pudo cancelar. Inténtalo de nuevo.')
      }
    } finally {
      setCargandoCancel(false)
    }
  }

  if (cargando) {
    return <div className={styles.centrado}><Spinner size={24} /></div>
  }

  if (errorCarga) {
    return <p className={styles.errorMsg} role="alert">{errorCarga}</p>
  }

  if (citas.length === 0) {
    return (
      <div className={styles.vacio}>
        <p>Aún no tienes citas.</p>
        <button type="button" className={styles.linkReservar} onClick={onReservar}>
          Reservar ahora →
        </button>
      </div>
    )
  }

  return (
    <div className={styles.lista}>
      {ordenarCitas(citas).map(cita => {
        const servicio    = serviciosMap[cita.servicio_id]
        const nombre      = servicio ? servicio.nombre : 'Servicio'
        const duracion    = servicio
          ? servicio.duracion_minutos
          : calcDuracionMinutos(cita.hora_inicio, cita.hora_fin)
        const { texto, clase } = derivarEtiqueta(cita)
        const puedeCancelar    = cita.estado === 'activa' && !esPasada(cita)
        const modalAbierto     = cancelando === cita.id

        return (
          <article key={cita.id} className={styles.citaCard}>
            <div className={styles.citaHeader}>
              <span className={styles.citaNombre}>{nombre}</span>
              <span className={`${styles.etiqueta} ${styles[clase]}`}>{texto}</span>
            </div>
            <div className={styles.citaMeta}>
              <span style={{ textTransform: 'capitalize' }}>{formatFecha(cita.fecha)}</span>
              <span className={styles.separador}>·</span>
              <span>{cita.hora_inicio}</span>
              <span className={styles.separador}>·</span>
              <span>{formatDuracion(duracion)}</span>
            </div>

            {puedeCancelar && !modalAbierto && (
              <button
                type="button"
                className={styles.btnCancelar}
                onClick={() => abrirModal(cita.id)}
              >
                Cancelar cita
              </button>
            )}

            {modalAbierto && (
              <div
                className={styles.modal}
                role="dialog"
                aria-modal="true"
                aria-label="Confirmar cancelación"
              >
                <p className={styles.modalTexto}>
                  ¿Cancelar esta cita? Esta acción no se puede deshacer.
                </p>
                {errorCancel && (
                  <p className={styles.errorMsg} role="alert">{errorCancel}</p>
                )}
                <div className={styles.modalAcciones}>
                  <button
                    type="button"
                    className={styles.btnConfirmarCancel}
                    disabled={cargandoCancel}
                    onClick={() => confirmarCancelacion(cita.id)}
                  >
                    {cargandoCancel ? 'Cancelando…' : 'Confirmar'}
                  </button>
                  <button
                    type="button"
                    className={styles.btnVolver}
                    disabled={cargandoCancel}
                    onClick={cerrarModal}
                  >
                    Volver
                  </button>
                </div>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
