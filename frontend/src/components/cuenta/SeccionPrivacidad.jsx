import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import client from '../../api/client'
import styles from './SeccionPrivacidad.module.css'

export default function SeccionPrivacidad() {
  const { logout } = useAuth()
  const navigate   = useNavigate()

  const [descargando,  setDescargando]  = useState(false)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [confirmText,  setConfirmText]  = useState('')
  const [eliminando,   setEliminando]   = useState(false)
  const [error,        setError]        = useState('')

  const descargarDatos = async () => {
    setDescargando(true)
    setError('')
    try {
      const res  = await client.get('/usuarios/me/datos')
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = 'mis-datos-rm.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('No se pudo descargar los datos. Inténtalo de nuevo.')
    } finally {
      setDescargando(false)
    }
  }

  const abrirModal = () => {
    setConfirmText('')
    setError('')
    setModalAbierto(true)
  }

  const confirmarEliminar = async () => {
    setEliminando(true)
    setError('')
    try {
      await client.delete('/usuarios/me')
      logout()
      navigate('/login', { replace: true })
    } catch (err) {
      const s = err.response?.status
      if (s === 403) {
        setError('Las cuentas admin no pueden autoeliminarse.')
      } else if (s === 429) {
        setError('Demasiados intentos. Espera un momento e inténtalo de nuevo.')
      } else {
        setError('No se pudo eliminar la cuenta. Inténtalo de nuevo.')
      }
      setEliminando(false)
    }
  }

  return (
    <section className={styles.seccion}>
      <h2 className={styles.titulo}>Privacidad y datos</h2>
      <p className={styles.descripcion}>
        Gestiona tus datos personales conforme al RGPD. Puedes descargar una copia de tu
        información o eliminar permanentemente tu cuenta.
      </p>

      <div className={styles.acciones}>
        <div className={styles.accion}>
          <p className={styles.accionDesc}>
            Descarga todos tus datos personales en formato JSON: perfil e historial de citas.
          </p>
          <button
            type="button"
            className={styles.btnDescargar}
            onClick={descargarDatos}
            disabled={descargando}
          >
            {descargando ? 'Descargando…' : 'Descargar mis datos'}
          </button>
        </div>

        <div className={`${styles.accion} ${styles.accionPeligro}`}>
          <p className={styles.accionDesc}>
            Elimina tu cuenta de forma permanente. Tus datos personales serán anonimizados y
            no podrás recuperar el acceso.
          </p>
          <button
            type="button"
            className={styles.btnEliminar}
            onClick={abrirModal}
          >
            Eliminar mi cuenta
          </button>
        </div>
      </div>

      {!modalAbierto && error && (
        <p className={styles.msgError} role="alert">{error}</p>
      )}

      {modalAbierto && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="modal-titulo">
          <div className={styles.modal}>
            <h3 id="modal-titulo" className={styles.modalTitulo}>¿Eliminar cuenta?</h3>
            <p className={styles.modalAviso}>
              Esta acción es <strong>irreversible</strong>. Tus datos personales serán
              anonimizados, tus citas futuras canceladas y no podrás volver a acceder con
              estas credenciales.
            </p>
            <p className={styles.modalInstruccion}>
              Escribe <strong>ELIMINAR</strong> para confirmar:
            </p>
            <input
              type="text"
              className={styles.modalInput}
              value={confirmText}
              onChange={e => setConfirmText(e.target.value)}
              placeholder="ELIMINAR"
              autoComplete="off"
              spellCheck={false}
            />
            {error && (
              <p className={styles.msgError} role="alert">{error}</p>
            )}
            <div className={styles.modalBotones}>
              <button
                type="button"
                className={styles.btnCancelarModal}
                onClick={() => setModalAbierto(false)}
                disabled={eliminando}
              >
                Cancelar
              </button>
              <button
                type="button"
                className={styles.btnConfirmar}
                onClick={confirmarEliminar}
                disabled={confirmText !== 'ELIMINAR' || eliminando}
              >
                {eliminando ? 'Eliminando…' : 'Confirmar eliminación'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
