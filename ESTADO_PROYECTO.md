# Estado del proyecto — Gestor de Citas Peluquería RM

> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo.

> **ESTADO ACTUAL: 🟢 EN PRODUCCIÓN.** La app está desplegada y viva en **https://rmolinastyle.com** (API en **https://api.rmolinastyle.com**). Quedan tareas de puesta a punto antes de entregar al peluquero (ver "Pendientes").

## Qué es

App web de gestión de citas para una peluquería/barbería real (RM), un único peluquero. Stack: FastAPI + React (Vite) + PostgreSQL, desplegada en Render. Mobile-first. Desarrollador único.

---

## Backend — COMPLETADO (fases 1 a 7 + validación de registro + gestión de cuenta + Telegram)

1. **Configuración y seguridad base**: estructura backend/frontend, venv, git + .gitignore, .env, Alembic, FastAPI con cabeceras de seguridad (HSTS, etc.), CORS, slowapi con límite global, `/health`.
2. **Modelos y migración inicial**: Usuario, Servicio, HorarioPeluquero, Cita, FranjaOcupada. Franjas de 30 min con `UNIQUE(fecha, hora)` que impide solapamientos.
3. **Autenticación**: registro (solo clientes), login con JWT, `get_usuario_actual` y `solo_admin`, seed de los 2 admin desde variables de entorno.
4. **Servicios y horario**: CRUD de servicios (admin) con borrado lógico (`activo`); horario con soporte de **N tramos por día** (jornada partida), validación de solapamiento en el router.
5. **Disponibilidad y reserva**: `/disponibilidad`, `POST /citas` (transacción todo-o-nada, `409` ante solapamiento), lectura de citas, rate limit por usuario.
6. **Cancelación**: `PATCH /citas/{id}/cancelar`, libera franjas, solo dueño o admin.
7. **Inasistencias**: `no_asistida`, `PATCH /citas/{id}/no-asistida` (admin), contador **almacenado** en `Usuario.inasistencias` (campo + backfill en migración `c7e4a1d9f2b3`), campo `bloqueado`.
8. **Validación de registro**: `nombre_completo` (mín. dos palabras, normalizado), `telefono` (formato España, normalizado).
9. **Gestión de cuenta**: `PATCH /usuarios/me` (nombre + teléfono, whitelist estricta), `PATCH /usuarios/me/password` (verifica actual, bcrypt, rate limit). Ambos sirven a cliente y admin.
10. **Notificaciones Telegram**: aviso al peluquero en `BackgroundTasks` cuando el cliente reserva o cancela; silencia errores sin romper la operación.
11. **Purga de citas (RGPD)**: script `scripts/purga_citas.py` con dry-run, ventana configurable (`RETENCION_MESES`, default 24), idempotente. Preparado para Render Cron Job.

**95 tests pytest en verde.** BD local en Docker (PostgreSQL) + HeidiSQL.

### Seed de admins

- Correos **`admin@rmolinastyle.com`** (desarrollador) y **`peluquero@rmolinastyle.com`** (peluquero), desde variables de entorno. (En local se usaron `@rmstyle.com`; en producción son `@rmolinastyle.com`, solo identificadores de login.)
- Seed **idempotente, CREATE-IF-MISSING** (upsert por email, sin duplicados, tope de 2 admins).
- ⚠️ **Comportamiento clave**: si el admin **no existe** → lo crea con todos los datos (incluida la contraseña). Si **ya existe** → solo garantiza `rol=admin` y `bloqueado=False`, y **nunca toca** `password_hash`, `nombre_completo` ni `telefono`.
- ⚠️ **Implicación práctica**: una vez creado un admin, **cambiar su contraseña en las variables de Render NO la actualiza**. Para resetearla hay que borrar su fila en la BD y re-sembrar (ver Pendientes → login del peluquero).

### Contratos de backend confirmados (los usa el frontend)

**Auth:**
- `POST /login` → `{ access_token, token_type: "bearer" }`.
- `GET /usuarios/me` → `{ id, email, telefono, nombre_completo, rol }`.
- JWT claims: `sub` (user_id), `rol`, `exp`. El frontend NO decodifica el JWT; llama a `/usuarios/me`.
- `POST /registro` → 201 + UsuarioRead (SIN token). Email duplicado → 409. Password: **mínimo 8 caracteres**.

