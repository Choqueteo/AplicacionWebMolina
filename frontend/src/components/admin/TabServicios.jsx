import { useEffect, useState } from 'react'
import client from '../../api/client'
import Spinner from '../ui/Spinner'
import styles from './TabServicios.module.css'

const DURACIONES = [30, 60, 90, 120]

function formatDuracion(min) {
  if (min < 60) return `${min} min`
  if (min % 60 === 0) return `${min / 60} h`
  return `${Math.floor(min / 60)} h ${min % 60} min`
}

function formatPrecio(precio) {
  return Number(precio).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

function extraerError422(err) {
  const detail = err.response?.data?.detail
  if (!Array.isArray(detail)) return {}
  const mapa = {}
  for (const item of detail) {
    const campo = item.loc?.[1]
    if (campo) mapa[campo] = item.msg
  }
  return mapa
}

function FormServicio({ inicial, onGuardar, onCancelar }) {
  const [nombre,    setNombre]    = useState(inicial?.nombre           ?? '')
  const [duracion,  setDuracion]  = useState(inicial?.duracion_minutos ?? 30)
  const [precio,    setPrecio]    = useState(inicial?.precio           ?? '')
  const [errores,   setErrores]   = useState({})
  const [guardando, setGuardando] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrores({})
    setGuardando(true)
    try {
      await onGuardar({ nombre, duracion_minutos: Number(duracion), precio })
    } catch (err) {
      if (err.response?.status === 422) {
        setErrores(extraerError422(err))
      } else {
        setErrores({ _global: 'Error al guardar. Inténtalo de nuevo.' })
      }
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <div className={styles.campo}>
        <label className={styles.label} htmlFor={`nombre-${inicial?.id ?? 'nuevo'}`}>Nombre</label>
        <input
          id={`nombre-${inicial?.id ?? 'nuevo'}`}
          className={`${styles.input} ${errores.nombre ? styles.inputError : ''}`}
          type="text"
          value={nombre}
          onChange={e => setNombre(e.target.value)}
          required
          maxLength={100}
        />
        {errores.nombre && <span className={styles.errorCampo}>{errores.nombre}</span>}
      </div>

      <div className={styles.campo}>
        <label className={styles.label} htmlFor={`dur-${inicial?.id ?? 'nuevo'}`}>Duración</label>
        <select
          id={`dur-${inicial?.id ?? 'nuevo'}`}
          className={styles.input}
          value={duracion}
          onChange={e => setDuracion(e.target.value)}
        >
          {DURACIONES.map(d => (
            <option key={d} value={d}>{formatDuracion(d)}</option>
          ))}
        </select>
      </div>

      <div className={styles.campo}>
        <label className={styles.label} htmlFor={`precio-${inicial?.id ?? 'nuevo'}`}>Precio (€)</label>
        <input
          id={`precio-${inicial?.id ?? 'nuevo'}`}
          className={`${styles.input} ${errores.precio ? styles.inputError : ''}`}
          type="number"
          min="0"
          step="0.01"
          value={precio}
          onChange={e => setPrecio(e.target.value)}
          required
        />
        {errores.precio && <span className={styles.errorCampo}>{errores.precio}</span>}
      </div>

      {errores._global && (
        <p className={styles.errorGlobal} role="alert">{errores._global}</p>
      )}

      <div className={styles.formAcciones}>
        <button type="submit" className={styles.btnGuardar} disabled={guardando}>
          {guardando ? 'Guardando…' : (inicial ? 'Guardar cambios' : 'Crear servicio')}
        </button>
        {onCancelar && (
          <button type="button" className={styles.btnCancelarForm} disabled={guardando} onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}

export default function TabServicios() {
  const [servicios, setServicios]   = useState([])
  const [cargando, setCargando]     = useState(true)
  const [errorCarga, setErrorCarga] = useState('')
  const [editandoId, setEditandoId] = useState(null)  // id del servicio con form inline abierto

  const cargar = () => {
    setCargando(true)
    client.get('/servicios', { params: { incluir_inactivos: true } })
      .then(r => setServicios(r.data))
      .catch(() => setErrorCarga('Error al cargar servicios. Recarga la página.'))
      .finally(() => setCargando(false))
  }

  useEffect(() => { cargar() }, [])

  const handleCrear = async (datos) => {
    await client.post('/servicios', datos)
    cargar()
  }

  const handleEditar = async (id, datos) => {
    await client.put(`/servicios/${id}`, datos)
    setEditandoId(null)
    cargar()
  }

  const handleDesactivar = async (id) => {
    await client.delete(`/servicios/${id}`)
    cargar()
  }

  const handleReactivar = async (id) => {
    await client.put(`/servicios/${id}`, { activo: true })
    cargar()
  }

  if (cargando) {
    return <div className={styles.centrado}><Spinner size={24} /></div>
  }

  if (errorCarga) {
    return <p className={styles.errorGlobal} role="alert">{errorCarga}</p>
  }

  return (
    <div className={styles.contenedor}>
      {/* Lista de servicios */}
      {servicios.length > 0 && (
        <div className={styles.lista}>
          {servicios.map(s => (
            <article key={s.id} className={`${styles.card} ${!s.activo ? styles.cardInactiva : ''}`}>
              <div className={styles.cardHeader}>
                <div className={styles.cardInfo}>
                  <span className={styles.cardNombre}>{s.nombre}</span>
                  <span className={styles.cardMeta}>
                    {formatDuracion(s.duracion_minutos)} · {formatPrecio(s.precio)}
                  </span>
                </div>
                <span className={`${styles.badge} ${s.activo ? styles.badgeActivo : styles.badgeInactivo}`}>
                  {s.activo ? 'Activo' : 'Inactivo'}
                </span>
              </div>

              {editandoId === s.id ? (
                <FormServicio
                  inicial={s}
                  onGuardar={(datos) => handleEditar(s.id, datos)}
                  onCancelar={() => setEditandoId(null)}
                />
              ) : (
                <div className={styles.cardAcciones}>
                  <button
                    type="button"
                    className={styles.btnEditar}
                    onClick={() => setEditandoId(s.id)}
                  >
                    Editar
                  </button>
                  {s.activo ? (
                    <button
                      type="button"
                      className={styles.btnDesactivar}
                      onClick={() => handleDesactivar(s.id)}
                    >
                      Desactivar
                    </button>
                  ) : (
                    <button
                      type="button"
                      className={styles.btnReactivar}
                      onClick={() => handleReactivar(s.id)}
                    >
                      Reactivar
                    </button>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      {/* Formulario de creación */}
      <section className={styles.seccionCrear}>
        <h2 className={styles.seccionTitulo}>Nuevo servicio</h2>
        <FormServicio onGuardar={handleCrear} />
      </section>
    </div>
  )
}
