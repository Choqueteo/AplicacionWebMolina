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

function esFuturaExcedida(date, hoy, diasMax = 30) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  const limite = new Date(hoy)
  limite.setHours(0, 0, 0, 0)
  limite.setDate(limite.getDate() + diasMax)
  return d > limite
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

function fechaISO(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default function Calendario({ diasAbiertos, fechasCerradas = new Set(), fechaSeleccionada, onSeleccionar, permitirPasados = false }) {
  const _now = new Date()
  const hoy  = new Date(_now.getFullYear(), _now.getMonth(), _now.getDate())
  const initDate = (permitirPasados && fechaSeleccionada) ? fechaSeleccionada : hoy
  const [vistaAño, setVistaAño]  = useState(initDate.getFullYear())
  const [vistaMes, setVistaMes]  = useState(initDate.getMonth())

  const irMesAnterior = () => {
    if (!permitirPasados && vistaAño === hoy.getFullYear() && vistaMes === hoy.getMonth()) return
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
    const futuraExcedida = esFuturaExcedida(date, hoy)
    const diaCerrado = fechasCerradas.has(fechaISO(date))
    if ((!permitirPasados && pasado) || cerrado || futuraExcedida || diaCerrado) return
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
          disabled={!permitirPasados && esMesActual}
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
          const futuraExcedida = esFuturaExcedida(date, hoy)
          const diaCerrado = fechasCerradas.has(fechaISO(date))
          const inactivo = (!permitirPasados && pasado) || cerrado || futuraExcedida || diaCerrado
          const esHoy  = mismosDia(date, hoy)
          const selec  = mismosDia(date, fechaSeleccionada)

          return (
            <div
              key={`${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`}
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
