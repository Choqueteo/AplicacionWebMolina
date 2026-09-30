import { useEffect, useState } from 'react'
import client from '../../api/client'
import { capitalizar } from '../../utils/texto'
import Spinner from '../ui/Spinner'
import styles from './TabHorario.module.css'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

function _fechaHoy() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function _formatFechaCierre(isoStr) {
  const [y, m, d] = isoStr.split('-')
  return new Date(Number(y), Number(m) - 1, Number(d))
    .toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

export default function TabHorario() {
  const [horario,         setHorario]         = useState([])
  const [cargando,        setCargando]        = useState(true)
  const [errorCarga,      setErrorCarga]      = useState('')
  const [formAbierto,     setFormAbierto]     = useState(null) // { dia, id: null|number }
  const [confirmarBorrar, setConfirmarBorrar] = useState(null) // tramo id
  const [procesando,      setProcesando]      = useState(false)
  const [errorAccion,     setErrorAccion]     = useState('')

  // Días cerrados
  const [cerrados,        setCerrados]        = useState([])
  const [fechaNuevoCierre, setFechaNuevoCierre] = useState('')
  const [errorCerrar,     setErrorCerrar]     = useState('')
  const [procesandoCerrar, setProcesandoCerrar] = useState(false)

  const cargar = () => {
    setCargando(true)
    client.get('/horario')
      .then(r => setHorario(r.data))
      .catch(() => setErrorCarga('Error al cargar el horario. Recarga la página.'))
      .finally(() => setCargando(false))
  }

  const cargarCerrados = () => {
    client.get('/excepciones')
      .then(r => setCerrados(r.data))
      .catch(() => {})
  }

  useEffect(() => { cargar() }, [])
  useEffect(() => { cargarCerrados() }, [])

  const handleCerrarDia = async () => {
    if (!fechaNuevoCierre) return
    setProcesandoCerrar(true)
    setErrorCerrar('')
    try {
      await client.post('/excepciones', { fecha: fechaNuevoCierre })
      setFechaNuevoCierre('')
      cargarCerrados()
    } catch (err) {
      const detail = err.response?.data?.detail
      setErrorCerrar(typeof detail === 'string' ? detail : 'Error al cerrar el día. Inténtalo de nuevo.')
    } finally {
      setProcesandoCerrar(false)
    }
  }

  const handleQuitarCierre = async (id) => {
    setProcesandoCerrar(true)
    setErrorCerrar('')
    try {
      await client.delete(`/excepciones/${id}`)
      cargarCerrados()
    } catch (err) {
      const detail = err.response?.data?.detail
      setErrorCerrar(typeof detail === 'string' ? detail : 'Error al quitar el cierre. Inténtalo de nuevo.')
    } finally {
      setProcesandoCerrar(false)
    }
  }

  // Agrupación: dia_semana → tramos ordenados por hora_apertura
  const tramosPorDia = {}
  horario.forEach(t => {
    if (!tramosPorDia[t.dia_semana]) tramosPorDia[t.dia_semana] = []
    tramosPorDia[t.dia_semana].push(t)
  })

  const abrirForm = (dia, id = null) => {
    setFormAbierto({ dia, id })
    setErrorAccion('')
  }

  const cerrarForm = () => {
    setFormAbierto(null)
    setErrorAccion('')
  }

  const handleGuardar = async (datos) => {
    if (!formAbierto) return
    setProcesando(true)
    setErrorAccion('')
    const { dia, id } = formAbierto
    try {
      if (id !== null) {
        await client.put(`/horario/${id}`, datos)
      } else {
        await client.post('/horario', { dia_semana: dia, ...datos })
      }
      cerrarForm()
      cargar()
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 409) {
        setErrorAccion(typeof detail === 'string' ? detail : 'El tramo se solapa con uno existente ese día.')
      } else if (status === 422) {
        setErrorAccion(typeof detail === 'string' ? detail : 'Horario inválido (cierre debe ser posterior a apertura).')
      } else {
        setErrorAccion('Error al guardar. Inténtalo de nuevo.')
      }
    } finally {
      setProcesando(false)
    }
  }

  const handleBorrar = async (id) => {
    setProcesando(true)
    setErrorAccion('')
    try {
      await client.delete(`/horario/${id}`)
      setConfirmarBorrar(null)
      cargar()
    } catch {
      setErrorAccion('Error al eliminar el tramo. Inténtalo de nuevo.')
    } finally {
      setProcesando(false)
    }
  }

  if (cargando) {
    return <div className={styles.centrado}><Spinner size={24} /></div>
  }

  if (errorCarga) {
    return <p className={styles.errorGlobal} role="alert">{errorCarga}</p>
  }

  return (
    <div className={styles.lista}>
      {errorAccion && (
        <p className={styles.errorGlobal} role="alert">{errorAccion}</p>
      )}

      {/* ── Días cerrados ────────────────────────────────────────────────── */}
      <section className={styles.seccionCerrados}>
        <h3 className={styles.tituloCerrados}>Días cerrados</h3>

        {errorCerrar && (
          <p className={styles.errorGlobal} role="alert">{errorCerrar}</p>
        )}

        <div className={styles.formCerrar}>
          <input
            type="date"
            className={styles.inputFecha}
            value={fechaNuevoCierre}
            min={_fechaHoy()}
            onChange={e => { setFechaNuevoCierre(e.target.value); setErrorCerrar('') }}
            aria-label="Fecha a cerrar"
          />
          <button
            type="button"
            className={styles.btnGuardar}
            disabled={!fechaNuevoCierre || procesandoCerrar}
            onClick={handleCerrarDia}
          >
            {procesandoCerrar ? 'Guardando…' : 'Cerrar día'}
          </button>
        </div>

        {cerrados.length > 0 && (
          <ul className={styles.listaCerrados}>
            {cerrados.map(exc => (
              <li key={exc.id} className={styles.itemCerrado}>
                <span className={styles.fechaTexto}>
                  {capitalizar(_formatFechaCierre(exc.fecha))}
                </span>
                <button
                  type="button"
                  className={styles.btnQuitar}
                  disabled={procesandoCerrar}
                  onClick={() => handleQuitarCierre(exc.id)}
                >
                  Quitar
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {DIAS.map((nombre, dia) => {
        const tramos = tramosPorDia[dia] ?? []
        const formEstesDia = formAbierto?.dia === dia

        return (
          <article key={dia} className={styles.diaCard}>
            <div className={styles.diaHeader}>
              <span className={styles.diaNombre}>{nombre}</span>
              {tramos.length === 0 && !formEstesDia && (
                <span className={styles.diaCerrado}>Cerrado</span>
              )}
            </div>

            {/* Lista de tramos existentes */}
            {tramos.length > 0 && (
              <div className={styles.listaTramos}>
                {tramos.map(tramo => {
                  const editandoEste  = formAbierto?.id === tramo.id
                  const borrandoEste  = confirmarBorrar === tramo.id

                  return (
                    <div key={tramo.id} className={styles.tramoItem}>
                      {!editandoEste && !borrandoEste && (
                        <div className={styles.tramoRow}>
                          <span className={styles.tramoHoras}>
                            {tramo.hora_apertura.slice(0, 5)} – {tramo.hora_cierre.slice(0, 5)}
                          </span>
                          <div className={styles.tramoBotones}>
                            <button
                              type="button"
                              className={styles.btnAccion}
                              onClick={() => abrirForm(dia, tramo.id)}
                              disabled={!!formAbierto || !!confirmarBorrar}
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              className={styles.btnEliminar}
                              onClick={() => { setConfirmarBorrar(tramo.id); setErrorAccion('') }}
                              disabled={!!formAbierto || !!confirmarBorrar}
                            >
                              Eliminar
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Formulario de edición inline para este tramo */}
                      {editandoEste && (
                        <FormHorario
                          apertura={tramo.hora_apertura.slice(0, 5)}
                          cierre={tramo.hora_cierre.slice(0, 5)}
                          procesando={procesando}
                          onGuardar={handleGuardar}
                          onCancelar={cerrarForm}
                        />
                      )}

                      {/* Confirmación de borrado inline */}
                      {borrandoEste && (
                        <div className={styles.confirmar}>
                          <p className={styles.confirmarTexto}>
                            ¿Eliminar el tramo {tramo.hora_apertura.slice(0, 5)}–{tramo.hora_cierre.slice(0, 5)}?
                          </p>
                          <div className={styles.confirmarAcciones}>
                            <button
                              type="button"
                              className={styles.btnConfirmarRojo}
                              disabled={procesando}
                              onClick={() => handleBorrar(tramo.id)}
                            >
                              {procesando ? 'Eliminando…' : 'Eliminar'}
                            </button>
                            <button
                              type="button"
                              className={styles.btnVolver}
                              disabled={procesando}
                              onClick={() => setConfirmarBorrar(null)}
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Formulario de nuevo tramo */}
            {formAbierto?.dia === dia && formAbierto?.id === null && (
              <FormHorario
                apertura="09:00"
                cierre="18:00"
                procesando={procesando}
                onGuardar={handleGuardar}
                onCancelar={cerrarForm}
              />
            )}

            {/* Botón añadir tramo — siempre visible si no hay form abierto en este día */}
            {!formEstesDia && !confirmarBorrar && (
              <button
                type="button"
                className={styles.btnAnadir}
                onClick={() => abrirForm(dia, null)}
                disabled={!!formAbierto}
              >
                + Añadir tramo
              </button>
            )}
          </article>
        )
      })}
    </div>
  )
}

function FormHorario({ apertura, cierre, procesando, onGuardar, onCancelar }) {
  const [horaApertura, setHoraApertura] = useState(apertura)
  const [horaCierre,   setHoraCierre]   = useState(cierre)

  const handleSubmit = (e) => {
    e.preventDefault()
    onGuardar({ hora_apertura: horaApertura, hora_cierre: horaCierre })
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <div className={styles.formFila}>
        <div className={styles.campo}>
          <label className={styles.label}>Apertura</label>
          <input
            type="time"
            className={styles.inputTime}
            value={horaApertura}
            onChange={e => setHoraApertura(e.target.value)}
            required
          />
        </div>
        <div className={styles.campo}>
          <label className={styles.label}>Cierre</label>
          <input
            type="time"
            className={styles.inputTime}
            value={horaCierre}
            onChange={e => setHoraCierre(e.target.value)}
            required
          />
        </div>
      </div>
      <div className={styles.formAcciones}>
        <button type="submit" className={styles.btnGuardar} disabled={procesando}>
          {procesando ? 'Guardando…' : 'Guardar'}
        </button>
        <button type="button" className={styles.btnVolver} disabled={procesando} onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
