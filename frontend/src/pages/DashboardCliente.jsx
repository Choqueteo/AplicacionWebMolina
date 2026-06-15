import { useAuth } from '../context/AuthContext'

export default function DashboardCliente() {
  const { usuario, logout } = useAuth()
  return (
    <div>
      <h1>Dashboard cliente</h1>
      <p>Bienvenido/a, {usuario?.nombre_completo}</p>
      <button onClick={logout}>Cerrar sesión</button>
    </div>
  )
}
