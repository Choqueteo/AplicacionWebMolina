import { useState } from 'react'
import FormField from '../ui/FormField'
import Button from '../ui/Button'
import client from '../../api/client'
import styles from './FormularioPassword.module.css'

export default function FormularioPassword() {
  const [passwordActual,  setPasswordActual]  = useState('')
  const [passwordNueva,   setPasswordNueva]   = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [errores,      setErrores]      = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [exito,        setExito]        = useState(false)
  const [guardando,    setGuardando]    = useState(false)
  const [mostrarActual, setMostrarActual] = useState(false)
  const [mostrarNueva,  setMostrarNueva]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrores({})
    setErrorGeneral('')
    setExito(false)

    if (passwordNueva !== passwordConfirm) {
      setErrores({ passwordConfirm: 'Las contraseñas nuevas no coinciden' })
      return
    }

    setGuardando(true)
    try {
      await client.patch('/usuarios/me/password', {
        password_actual: passwordActual,
        password_nueva:  passwordNueva,
      })
      setExito(true)
      setPasswordActual('')
      setPasswordNueva('')
      setPasswordConfirm('')
      setMostrarActual(false)
      setMostrarNueva(false)
    } catch (err) {
      const status = err.response?.status
      const data   = err.response?.data
      if (status === 400) {
        setErrores({ passwordActual: data?.detail ?? 'La contraseña actual no es correcta' })
      } else if (status === 422 && Array.isArray(data?.detail)) {
        const campos = {}
        for (const item of data.detail) {
          const campo = item.loc?.[1]
          if (campo === 'password_nueva') campos.passwordNueva = item.msg
          else                            setErrorGeneral(item.msg)
        }
        setErrores(campos)
      } else if (status === 429) {
        setErrorGeneral('Demasiados intentos, espera un momento')
      } else {
        setErrorGeneral('Error al cambiar la contraseña, inténtalo de nuevo')
      }
    } finally {
      setGuardando(false)
    }
  }

  const SvgOjo = ({ visible }) => visible ? (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  )

  return (
    <section className={styles.seccion}>
      <h2 className={styles.titulo}>Cambiar contraseña</h2>
      <form onSubmit={handleSubmit} noValidate className={styles.form}>
        <FormField
          label="Contraseña actual"
          name="passwordActual"
          type={mostrarActual ? 'text' : 'password'}
          value={passwordActual}
          onChange={(e) => setPasswordActual(e.target.value)}
          error={errores.passwordActual}
          required
          suffix={
            <button
              type="button"
              onClick={() => setMostrarActual(v => !v)}
              aria-label={mostrarActual ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              <SvgOjo visible={mostrarActual} />
            </button>
          }
        />
        <FormField
          label="Contraseña nueva"
          name="passwordNueva"
          type={mostrarNueva ? 'text' : 'password'}
          value={passwordNueva}
          onChange={(e) => setPasswordNueva(e.target.value)}
          error={errores.passwordNueva}
          ayuda="Mínimo 8 caracteres"
          required
          suffix={
            <button
              type="button"
              onClick={() => setMostrarNueva(v => !v)}
              aria-label={mostrarNueva ? 'Ocultar contraseña nueva' : 'Mostrar contraseña nueva'}
            >
              <SvgOjo visible={mostrarNueva} />
            </button>
          }
        />
        <FormField
          label="Repetir contraseña nueva"
          name="passwordConfirm"
          type="password"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          error={errores.passwordConfirm}
          required
        />
        {errorGeneral && (
          <p className={styles.msgError} role="alert">{errorGeneral}</p>
        )}
        {exito && (
          <p className={styles.msgExito} role="status">Contraseña cambiada correctamente.</p>
        )}
        <Button type="submit" loading={guardando}>Cambiar contraseña</Button>
      </form>
    </section>
  )
}
