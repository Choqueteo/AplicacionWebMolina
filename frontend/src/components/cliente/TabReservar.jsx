import { useEffect, useState } from 'react'
import client from '../../api/client'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import { capitalizar } from '../../utils/texto'
import Calendario from './Calendario'
import styles from './TabReservar.module.css'

function formatDuracion(minutos) {
  if (minutos >= 60 && minutos % 60 === 0) return `${minutos / 60} h`
  if (minutos >= 60) return `${Math.floor(minutos / 60)} h ${minutos % 60} min`
  return `${minutos} min`
}

function formatPrecio(precio) {
  return `${parseFloat(precio).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} €`
}

function formatFechaLarga(date) {
  return date.toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

function fechaAString(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default function TabReservar({ servicios, diasAbiertos, fechasCerradas = new Set(), onVerMisCitas }) {
  const [servicio, setServicio]     = useState(null)
  const [fecha, setFecha]           = useState(null)
  const [hora, setHora]             = useState(null)
  const [horas, setHoras]           = useState([])
  const [cargandoHoras, setCargandoHoras] = useState(false)
  const [confirmado, setConfirmado] = useState(false)
  const [cargandoPost, setCargandoPost] = useState(false)
  const [errorReserva, setErrorReserva] = useState('')

  // Al cambiar servicio o fecha, cargar disponibilidad
  useEffect(() => {
    if (!servicio || !fecha) return
    setHora(null)
    setHoras([])
    setErrorReserva('')
    setCargandoHoras(true)
    client
      .get('/disponibilidad', {
        params: { fecha: fechaAString(fecha), servicio_id: servicio.id },
      })
      .then(r => setHoras(r.data.horas_disponibles))
      .catch(() => setHoras([]))
      .finally(() => setCargandoHoras(false))
  }, [servicio, fecha])

  const handleServicio = (s) => {
    setServicio(s)
    setFecha(null)
    setHora(null)
    setHoras([])
    setConfirmado(false)
    setErrorReserva('')
  }

  const handleFecha = (d) => {
    setFecha(d)
    setHora(null)
    setErrorReserva('')
  }

  const recargarDisponibilidad = () => {
    if (!servicio || !fecha) return
    setHora(null)
    setCargandoHoras(true)
    client
      .get('/disponibilidad', {
        params: { fecha: fechaAString(fecha), servicio_id: servicio.id },
      })
      .then(r => setHoras(r.data.horas_disponibles))
      .catch(() => setHoras([]))
      .finally(() => setCargandoHoras(false))
  }

  const handleConfirmar = async () => {
    if (!servicio || !fecha || !hora) return
    setErrorReserva('')
    setCargandoPost(true)
    try {
      await client.post('/citas', {
        servicio_id: servicio.id,
        fecha: fechaAString(fecha),
        hora_inicio: hora,
      })
      setConfirmado(true)
    } catch (err) {
      const status = err.response?.status
      if (err.isConflict || status === 409) {
        setErrorReserva('Ese hueco acaba de ocuparse. Las horas se han actualizado.')
        recargarDisponibilidad()
      } else if (status === 403) {
        setErrorReserva(
          'No puedes hacer reservas ahora. Contacta con el peluquero para más información.'
        )
      } else {
        const detail = err.response?.data?.detail
        setErrorReserva(
          typeof detail === 'string' ? detail : 'No se pudo crear la reserva. Inténtalo de nuevo.'
        )
      }
    } finally {
      setCargandoPost(false)
    }
  }

  const handleNuevaReserva = () => {
    setServicio(null)
    setFecha(null)
    setHora(null)
    setHoras([])
    setConfirmado(false)
    setErrorReserva('')
  }

  // ── Éxito ──────────────────────────────────────────────────────────────────
  if (confirmado) {
    return (
      <div className={styles.exito}>
        <p className={styles.exitoIcono}>✓</p>
        <h2>¡Reserva confirmada!</h2>
        <p className={styles.exitoDetalle}>
          <strong>{servicio.nombre}</strong> — {formatFechaLarga(fecha)} a las {hora.slice(0, 5)}
        </p>
        <div className={styles.exitoAcciones}>
          <Button onClick={onVerMisCitas}>Ver mis citas</Button>
          <Button variant="ghost" onClick={handleNuevaReserva}>
            Hacer otra reserva
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.flujo}>
      {/* ── Sección 1: elegir servicio ───────────────────────────────────── */}
      <section className={styles.seccion}>
        <h2 className={styles.seccionTitulo}>Elige un servicio</h2>
        <div className={styles.serviciosGrid}>
          {servicios.map(s => (
            <button
              key={s.id}
              type="button"
              className={`${styles.servicioCard} ${servicio?.id === s.id ? styles.servicioSeleccionado : ''}`}
              onClick={() => handleServicio(s)}
            >
              <span className={styles.servicioNombre}>{s.nombre}</span>
              <span className={styles.servicioMeta}>
                {formatDuracion(s.duracion_minutos)} · {formatPrecio(s.precio)}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* ── Sección 2: elegir fecha ─────────────────────────────────────── */}
      {servicio && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Elige un día</h2>
          <Calendario
            diasAbiertos={diasAbiertos}
            fechasCerradas={fechasCerradas}
            fechaSeleccionada={fecha}
            onSeleccionar={handleFecha}
          />
        </section>
      )}

      {/* ── Sección 3: elegir hora ──────────────────────────────────────── */}
      {servicio && fecha && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Elige una hora</h2>
          {cargandoHoras ? (
            <div className={styles.centrado}><Spinner size={22} /></div>
          ) : horas.length === 0 ? (
            <p className={styles.vacio}>No hay horas disponibles para ese día.</p>
          ) : (
            <div className={styles.horasGrid}>
              {horas.map(h => (
                <button
                  key={h}
                  type="button"
                  className={`${styles.horaBtn} ${hora === h ? styles.horaSeleccionada : ''}`}
                  onClick={() => { setHora(h); setErrorReserva('') }}
                >
                  {h.slice(0, 5)}
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Sección 4: resumen y confirmar ──────────────────────────────── */}
      {servicio && fecha && hora && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Confirma tu reserva</h2>
          <div className={styles.resumen}>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Servicio</span>
              <span>{servicio.nombre}</span>
            </div>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Día</span>
              <span>{capitalizar(formatFechaLarga(fecha))}</span>
            </div>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Hora</span>
              <span>{hora.slice(0, 5)}</span>
            </div>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Duración</span>
              <span>{formatDuracion(servicio.duracion_minutos)}</span>
            </div>
          </div>
          {errorReserva && (
            <p className={styles.errorMsg} role="alert">{errorReserva}</p>
          )}
          <Button
            type="button"
            loading={cargandoPost}
            onClick={handleConfirmar}
          >
            Confirmar reserva
          </Button>
        </section>
      )}
    </div>
  )
}
