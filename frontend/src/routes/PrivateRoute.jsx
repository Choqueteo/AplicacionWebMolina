import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Redirige a /login si no hay sesión activa. */
export function PrivateRoute({ children }) {
  const { usuario, cargando } = useAuth()
  if (cargando) return <div>Cargando…</div>
  if (!usuario)  return <Navigate to="/login" replace />
  return children
}

/**
 * Redirige a /login si no hay sesión, o al propio dashboard si el rol
 * no coincide con el requerido.
 */
export function RoleRoute({ rol, children }) {
  const { usuario, cargando } = useAuth()
  if (cargando) return <div>Cargando…</div>
  if (!usuario)  return <Navigate to="/login" replace />
  if (usuario.rol !== rol)
    return <Navigate to={usuario.rol === 'admin' ? '/admin' : '/dashboard'} replace />
  return children
}
