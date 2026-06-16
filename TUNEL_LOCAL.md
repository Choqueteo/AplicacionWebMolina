# Demo local con túnel Cloudflare

> ⚠️ AVISO DE SEGURIDAD: Este túnel expone tu entorno local a internet.
> Las contraseñas de los admins son sencillas (Admin1234, Peluquero1234).
> Úsalo SOLO para demos cortas y **PARA el túnel al terminar**.

---

## Requisitos previos

### Instalar cloudflared (solo la primera vez)

Con winget (Windows):
```
winget install --id Cloudflare.cloudflared
```

Si winget no está disponible, descarga el binario desde:
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

Verifica que funciona:
```
cloudflared --version
```

---

## Orden de arranque (3 terminales)

**Terminal 1 — Backend** (desde `backend/`)
```
venv\Scripts\uvicorn app.main:app --reload
```

**Terminal 2 — Frontend** (desde `frontend/`)
```
npm run dev
```
Vite mostrará `Local: http://localhost:5173` y también la IP de red. Todas las
llamadas axios van a `/api/...` y el proxy de Vite las reenvía al backend en
`http://localhost:8000`.

**Terminal 3 — Túnel** (desde cualquier directorio)
```
cloudflared tunnel --url http://localhost:5173
```
Espera hasta ver una línea como:
```
https://xxxx-xxxx-xxxx.trycloudflare.com
```
Copia esa URL y pásasela al peluquero.

---

## Para parar

```
Ctrl+C  →  terminal del túnel      (URL desaparece de inmediato)
Ctrl+C  →  terminal de Vite
Ctrl+C  →  terminal de uvicorn
```

---

## Notas técnicas

- **Errores de WebSocket en consola**: si el peluquero ve errores de WS/HMR,
  son del hot-reload de Vite. Inofensivos para la demo; la app funciona igual.
- **Solo para dev**: en producción (Render) `VITE_API_URL` es la URL absoluta
  del backend. El proxy de Vite no interviene allí.
- **`.env.local` no se commitea**: está en `.gitignore`. Confirmado.
