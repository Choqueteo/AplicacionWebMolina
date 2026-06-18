import { useEffect, useState } from 'react'
import client from '../../api/client'
import Spinner from '../ui/Spinner'
import styles from './TabClientes.module.css'

export default function TabClientes() {
  const [clientes,    setClientes]    = useState([])
  const [cargando,    setCargando]    = useState(true)
  const [errorCarga,  setErrorCarga]  = useState('')
  const [confirmar,   setConfirmar]   = useState(null)  // { id, accion: 'bloquear'|'desbloquear' }
  const [procesando,  setProcesando]  = useState(false)
  const [errorAccion, setErrorAccion] = useState('')

  useEffect(() => {
    client.get('/usuarios')
      .then(r => setClientes(r.data.filter(u => u.rol === 'cliente')))
      .catch(() => setErrorCarga('Error al cargar clientes. Recarga la página.'))
      .finally(() => setCargando(false))
  }, [])

  const abrirConfirmar = (id, accion) => {
    setErrorAccion('')
    setConfirmar({ id, accion })
  }

  const handleAccion = async () => {
    if (!confirmar) return
    setProcesando(true)
    setErrorAccion('')
    const { id, accion } = confirmar
    try {
      const r = await client.patch(`/usuarios/${id}/${accion}`)
      setClientes(prev => prev.map(c => c.id === id ? { ...c, bloqueado: r.data.bloqueado } : c))
      setConfirmar(null)
    } catch {
      setErrorAccion('Error al procesar la acción. Inténtalo de nuevo.')
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

  if (clientes.length === 0) {
    return <p className={styles.vacio}>Aún no hay clientes registrados.</p>
  }

  return (
    <div className={styles.lista}>
      {errorAccion && (
        <p className={styles.errorGlobal} role="alert">{errorAccion}</p>
      )}

      {clientes.map(c => {
        const modalAbierto = confirmar?.id === c.id

        return (
          <article key={c.id} className={`${styles.card} ${c.bloqueado ? styles.cardBloqueada : ''}`}>
            <div className={styles.cardHeader}>
              <span className={styles.cardNombre}>{c.nombre_completo}</span>
              <div className={styles.badges}>
                {c.inasistencias > 0 && (
                  <span className={styles.badgeInasistencias} title="Inasistencias">
                    {c.inasistencias} ✗
                  </span>
                )}
                <span className={`${styles.badge} ${c.bloqueado ? styles.badgeBloqueado : styles.badgeActivo}`}>
                  {c.bloqueado ? 'Bloqueado' : 'Activo'}
                </span>
              </div>
            </div>

            <div className={styles.cardMeta}>
              <a href={`tel:${c.telefono}`} className={styles.tel}>{c.telefono}</a>
              <span className={styles.sep}>·</span>
              <span className={styles.email}>{c.email}</span>
            </div>

            {!modalAbierto && (
              <div className={styles.cardAcciones}>
                {c.bloqueado ? (
                  <button
                    type="button"
                    className={styles.btnDesbloquear}
                    onClick={() => abrirConfirmar(c.id, 'desbloquear')}
                  >
                    Desbloquear
                  </button>
                ) : (
                  <button
                    type="button"
                    className={styles.btnBloquear}
                    onClick={() => abrirConfirmar(c.id, 'bloquear')}
                  >
                    Bloquear
                  </button>
                )}
              </div>
            )}

            {modalAbierto && (
              <div
                className={styles.modal}
                role="dialog"
                aria-modal="true"
                aria-label={confirmar.accion === 'bloquear' ? 'Confirmar bloqueo' : 'Confirmar desbloqueo'}
              >
                <p className={styles.modalTexto}>
                  {confirmar.accion === 'bloquear'
                    ? `¿Bloquear a ${c.nombre_completo}? No podrá hacer nuevas reservas.`
                    : `¿Desbloquear a ${c.nombre_completo}? Podrá volver a reservar.`}
                </p>
                <div className={styles.modalAcciones}>
                  <button
                    type="button"
                    className={confirmar.accion === 'bloquear' ? styles.btnConfirmarRojo : styles.btnConfirmarVerde}
                    disabled={procesando}
                    onClick={handleAccion}
                  >
                    {procesando ? 'Procesando…' : 'Confirmar'}
                  </button>
                  <button
                    type="button"
                    className={styles.btnVolver}
                    disabled={procesando}
                    onClick={() => setConfirmar(null)}
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
