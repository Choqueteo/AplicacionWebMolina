import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client, { setUnauthorizedHandler } from '../api/client'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario]   = useState(null)
  const [cargando, setCargando] = useState(true)
  const navigate = useNavigate()

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setUsuario(null)
    navigate('/login', { replace: true })
  }, [navigate])

  // Registrar el handler de 401 en el cliente axios (fuera del árbol React)
  useEffect(() => {
    setUnauthorizedHandler(logout)
  }, [logout])

  // Rehidratar sesión al montar: valida el token guardado llamando a /usuarios/me
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setCargando(false); return }
    client.get('/usuarios/me')
      .then((r) => setUsuario(r.data))
      .catch(() => { localStorage.removeItem('token'); setUsuario(null) })
      .finally(() => setCargando(false))
  }, []) // solo al montar

  const login = async (credenciales) => {
    const { data } = await client.post('/login', credenciales)
    localStorage.setItem('token', data.access_token)
    const { data: userData } = await client.get('/usuarios/me')
    setUsuario(userData)
    return userData // el llamador navega según userData.rol
  }

  const refreshUsuario = useCallback(async () => {
    const { data } = await client.get('/usuarios/me')
    setUsuario(data)
  }, [])

  return (
    <AuthCtx.Provider value={{ usuario, cargando, login, logout, refreshUsuario }}>
      {children}
    </AuthCtx.Provider>
  )
}

export function useAuth() { return useContext(AuthCtx) }
