import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { RoleRoute } from './routes/PrivateRoute'
import Login            from './pages/Login'
import Registro         from './pages/Registro'
import DashboardCliente from './pages/DashboardCliente'
import PanelAdmin       from './pages/PanelAdmin'

/** Redirige la raíz según estado de sesión: sin sesión → login, cliente → dashboard, admin → panel. */
function RootRedirect() {
  const { usuario, cargando } = useAuth()
  if (cargando) return <div>Cargando…</div>
  if (!usuario)                return <Navigate to="/login"    replace />
  if (usuario.rol === 'admin') return <Navigate to="/admin"    replace />
  return                              <Navigate to="/dashboard" replace />
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/"          element={<RootRedirect />} />
            <Route path="/login"     element={<Login />} />
            <Route path="/registro"  element={<Registro />} />
            <Route path="/dashboard" element={
              <RoleRoute rol="cliente"><DashboardCliente /></RoleRoute>
            } />
            <Route path="/admin"     element={
              <RoleRoute rol="admin"><PanelAdmin /></RoleRoute>
            } />
            {/* Cualquier ruta desconocida va a la raíz (que redirige según sesión) */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
