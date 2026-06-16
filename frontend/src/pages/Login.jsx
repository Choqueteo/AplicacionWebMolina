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
              {mostrarPass ? '🙈' : '👁'}
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
