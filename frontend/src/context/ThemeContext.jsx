import { createContext, useContext, useEffect, useState } from 'react'

const ThemeCtx = createContext(null)

function getInitialTema() {
  try {
    const saved = localStorage.getItem('tema')
    if (saved === 'dark' || saved === 'light') return saved
  } catch (_) {}
  // Primera vez: respetar preferencia del sistema, o dark por defecto
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  } catch (_) {}
  return 'dark'
}

export function ThemeProvider({ children }) {
  const [tema, setTema] = useState(getInitialTema)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tema)
    try { localStorage.setItem('tema', tema) } catch (_) {}
  }, [tema])

  const toggleTema = () => setTema(t => (t === 'dark' ? 'light' : 'dark'))

  return (
    <ThemeCtx.Provider value={{ tema, toggleTema }}>
      {children}
    </ThemeCtx.Provider>
  )
}

export function useTheme() { return useContext(ThemeCtx) }
