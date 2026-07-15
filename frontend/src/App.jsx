import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { PrivateRoute, RoleRoute } from './routes/PrivateRoute'
import Login             from './pages/Login'
import Registro          from './pages/Registro'
import DashboardCliente  from './pages/DashboardCliente'
import MiCuenta          from './pages/MiCuenta'
import PanelAdmin        from './pages/PanelAdmin'
import AvisoLegal        from './pages/AvisoLegal'
import PoliticaPrivacidad from './pages/PoliticaPrivacidad'
import PoliticaCookies   from './pages/PoliticaCookies'
import Footer            from './components/layout/Footer'

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
            <Route path="/aviso-legal"         element={<AvisoLegal />} />
            <Route path="/politica-privacidad" element={<PoliticaPrivacidad />} />
            <Route path="/politica-cookies"    element={<PoliticaCookies />} />
            <Route path="/dashboard" element={
              <RoleRoute rol="cliente"><DashboardCliente /></RoleRoute>
            } />
            <Route path="/admin"     element={
              <RoleRoute rol="admin"><PanelAdmin /></RoleRoute>
            } />
            <Route path="/mi-cuenta" element={
              <PrivateRoute><MiCuenta /></PrivateRoute>
            } />
            {/* Cualquier ruta desconocida va a la raíz (que redirige según sesión) */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Footer />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
