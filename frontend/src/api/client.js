import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Callback de logout registrado por AuthContext; vive fuera del árbol React.
let _onUnauthorized = null
export function setUnauthorizedHandler(fn) { _onUnauthorized = fn }

// Request: inyecta Bearer si hay token en localStorage
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response: manejo central de 401 y 409
client.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status
    const url    = error.config?.url ?? ''

    // 401 en /login = credenciales incorrectas, no sesión caducada → no llamar logout
    if (status === 401 && !url.includes('/login') && _onUnauthorized) {
      _onUnauthorized()
    }

    // 409: marca el error para que la pantalla de reservas pueda identificarlo
    if (status === 409) {
      error.isConflict = true
    }

    return Promise.reject(error)
  }
)

export default client
