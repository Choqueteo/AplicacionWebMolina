import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import client from '../api/client'
import AuthLayout from '../components/layout/AuthLayout'
import FormField from '../components/ui/FormField'
import Button from '../components/ui/Button'
import styles from './Registro.module.css'

export default function Registro() {
  const navigate = useNavigate()

  const [cargando, setCargando]                       = useState(false)
  const [erroresCampo, setErroresCampo]               = useState({})
  const [errorGeneral, setErrorGeneral]               = useState('')
  const [aceptaConsentimiento, setAceptaConsentimiento] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErroresCampo({})
    setErrorGeneral('')
    setCargando(true)

    const f = e.target.elements
    const nombreCompleto = `${f.nombre.value.trim()} ${f.apellidos.value.trim()}`.trim()

    try {
      await client.post('/registro', {
        nombre_completo:       nombreCompleto,
        telefono:              f.telefono.value,
        email:                 f.email.value,
        password:              f.password.value,
        acepta_consentimiento: true,
      })
      navigate('/login', {
        state: { mensaje: 'Cuenta creada, ya puedes iniciar sesión' },
      })
    } catch (err) {
      const status = err.response?.status
      const data   = err.response?.data

      if (status === 422) {
        const detail = data?.detail
        if (Array.isArray(detail)) {
          const campos = {}
          let tieneError = false
          for (const item of detail) {
            const campo = item.loc?.[1]
            if (campo === 'nombre_completo') {
              campos.apellidos = item.msg
              tieneError = true
            } else if (campo === 'telefono') {
              campos.telefono = item.msg
              tieneError = true
            } else if (campo === 'email') {
              campos.email = item.msg
              tieneError = true
            } else if (campo === 'acepta_consentimiento') {
              setErrorGeneral(item.msg || 'Debes aceptar la política de privacidad')
              tieneError = true
            }
          }
          setErroresCampo(campos)
          if (!tieneError) {
            setErrorGeneral('Datos inválidos, revisa el formulario')
          }
        } else {
          setErrorGeneral(typeof detail === 'string' ? detail : 'Datos inválidos, revisa el formulario')
        }
      } else if (status === 409 || err.isConflict) {
        setErroresCampo({ email: 'El email ya está registrado' })
      } else if (status === 429) {
        setErrorGeneral('Demasiados intentos, espera un momento')
      } else {
        setErrorGeneral('Error al registrarse, inténtalo de nuevo')
      }
    } finally {
      setCargando(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className={styles.titulo}>Crear cuenta</h1>

      <p className={styles.contexto}>
        Solo necesitamos unos datos para gestionar tus citas; no los usaremos para nada más.
      </p>

      <form onSubmit={handleSubmit} noValidate className={styles.form}>
        <FormField
          label="Nombre"
          name="nombre"
          autoComplete="given-name"
          ayuda="Pon tu nombre y apellidos reales: así el peluquero te identifica en su agenda."
          required
        />

        <FormField
          label="Apellidos"
          name="apellidos"
          autoComplete="family-name"
          error={erroresCampo.apellidos}
          required
        />

        <FormField
          label="Teléfono"
          name="telefono"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          ayuda="El peluquero lo usará para avisarte si hay algún cambio en tu cita."
          error={erroresCampo.telefono}
          required
        />

        <FormField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          ayuda="Será tu usuario para iniciar sesión. Usa un correo que consultes."
          error={erroresCampo.email}
          required
        />

        <FormField
          label="Contraseña"
          name="password"
          type="password"
          autoComplete="new-password"
          ayuda="La necesitarás para entrar y gestionar tus citas, así que elige una que recuerdes. Mínimo 8 caracteres."
          required
        />

        <div className={styles.consentimiento}>
          <label className={styles.checkLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={aceptaConsentimiento}
              onChange={e => setAceptaConsentimiento(e.target.checked)}
            />
            <span>
              He leído y acepto la{' '}
              <Link to="/politica-privacidad" target="_blank" rel="noopener">
                política de privacidad
              </Link>
              {' '}para el tratamiento de mis datos con el fin de gestionar mis citas.
            </span>
          </label>
        </div>

        {errorGeneral && (
          <p className={styles.errorMsg} role="alert">{errorGeneral}</p>
        )}

        <Button type="submit" loading={cargando} disabled={!aceptaConsentimiento || cargando}>
          Registrarse
        </Button>
      </form>

      <p className={styles.enlace}>
        ¿Ya tienes cuenta?{' '}
        <Link to="/login">Inicia sesión</Link>
      </p>
    </AuthLayout>
  )
}