**Citas/servicios:**
- `GET /servicios` → solo activos; `[{id, nombre, duracion_minutos, precio (Decimal como string "25.50"), activo}]`. `?incluir_inactivos=true` solo admin.
- `GET /disponibilidad?fecha=YYYY-MM-DD&servicio_id=int` → `{fecha, servicio_id, horas_disponibles: ["HH:MM", ...]}`. Vacío si día cerrado / sin horario / todo ocupado. Filtra horas pasadas si es hoy.
- `POST /citas` → body `{servicio_id, fecha, hora_inicio}` (NO enviar cliente_id/estado/hora_fin → 422). 201 con `hora_fin` calculado. Errores: 403 (bloqueado), 409 (hueco ocupado), 422.
- `GET /citas/mias` → `[{id, cliente_id, servicio_id, fecha, hora_inicio, hora_fin, estado}]`. **Solo servicio_id, NO el nombre** → cruzar con `/servicios`. Orden cronológico.
- `PATCH /citas/{id}/cancelar` → body vacío, 200 cancelada (libera franjas). Errores: 404, 409 (ya cancelada), 422 (pasada).
- `GET /horario` → accesible a clientes autenticados; `[{id, dia_semana (0=lunes…6=domingo), hora_apertura, hora_cierre}]`.
- **Zona horaria: Europe/Madrid**. ⚠️ En el frontend construir fechas con componentes locales del `Date`, **nunca `toISOString()`**.

---

## Frontend — Fases A, B, C, C.extra y D — COMPLETADAS

- **Fase A (cimientos)**: Vite + React (JS), `react-router-dom`, `axios`. Cliente HTTP centralizado (`src/api/client.js`) con interceptor Bearer y manejo central de **401** (logout + a `/login`) y **409** (`error.isConflict`). AuthContext (usuario+rol, rehidratación vía `/usuarios/me`, token en localStorage). Rutas por rol.
- **Fase B (login/registro)**: pantallas reales con estética premium. Tema claro/oscuro manual (por defecto oscuro). CSS Modules + variables CSS. Tipografía self-hosted (RGPD): Cormorant Garamond + Inter. Logo `src/assets/logo-rm.png`. Auto-login tras registro. Errores 422 por campo + 409.
- **Fase C (dashboard cliente)**: pestañas Reservar / Mis citas. Reservar progresivo (servicio → calendario propio → horas → confirmar). Etiquetas derivadas. Cancelar en futuras activas. Formato es-ES. Micro-interacciones con `prefers-reduced-motion`.
- **Fase C.extra ("Mi cuenta")**: `/mi-cuenta` (cualquier rol). FormularioPerfil (email read-only; nombre y teléfono editables) y FormularioPassword. `refreshUsuario()` en AuthContext.
- **Fase D (panel admin)**: shell mobile-first con barra inferior (Agenda / Servicios / Horario / Clientes). TabAgenda (citas del día, no-show, cancelar), TabServicios (CRUD + activar/desactivar), TabHorario (N tramos/día), TabClientes (inasistencias, bloquear/desbloquear). Iconos SVG inline, bug de calendario "hoy" corregido (componentes locales, no UTC).

---

## Notificaciones al peluquero (Telegram) — COMPLETADO

Aviso al peluquero por Telegram cuando un cliente reserva o cancela. Envío en `BackgroundTasks` tras confirmar la transacción; los fallos no rompen la operación. Minimización RGPD. `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` configurados en Render (el `chat_id` es el del peluquero).
⚠️ Para que los avisos lleguen, el peluquero debe haber hecho `/start` al bot al menos una vez (ver Pendientes).

---

## Purga de citas (RGPD) — IMPLEMENTADA (script), pendiente de programar

- **Contador almacenado**: `Usuario.inasistencias` (migración `c7e4a1d9f2b3` con backfill).
- **Script**: `backend/scripts/purga_citas.py` — borrado real, dry-run, ventana 24 meses (`RETENCION_MESES`).
- **Pendiente**: configurar el Render Cron Job (ver Pendientes).

