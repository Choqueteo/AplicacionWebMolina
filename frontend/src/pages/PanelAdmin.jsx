import { useAuth } from '../context/AuthContext'

export default function PanelAdmin() {
  const { usuario, logout } = useAuth()
  return (
    <div>
      <h1>Panel de administración</h1>
      <p>Sesión: {usuario?.nombre_completo} ({usuario?.rol})</p>
      <button onClick={logout}>Cerrar sesión</button>
    </div>
  )
}
