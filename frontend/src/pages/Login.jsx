import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AuthLayout from '../components/layout/AuthLayout'
import FormField from '../components/ui/FormField'
import Button from '../components/ui/Button'
import styles from './Login.module.css'

export default function Login() {
  const { login } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()

  const [cargando, setCargando]     = useState(false)
  const [error, setError]           = useState('')
  const [mostrarPass, setMostrarPass] = useState(false)

  const mensajeExito = location.state?.mensaje ?? ''

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setCargando(true)

    const f = e.target.elements
    try {
      const usuario = await login({
        email:    f.email.value,
        password: f.password.value,
      })
      navigate(usuario.rol === 'admin' ? '/admin' : '/dashboard', { replace: true })
    } catch (err) {
      const status = err.response?.status
      if (status === 401) {
        setError('Email o contraseña incorrectos')
      } else if (status === 429) {
        setError('Demasiados intentos, espera un momento')
      } else if (status >= 500) {
        setError('Error en el servidor, inténtalo más tarde')
      } else {
        setError('Error al iniciar sesión, inténtalo de nuevo')
      }
    } finally {
      setCargando(false)
    }
  }

  const togglePass = () => setMostrarPass(v => !v)

  return (
    <AuthLayout>
      {mensajeExito && (
        <p className={styles.successMsg} role="status">{mensajeExito}</p>
      )}

      <h1 className={styles.titulo}>Iniciar sesión</h1>

      <form onSubmit={handleSubmit} noValidate className={styles.form}>
        <FormField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
        />

        <FormField
          label="Contraseña"
          name="password"
          type={mostrarPass ? 'text' : 'password'}
          autoComplete="current-password"
          required
          suffix={
            <button
              type="button"
              onClick={togglePass}
              aria-label={mostrarPass ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              {mostrarPass ? (
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
              )}
            </button>
          }
        />

        {error && (
          <p className={styles.errorMsg} role="alert">{error}</p>
        )}

        <Button type="submit" loading={cargando}>
          Entrar
        </Button>
      </form>

      <p className={styles.enlace}>
        ¿No tienes cuenta?{' '}
        <Link to="/registro">Regístrate</Link>
      </p>
    </AuthLayout>
  )
}
