# Plan de despliegue en Render — Gestor de Citas RM

> Runbook paso a paso. Tres piezas en Render: **PostgreSQL gestionada**, **backend** (Web Service) y **frontend** (static site), con **dominio propio `rmolinastyle.com`**.
>
> **Estrategia recomendada (a prueba de sustos):** primero despliega y verifica todo con las URLs por defecto de Render (`.onrender.com`); cuando funcione de punta a punta, añade el dominio propio y el DNS, y al final cambias las URLs a las definitivas. Así separas "¿falla el código?" de "¿falla el DNS?".
>
> **Dominios objetivo:** frontend → `rmolinastyle.com` (+ `www.rmolinastyle.com`); backend/API → `api.rmolinastyle.com`.
>
> **El orden importa: BD → backend → frontend → CORS → (verificar) → dominios + DNS → cambiar URLs.**

---

## Fase 0 — Antes de tocar Render (en local)

1. **`pytest` todo en verde.**
2. **Repaso de seguridad:** DEBUG off; los 500 no filtran stack trace; rate limits activos; secretos solo en variables de entorno; el proxy de Vite y `allowedHosts` del túnel son solo de desarrollo.
3. **`requirements.txt` y `package.json` completos y commiteados.** Confirma el comando de arranque del backend y el de build del frontend.
4. **Genera secretos de PRODUCCIÓN fuertes:**
   - Secreto JWT nuevo (o que lo autogenere Render con `generateValue`).
   - Contraseñas fuertes para los admins (distintas de local).
   - Ten a mano `TELEGRAM_BOT_TOKEN` y el `chat_id` del **peluquero**.
5. **Correos de admin (recomendado):** usa `admin@rmolinastyle.com` y `peluquero@rmolinastyle.com` (alineados con tu dominio). Son solo identificadores de login; no necesitan ser buzones reales.
6. Ten registrado y a tu nombre el dominio **`rmolinastyle.com`**. Crea cuenta en Render y **conecta tu repo de GitHub**.

---

## Fase 1 — PostgreSQL gestionada (primero)

1. **New + → PostgreSQL.**
2. **Región: Europa (Frankfurt)** — RGPD y latencia (estás en España).
3. **Plan de PAGO** (el gratuito caduca a los 30 días y no tiene backups). El más pequeño con **backups diarios** sirve.
4. Copia la **"Internal Database URL"**.

---

## Fase 2 — Backend (Web Service)

1. **New + → Web Service** → conecta el repo. Root = carpeta del backend (si es monorepo).
2. **Runtime: Python.**
3. **Build:** `pip install -r requirements.txt`
4. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT` *(ajusta a tu estructura; o gunicorn con workers uvicorn)*.
5. **Pre-Deploy Command:** `alembic upgrade head && <comando del seed>` *(idempotente, create-if-missing para los admins)*.
6. **Instance type: Starter (~7 $/mes, always-on).** Nunca la gratuita (se duerme a los 15 min).
7. **Región: la MISMA que la BD (Frankfurt).**
8. **Health check path:** `/health`
9. **Variables de entorno:**
   - `DATABASE_URL` = Internal Database URL (Fase 1).
   - Secreto JWT (fuerte).
   - Variables del seed: emails admin (`@rmolinastyle.com`) + **contraseñas fuertes**.
   - `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (el del peluquero).
   - `ALLOWED_ORIGINS` = **de momento la URL del frontend en `.onrender.com`** (la cambias por el dominio propio en la Fase 6).
   - Zona horaria si tu código la lee de entorno (Europe/Madrid).
10. Deploy. En los logs, verifica que migró y sembró; `/health` responde 200.

---

## Fase 3 — Frontend (Static Site)

