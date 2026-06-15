import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

export default function Registro() {
  const { login }  = useAuth()
  const navigate   = useNavigate()
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const f = e.target.elements
    try {
      await client.post('/registro', {
        nombre_completo: f.nombre_completo.value,
        telefono:        f.telefono.value,
        email:           f.email.value,
        password:        f.password.value,
      })
      // Tras registro exitoso, login automático y redirect a dashboard de cliente
      await login({ email: f.email.value, password: f.password.value })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Error al registrarse')
    }
  }

  return (
    <div>
      <h1>Crear cuenta</h1>
      <form onSubmit={handleSubmit}>
        <input name="nombre_completo" placeholder="Nombre y apellidos" required />
        <input name="telefono"        placeholder="Teléfono"           required />
        <input name="email"           type="email"    placeholder="Email"      required />
        <input name="password"        type="password" placeholder="Contraseña" required />
        <button type="submit">Registrarse</button>
      </form>
      {error && <p>{error}</p>}
      <p>¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></p>
    </div>
  )
}
