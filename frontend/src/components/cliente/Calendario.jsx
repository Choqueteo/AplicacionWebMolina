import { useState } from 'react'
import styles from './Calendario.module.css'

const DIAS_SEMANA = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

function mismosDia(a, b) {
  return a && b &&
    a.getFullYear() === b.getFullYear() &&
    a.getMonth()    === b.getMonth() &&
    a.getDate()     === b.getDate()
}

function esPasado(date, hoy) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  const h = new Date(hoy)
  h.setHours(0, 0, 0, 0)
  return d < h
}

// dia_semana del backend: 0=lunes … 6=domingo
// getDay() JS: 0=domingo, 1=lunes … 6=sábado
// Conversión: (getDay() + 6) % 7  → 0=lunes … 6=domingo
function diaSemanaISO(date) {
  return (date.getDay() + 6) % 7
}

function generarCeldas(año, mes) {
  const primerDia = new Date(año, mes, 1)
  const ultimoDia = new Date(año, mes + 1, 0)
  const offset = diaSemanaISO(primerDia) // celdas vacías al inicio

  const celdas = []
  for (let i = 0; i < offset; i++) celdas.push(null)
  for (let d = 1; d <= ultimoDia.getDate(); d++) {
    celdas.push(new Date(año, mes, d))
  }
  return celdas
}

export default function Calendario({ diasAbiertos, fechaSeleccionada, onSeleccionar }) {
  const hoy = new Date()
  const [vistaAño, setVistaAño]  = useState(hoy.getFullYear())
  const [vistaMes, setVistaMes]  = useState(hoy.getMonth())

  const irMesAnterior = () => {
    // No ir antes del mes actual
    if (vistaAño === hoy.getFullYear() && vistaMes === hoy.getMonth()) return
    if (vistaMes === 0) { setVistaAño(y => y - 1); setVistaMes(11) }
    else setVistaMes(m => m - 1)
  }

  const irMesSiguiente = () => {
    if (vistaMes === 11) { setVistaAño(y => y + 1); setVistaMes(0) }
    else setVistaMes(m => m + 1)
  }

  const tituloMes = new Intl.DateTimeFormat('es-ES', {
    month: 'long', year: 'numeric',
  }).format(new Date(vistaAño, vistaMes, 1))

  const celdas = generarCeldas(vistaAño, vistaMes)
  const esMesActual = vistaAño === hoy.getFullYear() && vistaMes === hoy.getMonth()

  const handleClick = (date) => {
    if (!date) return
    const pasado = esPasado(date, hoy)
    const cerrado = !diasAbiertos.has(diaSemanaISO(date))
    if (pasado || cerrado) return
    onSeleccionar(date)
  }

  const handleKeyDown = (e, date) => {
    if (!date) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick(date)
    }
  }

  return (
    <div className={styles.calendario} role="application" aria-label="Selector de fecha">
      {/* Navegación de mes */}
      <div className={styles.navMes}>
        <button
          type="button"
          className={styles.navBtn}
          onClick={irMesAnterior}
          disabled={esMesActual}
          aria-label="Mes anterior"
        >
          ‹
        </button>
        <span className={styles.tituloMes} style={{ textTransform: 'capitalize' }}>
          {tituloMes}
        </span>
        <button
          type="button"
          className={styles.navBtn}
          onClick={irMesSiguiente}
          aria-label="Mes siguiente"
        >
          ›
        </button>
      </div>

      {/* Cabecera días de semana */}
      <div className={styles.grid} role="grid">
        {DIAS_SEMANA.map(d => (
          <div key={d} className={styles.diaSemana} role="columnheader" aria-label={d}>
            {d}
          </div>
        ))}

        {/* Celdas */}
        {celdas.map((date, i) => {
          if (!date) {
            return <div key={`empty-${i}`} role="gridcell" aria-hidden="true" />
          }
          const pasado  = esPasado(date, hoy)
          const cerrado = !diasAbiertos.has(diaSemanaISO(date))
          const inactivo = pasado || cerrado
          const esHoy  = mismosDia(date, hoy)
          const selec  = mismosDia(date, fechaSeleccionada)

          return (
            <div
              key={date.toISOString()}
              role="gridcell"
              className={[
                styles.dia,
                inactivo   ? styles.inactivo   : styles.activo,
                esHoy      ? styles.hoy         : '',
                selec      ? styles.seleccionado : '',
              ].join(' ')}
              aria-disabled={inactivo ? 'true' : undefined}
              aria-selected={selec ? 'true' : undefined}
              aria-label={date.toLocaleDateString('es-ES', {
                weekday: 'long', day: 'numeric', month: 'long',
              })}
              tabIndex={inactivo ? -1 : 0}
              onClick={() => handleClick(date)}
              onKeyDown={e => handleKeyDown(e, date)}
            >
              {date.getDate()}
            </div>
          )
        })}
      </div>
    </div>
  )
}