---

## Despliegue en Render — ✅ COMPLETADO (EN PRODUCCIÓN)

La app está **desplegada y viva** en su dominio propio. Se desplegó vía **Blueprint** (`render.yaml`).

### URLs en producción
- **Frontend**: `https://rmolinastyle.com` (+ `https://www.rmolinastyle.com` → **redirige** al apex, lo gestiona Render automáticamente).
- **Backend/API**: `https://api.rmolinastyle.com`
- URLs internas de Render (los nombres `rm-backend`/`rm-frontend` estaban ocupados globalmente → Render añadió sufijo):
  - Backend: `https://rm-backend-z7zb.onrender.com`
  - Frontend: `https://rm-frontend-4wr6.onrender.com`

### Dominio y DNS
- Dominio **`rmolinastyle.com`** registrado en **Cloudflare Registrar** (~10,46 $/año, a coste, sin markup en renovación, WHOIS privacy incluida, auto-renew activado). A nombre de Cristian.
- DNS en Cloudflare: **3 registros CNAME, los tres en "DNS only" (nube gris)**:
  - `api` → `rm-backend-z7zb.onrender.com`
  - `www` → `rm-frontend-4wr6.onrender.com`
  - `@` (apex, vía CNAME flattening de Cloudflare) → `rm-frontend-4wr6.onrender.com`