1. **New + → Static Site** → conecta el repo. Root = carpeta del frontend.
2. **Build:** `npm install && npm run build`
3. **Publish directory:** `dist`
4. **Variable (build-time):** `VITE_API_URL` = **de momento la URL del backend en `.onrender.com`** (la cambias en la Fase 6). ⚠️ Nunca `/api`.
5. **IMPORTANTE (SPA):** regla de **Rewrite** `/*` → `/index.html` (acción Rewrite). Sin esto, recargar en `/admin`, `/mi-cuenta` da 404.
6. Deploy. Copia la URL del frontend.

---

## Fase 4 — CORS + verificación en URLs `.onrender.com`

1. Backend → `ALLOWED_ORIGINS` = la URL real del frontend (`https://<tu-frontend>.onrender.com`). Redeploy del backend.
2. **Verifica TODO funcionando ya con las URLs `.onrender.com`** (registro/login, reservar, cancelar, inasistencia, Telegram, recargar en rutas profundas). No sigas al dominio propio hasta que esto vaya bien.

---

## Fase 5 — Dominios propios + DNS

1. **Backend:** añade el dominio `api.rmolinastyle.com` en la configuración del web service.
2. **Frontend:** añade `rmolinastyle.com` y `www.rmolinastyle.com` en la configuración del static site; marca uno como principal (recomendado: apex `rmolinastyle.com`) y el otro como redirección.
3. **DNS (en tu registrador):** crea los registros EXACTOS que te indique Render para cada dominio (normalmente un CNAME para `api.` y `www.`, y un registro A/ALIAS para el apex). Render verifica el dominio y **emite el certificado HTTPS automáticamente** (puede tardar unos minutos).

---

## Fase 6 — Cambiar a los dominios definitivos

1. Backend → `ALLOWED_ORIGINS` = `https://rmolinastyle.com,https://www.rmolinastyle.com`. Redeploy del backend.
2. Frontend → `VITE_API_URL` = `https://api.rmolinastyle.com`. **Rebuild del frontend** (es build-time).
3. Comprueba que el frontend en `rmolinastyle.com` habla con la API en `api.rmolinastyle.com` sin errores de CORS.

---

## Fase 7 — Puesta a punto

1. Entra como admin (`admin@rmolinastyle.com` + contraseña fuerte de producción).
2. Configura **servicios** y **horario** desde el panel (incluidos tramos partidos).
3. **Telegram:** el peluquero le da Start al bot (si no lo hizo), su `chat_id` está en las variables de producción, haces una reserva de prueba → debe llegarle el aviso.

---

## Fase 8 — Verificación final (checklist)

- [ ] HTTPS en `rmolinastyle.com` y `api.rmolinastyle.com`.
- [ ] `www.rmolinastyle.com` redirige al apex.
- [ ] Registro + login de cliente.
- [ ] Login de admin y de peluquero.
- [ ] Reservar / cancelar / marcar inasistencia.
- [ ] Aviso de Telegram al reservar y cancelar (como cliente).
- [ ] Recargar en `/admin`, `/mi-cuenta` NO da 404.
- [ ] Un 500 no muestra stack trace; rate limits activos.
- [ ] Responsive en móvil (375 px).

---

## Notas

- **No copies tu base de datos local a producción.** Producción arranca limpia: el `alembic upgrade head` crea las tablas y el seed crea **solo los 2 admins**. Servicios, horario, clientes y citas empiezan vacíos.
- **Coste base aproximado:** backend Starter ~7 $/mes + PostgreSQL pequeña con backups ~7 $/mes + frontend static gratis ≈ **~14 $/mes**. Verifica las cifras en la página de precios de Render.
- **Telegram:** el `chat_id` de producción es el del peluquero. En local, apunta el `chat_id` a otro sitio (o déjalo vacío) para no avisarle con tus pruebas.
- **Sentry y BetterStack** se añaden DESPUÉS, sin afectar a estos pasos (solo alguna variable de entorno más / config en su panel).
- **Alternativa IaC:** puedes definir las 3 piezas y los dominios en un `render.yaml` (Blueprint) para un despliegue reproducible.
