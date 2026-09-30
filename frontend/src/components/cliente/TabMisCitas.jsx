import { useEffect, useState } from 'react'
import client from '../../api/client'
import Spinner from '../ui/Spinner'
import { capitalizar } from '../../utils/texto'
import Calendario from './Calendario'
import styles from './TabMisCitas.module.css'

function esPasada(cita) {
  const [y, m, d] = cita.fecha.split('-').map(Number)
  const [h, min]  = cita.hora_inicio.split(':').map(Number)
  return new Date(y, m - 1, d, h, min) <= new Date()
}

function tieneAntelacion(cita) {
  const [y, m, d] = cita.fecha.split('-').map(Number)
  const [h, min]  = cita.hora_inicio.split(':').map(Number)
  return new Date(y, m - 1, d, h, min) > new Date(Date.now() + 24 * 60 * 60 * 1000)
}

function fechaAStr(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function formatDuracionMin(minutos) {
  if (minutos >= 60 && minutos % 60 === 0) return `${minutos / 60} h`
  if (minutos >= 60) return `${Math.floor(minutos / 60)} h ${minutos % 60} min`
  return `${minutos} min`
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

export default function TabMisCitas({ serviciosMap, diasAbiertos = new Set(), fechasCerradas = new Set(), onReservar }) {
  const [citas, setCitas]               = useState([])
  const [cargando, setCargando]         = useState(true)
  const [errorCarga, setErrorCarga]     = useState('')
  const [cancelando, setCancelando]     = useState(null)
  const [cargandoCancel, setCargandoCancel] = useState(false)
  const [errorCancel, setErrorCancel]   = useState('')

  // Estado del modal de reprogramación
  const [reprogramando, setReprogramando]   = useState(null)   // cita | null
  const [fechaReprog, setFechaReprog]       = useState(null)
  const [horaReprog, setHoraReprog]         = useState(null)
  const [horasDisp, setHorasDisp]           = useState([])
  const [cargandoHoras, setCargandoHoras]   = useState(false)
  const [cargandoReprog, setCargandoReprog] = useState(false)
  const [errorReprog, setErrorReprog]       = useState('')

  const cargarCitas = () => {
    client.get('/citas/mias')
      .then(r => setCitas(r.data))
      .catch(() => setErrorCarga('No se pudieron cargar tus citas. Recarga la página.'))
      .finally(() => setCargando(false))
  }

  useEffect(() => { cargarCitas() }, [])

  // Cargar horas disponibles cuando cambia la fecha en el modal de reprogramación
  useEffect(() => {
    if (!reprogramando || !fechaReprog) { setHorasDisp([]); return }
    setCargandoHoras(true)
    setHoraReprog(null)
    const fechaStr = fechaAStr(fechaReprog)
    client.get(`/disponibilidad?fecha=${fechaStr}&servicio_id=${reprogramando.servicio_id}`)
      .then(r => setHorasDisp(r.data.horas_disponibles))
      .catch(() => setHorasDisp([]))
      .finally(() => setCargandoHoras(false))
  }, [fechaReprog, reprogramando])

  const abrirModal = (id) => {
    setErrorCancel('')
    setCancelando(id)
  }

  const cerrarModal = () => {
    setCancelando(null)
    setErrorCancel('')
  }

  const abrirReprogramar = (cita) => {
    setReprogramando(cita)
    setFechaReprog(null)
    setHoraReprog(null)
    setHorasDisp([])
    setErrorReprog('')
  }

  const cerrarReprogramar = () => {
    setReprogramando(null)
    setFechaReprog(null)
    setHoraReprog(null)
    setHorasDisp([])
    setErrorReprog('')
  }

  const confirmarReprogramar = async () => {
    if (!reprogramando || !fechaReprog || !horaReprog) return
    setErrorReprog('')
    setCargandoReprog(true)
    try {
      const r = await client.patch(`/citas/${reprogramando.id}/reprogramar`, {
        fecha: fechaAStr(fechaReprog),
        hora_inicio: horaReprog,
      })
      setCitas(prev => prev.map(c => c.id === reprogramando.id ? r.data : c))
      cerrarReprogramar()
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 409) {
        setErrorReprog('Ese hueco se acaba de ocupar. Elige otra fecha u hora.')
        cargarCitas()
      } else if (status === 422 || status === 403) {
        setErrorReprog(detail || 'No se pudo reprogramar. Comprueba los datos.')
      } else {
        setErrorReprog('Error inesperado. Inténtalo de nuevo.')
      }
    } finally {
      setCargandoReprog(false)
    }
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
        const { texto, clase }  = derivarEtiqueta(cita)
        const puedeCancelar     = cita.estado === 'activa' && !esPasada(cita)
        const puedeReprogramar  = cita.estado === 'activa' && tieneAntelacion(cita)
        const modalAbierto      = cancelando === cita.id
        const reprogAbierto     = reprogramando?.id === cita.id

        return (
          <article key={cita.id} className={styles.citaCard}>
            <div className={styles.citaHeader}>
              <span className={styles.citaNombre}>{nombre}</span>
              <span className={`${styles.etiqueta} ${styles[clase]}`}>{texto}</span>
            </div>
            <div className={styles.citaMeta}>
              <span>{capitalizar(formatFecha(cita.fecha))}</span>
              <span className={styles.separador}>·</span>
              <span>{cita.hora_inicio.slice(0, 5)}</span>
              <span className={styles.separador}>·</span>
              <span>{formatDuracion(duracion)}</span>
            </div>

            {/* Botones de acción (solo si no hay modal abierto) */}
            {!modalAbierto && !reprogAbierto && (puedeCancelar || puedeReprogramar) && (
              <div className={styles.acciones}>
                {puedeReprogramar && (
                  <button
                    type="button"
                    className={styles.btnReprogramar}
                    onClick={() => abrirReprogramar(cita)}
                  >
                    Cambiar fecha
                  </button>
                )}
                {puedeCancelar && (
                  <button
                    type="button"
                    className={styles.btnCancelar}
                    onClick={() => abrirModal(cita.id)}
                  >
                    Cancelar cita
                  </button>
                )}
              </div>
            )}

            {/* Modal cancelar */}
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

            {/* Modal reprogramar */}
            {reprogAbierto && (
              <div
                className={styles.modalReprog}
                role="dialog"
                aria-modal="true"
                aria-label="Reprogramar cita"
              >
                <p className={styles.servicioFijo}>
                  {nombre} · {formatDuracionMin(servicio ? servicio.duracion_minutos : duracion)}
                </p>

                <Calendario
                  diasAbiertos={diasAbiertos}
                  fechasCerradas={fechasCerradas}
                  fechaSeleccionada={fechaReprog}
                  onSeleccionar={setFechaReprog}
                  permitirPasados={false}
                />

                {fechaReprog && (
                  <div className={styles.horasWrap}>
                    {cargandoHoras ? (
                      <div className={styles.centrado}><Spinner size={18} /></div>
                    ) : horasDisp.length === 0 ? (
                      <p className={styles.sinHoras}>Sin horas disponibles para este día.</p>
                    ) : (
                      <div className={styles.horasGrid}>
                        {horasDisp.map(h => (
                          <button
                            key={h}
                            type="button"
                            className={`${styles.horaBtn} ${horaReprog === h ? styles.horaBtnSel : ''}`}
                            onClick={() => setHoraReprog(h)}
                          >
                            {h.slice(0, 5)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {errorReprog && (
                  <p className={styles.errorMsg} role="alert">{errorReprog}</p>
                )}

                <div className={styles.modalAcciones}>
                  <button
                    type="button"
                    className={styles.btnConfirmarReprog}
                    disabled={!fechaReprog || !horaReprog || cargandoReprog}
                    onClick={confirmarReprogramar}
                  >
                    {cargandoReprog ? 'Guardando…' : 'Confirmar cambio'}
                  </button>
                  <button
                    type="button"
                    className={styles.btnVolver}
                    disabled={cargandoReprog}
                    onClick={cerrarReprogramar}
                  >
                    Cancelar
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