- HTTPS emitido por Render (Let's Encrypt) para los 3 dominios.

### render.yaml (Blueprint) — estado actual
- 3 piezas: `rm-backend` (web, Python, **Starter**, Frankfurt), `rm-frontend` (**static site**, Frankfurt), `rm-postgres` (**basic-256mb**, Frankfurt, `ipAllowList: []` → solo conexiones internas).
- Pre-deploy: `alembic upgrade head && python seed.py`.
- Bloques `domains:` **activos** (backend: `api.rmolinastyle.com`; frontend: `rmolinastyle.com` + `www.rmolinastyle.com`).
- `VITE_API_URL = https://api.rmolinastyle.com` (build-time).
- `ALLOWED_ORIGINS = ["https://rmolinastyle.com","https://www.rmolinastyle.com"]`.
- Comentarios en el archivo documentan los valores `.onrender.com` de la fase intermedia (por si hubiera que volver atrás).
- Variables secretas (`ADMIN1_*`, `ADMIN2_*`, `TELEGRAM_*`) introducidas a mano en el panel (`sync: false`). `SECRET_KEY` autogenerada (`generateValue`). `DATABASE_URL` inyectada desde la BD (normalizada a `postgresql+psycopg://` por el `field_validator` de `config.py`).

### Cómo se hizo (historia del despliegue)
1. Primer deploy en URLs `.onrender.com` (sin dominio) para separar "¿falla el código?" de "¿falla el DNS?".
2. Los nombres `rm-backend`/`rm-frontend` estaban ocupados → se corrigieron `VITE_API_URL` y `ALLOWED_ORIGINS` con las URLs reales (con sufijo `-z7zb` / `-4wr6`).
3. Smoke test completo en verde sobre `.onrender.com`.
4. El peluquero confirma que quiere dominio propio → compra de `rmolinastyle.com` en Cloudflare.
5. Se activan los `domains:` en `render.yaml` → 3 CNAME en Cloudflare → Render verifica + emite HTTPS.
6. Se cambian las dos variables al dominio propio → app viva en `rmolinastyle.com`.

### Coste real
~**17,50 $/mes** (backend Starter ~7 $ + Postgres basic-256mb ~7 $ + extras de almacenamiento/ancho de banda; frontend estático **gratis**). Dominio ~10 €/año aparte.

### Verificación final — TODO EN VERDE ✅
Registro + login cliente, login admin (`admin@`), reservar, cancelar, aviso Telegram, recargar en `/admin` y `/mi-cuenta` sin 404, responsive en móvil. Todo OK sobre el dominio propio.
⚠️ **Excepción**: el login del peluquero (`peluquero@`) da error con su contraseña (ver Pendientes).

---

## Pendientes (antes de entregar al peluquero / cierre)

1. **Arreglar el login del peluquero** (`peluquero@rmolinastyle.com`): da error con su contraseña. **Causa probable**: la cuenta se creó en el primer deploy con una contraseña distinta (typo en `ADMIN2_PASSWORD`), y como el seed es CREATE-IF-MISSING, **no la actualiza** en deploys posteriores.
   - **Descartar primero**: email exacto y en minúsculas; comparar el `ADMIN2_PASSWORD` real de Render con lo que se teclea; descartar 429 (rate limit, esperar unos minutos).
   - **Si es mismatch real**: (a) poner `ADMIN2_PASSWORD` correcto en Render; (b) borrar la fila → `DELETE FROM usuarios WHERE email='peluquero@rmolinastyle.com';`; (c) redeploy o `python seed.py` en la Shell del backend → la recrea con la contraseña correcta.
   - ⚠️ La BD es `ipAllowList: []` (solo interna): usar la **Shell de `rm-backend`** o **allowlistar la IP temporalmente**. **NO** modificar `seed.py` para sobrescribir contraseñas (reintroduce el bug de clobbering).
   - Opción: mini-script `scripts/reset_admin.py` que haga borrado + reseed de un admin de forma segura, para ejecutar en la Shell.
2. **Reiniciar horarios y eliminar las citas de prueba** antes de entregar.
   - ⚠️ La cuenta de cliente registrada en las pruebas **NO se borra**: es la **cuenta personal de Cristian** para pedir cita.
   - Los tramos de horario se borran desde el panel admin (TabHorario). Las citas de prueba: desde la BD (mismo acceso que el punto 1) o cancelándolas.
3. **Configurar servicios y horario reales** con el peluquero (precios, duraciones, tramos reales, jornada partida si aplica).
4. **Confirmar Telegram al peluquero**: que haya hecho `/start` al bot, o no se le entregan los avisos.
5. **Cron Job de purga RGPD** (`scripts/purga_citas.py`) en Render — pendiente de programar (diario/semanal). No está en `render.yaml`.
6. **Observabilidad: Sentry y BetterStack** — pendiente de integrar. Van DESPUÉS, sin afectar al despliegue base (solo alguna variable de entorno / config en su panel).

---

## Decisiones de diseño (acordadas)

- Estética **premium negro/oro**, modo claro/oscuro **manual** (por defecto oscuro). Mobile-first.
- Logo como **imagen** (`src/assets/logo-rm.png`, transparente).
- Estados de cita **derivados** (no hay "Confirmada").
- En reservar, solo las horas que el servicio puede ocupar; **calendario propio**.
- Micro-interacciones con mesura, solo `transform`/`opacity`, respetando `prefers-reduced-motion`.
- Fuentes **self-hosted** por RGPD. Email no editable (login id). Verificación SMS = V2.
- Avisos al peluquero por **Telegram** (V1). Recordatorios a clientes por WhatsApp/SMS = V2.

## Decisiones técnicas del frontend

- **JavaScript** (no TypeScript). **axios** con interceptores 401/409. Token JWT en localStorage. Rol vía `/usuarios/me`.
- **CSS Modules + variables CSS**. Sin frameworks de UI ni librerías de fechas pesadas.
- En dev, las llamadas a la API pasan por el **proxy de Vite** (`/api`); en producción `VITE_API_URL` es la URL absoluta del backend.

---

## Herramienta de desarrollo — Compartir en local (Cloudflare Tunnel)

- Un solo túnel con proxy de Vite (`/api` → `localhost:8000`), `allowedHosts` con `.trycloudflare.com`. Comando: `cloudflared tunnel --url http://localhost:5173`. Si da errores QUIC: `--protocol http2` o desactivar la VPN. Solo dev; parar el túnel al terminar.

---

## Siguiente paso inmediato

Resolver el **login del peluquero** (punto 1 de Pendientes) y la **limpieza de horarios/citas de prueba** (punto 2), que requieren acceso a la BD interna. Luego configurar servicios/horario reales y confirmar Telegram. Sentry/BetterStack y el Cron de purga, después.
