import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login }  = useAuth()
  const navigate   = useNavigate()
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const { email, password } = e.target.elements
    try {
      const usuario = await login({ email: email.value, password: password.value })
      navigate(usuario.rol === 'admin' ? '/admin' : '/dashboard', { replace: true })
    } catch {
      setError('Credenciales incorrectas')
    }
  }

  return (
    <div>
      <h1>Iniciar sesión</h1>
      <form onSubmit={handleSubmit}>
        <input name="email"    type="email"    placeholder="Email"      required />
        <input name="password" type="password" placeholder="Contraseña" required />
        <button type="submit">Entrar</button>
      </form>
      {error && <p>{error}</p>}
      <p>¿No tienes cuenta? <Link to="/registro">Regístrate</Link></p>
    </div>
  )
}
