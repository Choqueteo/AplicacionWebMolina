import { useState } from 'react'
import client from '../../api/client'
import Spinner from '../ui/Spinner'
import Calendario from '../cliente/Calendario'
import styles from './TabAgenda.module.css'

function fechaAString(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function addDias(fechaStr, n) {
  const [y, m, d] = fechaStr.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  date.setDate(date.getDate() + n)
  return fechaAString(date)
}

function fechaADate(fechaStr) {
  const [y, m, d] = fechaStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function formatNavFecha(fechaStr) {
  return fechaADate(fechaStr).toLocaleDateString('es-ES', {
    weekday: 'short', day: 'numeric', month: 'short',
  })
}

function esPasada(cita) {
  const [y, m, d] = cita.fecha.split('-').map(Number)
  const [h, min]  = cita.hora_inicio.split(':').map(Number)
  return new Date(y, m - 1, d, h, min) <= new Date()
}

function derivarEtiqueta(cita) {
  if (cita.estado === 'cancelada')   return { texto: 'Cancelada',  clase: 'etiquetaCancelada'  }
  if (cita.estado === 'no_asistida') return { texto: 'No asistió', clase: 'etiquetaNoAsistio'  }
  if (esPasada(cita))                return { texto: 'Realizada',  clase: 'etiquetaRealizada'  }
  return                                    { texto: 'Reservada',  clase: 'etiquetaReservada'  }
}

export default function TabAgenda({ citas, clientesMap, serviciosMap, fecha, onFechaChange, cargando }) {
  const [mostrarCalendario, setMostrarCalendario] = useState(false)
  const [citaAccion, setCitaAccion] = useState(null)  // { cita, tipo: 'no-asistida' | 'cancelar' }
  const [procesando, setProcesando] = useState(false)
  const [errorAccion, setErrorAccion] = useState('')

  const hoyStr = fechaAString(new Date())
  const esHoy  = fecha === hoyStr

  const abrirAccion = (cita, tipo) => {
    setErrorAccion('')
    setCitaAccion({ cita, tipo })
  }

  const cerrarAccion = () => {
    setCitaAccion(null)
    setErrorAccion('')
  }

  const confirmarAccion = async () => {
    if (!citaAccion) return
    setProcesando(true)
    setErrorAccion('')
    const { cita, tipo } = citaAccion
    try {
      await client.patch(`/citas/${cita.id}/${tipo}`)
      setCitaAccion(null)
      onFechaChange(fecha)   // fuerza recarga del mismo día en el padre
    } catch (err) {
      const status = err.response?.status
      if (status === 422) setErrorAccion('Operación no permitida para esta cita.')
      else if (status === 409) setErrorAccion('La cita ya está en ese estado.')
      else setErrorAccion('Error al procesar la acción. Inténtalo de nuevo.')
    } finally {
      setProcesando(false)
    }
  }

  const handleSeleccionarFecha = (date) => {
    setMostrarCalendario(false)
    onFechaChange(fechaAString(date))
  }

  return (
    <div className={styles.agenda}>
      {/* Navegación de fecha */}
      <div className={styles.navFecha}>
        <div className={styles.navFechaMain}>
          <button
            type="button"
            className={styles.navBtn}
            onClick={() => onFechaChange(addDias(fecha, -1))}
            aria-label="Día anterior"
          >
            ‹
          </button>
          <span className={styles.fechaLabel} style={{ textTransform: 'capitalize' }}>
            {formatNavFecha(fecha)}
          </span>
          <button
            type="button"
            className={styles.navBtn}
            onClick={() => onFechaChange(addDias(fecha, 1))}
            aria-label="Día siguiente"
          >
            ›
          </button>
        </div>
        <div className={styles.navFechaExtra}>
          {!esHoy && (
            <button type="button" className={styles.btnHoy} onClick={() => onFechaChange(hoyStr)}>
              Hoy
            </button>
          )}
          <button
            type="button"
            className={styles.btnCal}
            onClick={() => setMostrarCalendario(v => !v)}
            aria-label={mostrarCalendario ? 'Cerrar calendario' : 'Abrir calendario'}
            aria-expanded={mostrarCalendario}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </button>
        </div>
      </div>

      {mostrarCalendario && (
        <div className={styles.calendarioWrap}>
          <Calendario
            diasAbiertos={new Set([0, 1, 2, 3, 4, 5, 6])}
            fechaSeleccionada={fechaADate(fecha)}
            onSeleccionar={handleSeleccionarFecha}
            permitirPasados
          />
        </div>
      )}

      {/* Lista de citas del día */}
      {cargando ? (
        <div className={styles.centrado}><Spinner size={24} /></div>
      ) : citas.length === 0 ? (
        <p className={styles.vacioDia}>No hay citas para este día.</p>
      ) : (
        <div className={styles.lista}>
          {citas.map(cita => {
            const cliente  = clientesMap[cita.cliente_id]
            const servicio = serviciosMap[cita.servicio_id]
            const { texto, clase } = derivarEtiqueta(cita)
            const pasada = esPasada(cita)
            const puedeNoAsistida = cita.estado === 'activa' && pasada
            const puedeCancelar   = cita.estado === 'activa' && !pasada
            const modalAbierto    = citaAccion?.cita.id === cita.id

            return (
              <article key={cita.id} className={styles.citaCard}>
                <div className={styles.citaHeader}>
                  <span className={styles.citaHora}>{cita.hora_inicio.slice(0, 5)}</span>
                  <span className={`${styles.etiqueta} ${styles[clase]}`}>{texto}</span>
                </div>

                <div className={styles.citaCliente}>
                  <span className={styles.citaNombre}>{cliente?.nombre_completo ?? '—'}</span>
                  {cliente?.telefono && (
                    <a
                      href={`tel:${cliente.telefono}`}
                      className={styles.citaTel}
                    >
                      {cliente.telefono}
                    </a>
                  )}
                </div>

                {servicio && (
                  <span className={styles.citaServicio}>{servicio.nombre}</span>
                )}

                {!modalAbierto && (puedeNoAsistida || puedeCancelar) && (
                  <div className={styles.citaAcciones}>
                    {puedeNoAsistida && (
                      <button
                        type="button"
                        className={styles.btnNoAsistio}
                        onClick={() => abrirAccion(cita, 'no-asistida')}
                      >
                        No asistió
                      </button>
                    )}
                    {puedeCancelar && (
                      <button
                        type="button"
                        className={styles.btnCancelar}
                        onClick={() => abrirAccion(cita, 'cancelar')}
                      >
                        Cancelar cita
                      </button>
                    )}
                  </div>
                )}

                {modalAbierto && (
                  <div
                    className={styles.modal}
                    role="dialog"
                    aria-modal="true"
                    aria-label={citaAccion.tipo === 'no-asistida' ? 'Confirmar no asistencia' : 'Confirmar cancelación'}
                  >
                    <p className={styles.modalTexto}>
                      {citaAccion.tipo === 'no-asistida'
                        ? '¿Marcar que el cliente no asistió? Esta acción no se puede deshacer.'
                        : '¿Cancelar esta cita? El hueco quedará libre en la agenda.'}
                    </p>
                    {errorAccion && (
                      <p className={styles.errorMsg} role="alert">{errorAccion}</p>
                    )}
                    <div className={styles.modalAcciones}>
                      <button
                        type="button"
                        className={citaAccion.tipo === 'no-asistida' ? styles.btnConfirmarAmbar : styles.btnConfirmarRojo}
                        disabled={procesando}
                        onClick={confirmarAccion}
                      >
                        {procesando ? 'Procesando…' : 'Confirmar'}
                      </button>
                      <button
                        type="button"
                        className={styles.btnVolver}
                        disabled={procesando}
                        onClick={cerrarAccion}
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
      )}
    </div>
  )
}
