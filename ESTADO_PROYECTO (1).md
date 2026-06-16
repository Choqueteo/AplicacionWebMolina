# Estado del proyecto — Gestor de Citas Peluquería RM

> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo.

## Qué es

App web de gestión de citas para una peluquería/barbería real (RM), un único peluquero. Stack: FastAPI + React (Vite) + PostgreSQL, desplegará en Render. Mobile-first. Desarrollador único.

---

## Backend — COMPLETADO (fases 1 a 7 + validación + perfil + Telegram)

1. **Configuración y seguridad base**: estructura backend/frontend, venv, git + .gitignore, .env, Alembic, FastAPI con cabeceras de seguridad (HSTS, etc.), CORS, slowapi con límite global, `/health`.
2. **Modelos y migración inicial**: Usuario, Servicio, HorarioPeluquero, Cita, FranjaOcupada. Franjas de 30 min con `UNIQUE(fecha, hora)` que impide solapamientos.
3. **Autenticación**: registro (solo clientes), login con JWT, `get_usuario_actual` y `solo_admin`, seed de los 2 admin desde variables de entorno.
4. **Servicios y horario**: CRUD de servicios (admin) con borrado lógico (`activo`); horario con varios tramos por día.
5. **Disponibilidad y reserva**: `/disponibilidad`, `POST /citas` (transacción todo-o-nada, `409` ante solapamiento), lectura de citas, rate limit por usuario.
6. **Cancelación**: `PATCH /citas/{id}/cancelar`, libera franjas, solo dueño o admin.
7. **Inasistencias**: `no_asistida`, `PATCH /citas/{id}/no-asistida` (admin), contador calculado, campo `bloqueado`.
8. **Validación de registro**: `nombre_completo` (mín. dos palabras, normalizado), `telefono` (formato España, normalizado).
9. **Gestión de cuenta**: `PATCH /usuarios/me` (nombre y teléfono, whitelist estricta) y `PATCH /usuarios/me/password` (verificación previa, bcrypt, rate limit). Sirven para cliente y admin.
10. **Notificaciones Telegram**: bot → peluquero al reservar/cancelar. `BackgroundTasks` post-commit, silent-fail, sin datos personales en logs. `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en variables de entorno.

**84 tests pytest en verde.** BD local en Docker (PostgreSQL) + HeidiSQL.

### Seed de admins — ACTUALIZADO (sesión actual)

- Correos cambiados a **`admin@rmstyle.com`** (desarrollador) y **`peluquero@rmstyle.com`** (peluquero), desde variables de entorno (no hardcodeados).
- Contraseñas **sencillas solo para LOCAL** (`Admin1234` / `Peluquero1234`), en el `.env` local (gitignored). En `.env.example` solo los nombres de las variables.
- Seed hecho **idempotente** (upsert por email, sin duplicados, tope de 2 admins).
- ⚠️ En **producción (Render)** las contraseñas deben ser **fuertes** y distintas de las de local.

### Contratos de backend confirmados (los usa el frontend)

**Auth:**
- `POST /login` → `{ access_token, token_type: "bearer" }`.
- `GET /usuarios/me` → `{ id, email, telefono, nombre_completo, rol }`.
- JWT claims: `sub` (user_id), `rol`, `exp`. El frontend NO decodifica el JWT; llama a `/usuarios/me`.
- `POST /registro` → 201 + UsuarioRead (SIN token). Email duplicado → 409 `{"detail": "El email ya está registrado"}`. Validación password: **mínimo 8 caracteres**.

**Citas/servicios (confirmados en Fase C):**
- `GET /servicios` → solo activos; `[{id, nombre, duracion_minutos, precio (Decimal como string "25.50"), activo}]`. `?incluir_inactivos=true` solo admin.
- `GET /disponibilidad?fecha=YYYY-MM-DD&servicio_id=int` → `{fecha, servicio_id, horas_disponibles: ["HH:MM", ...]}`. Vacío si día cerrado / sin horario / todo ocupado. Filtra horas pasadas si es hoy.
- `POST /citas` → body `{servicio_id, fecha, hora_inicio}` (NO enviar cliente_id/estado/hora_fin → 422). 201 con `hora_fin` calculado. Errores: 403 (bloqueado), 409 (hueco ocupado), 422 (fecha pasada/fuera de horario/servicio inactivo).
- `GET /citas/mias` → `[{id, cliente_id, servicio_id, fecha, hora_inicio, hora_fin, estado}]`. **Solo servicio_id, NO el nombre** → cruzar con `/servicios`. Orden cronológico.
- `PATCH /citas/{id}/cancelar` → body vacío, 200 cancelada (libera franjas). Errores: 404, 409 (ya cancelada), 422 (pasada).
- `GET /horario` → accesible a clientes autenticados; `[{id, dia_semana (0=lunes…6=domingo), hora_apertura, hora_cierre}]`.
- **Zona horaria: Europe/Madrid** (hardcoded en backend). ⚠️ En el frontend construir fechas con componentes locales del `Date`, **nunca `toISOString()`** (desfasa un día por UTC).

---

## Frontend — Fase A COMPLETADA

Cimientos: Vite + React (JS), `react-router-dom`, `axios`. `VITE_API_URL` desde `.env.local`. Cliente HTTP centralizado (`src/api/client.js`) con interceptor Bearer y manejo central de **401** (logout + a `/login`, salvo en login fallido) y **409** (`error.isConflict`). AuthContext (usuario+rol, rehidratación vía `/usuarios/me`, token en localStorage). Rutas por rol. Placeholders iniciales.

## Frontend — Fase B COMPLETADA (sesión actual)

Login y Registro reales con estética premium.

- **Tema claro/oscuro manual** (toggle persistido en localStorage; por defecto oscuro, con `prefers-color-scheme` como valor inicial la primera vez). Tokens en `theme.css` (variables CSS).
- **Estilado**: CSS Modules + variables CSS. Sin frameworks de UI.
- **Tipografía self-hosted** (RGPD): Cormorant Garamond (serif/títulos) + Inter (sans), vía `@fontsource/*` (sin CDN de Google).
- **Logo**: imagen en `src/assets/logo-rm.png` (PNG transparente, sirve para ambos modos). *Nota: el archivo del repo es transparente; la copia "negra" que se vio fue solo un artefacto de conversión a JPEG al subirlo a otro sitio.*
- **Login**: errores 401 ("Email o contraseña incorrectos") y 429 ("Demasiados intentos…"), loading, toggle ver/ocultar contraseña.
- **Registro**: campos nombre + apellidos (se combinan en `nombre_completo` al enviar), teléfono, email, contraseña. Errores 422 por campo (`detail[].msg` + `detail[].loc`), 409 (email duplicado, detectado por status), **auto-login tras registro** (entra directo al dashboard).
- **Textos de ayuda** bajo cada campo del registro (FormField extendido con prop `ayuda` + `aria-describedby`) + frase de privacidad. La de contraseña muestra "Mínimo 8 caracteres".

## Frontend — Fase C COMPLETADA (sesión actual)

Dashboard del cliente.

- **Navegación: pestañas arriba** (Reservar | Mis citas). Cabecera con logo, nombre del usuario, ThemeToggle y Logout.
- **Reservar (todo en una pantalla, progresivo)**: elegir servicio → **calendario propio** (sin librerías; días pasados y días cerrados deshabilitados usando `/horario`; hoy/seleccionado resaltados; accesible) → horas válidas vía `/disponibilidad` → resumen + confirmar (`POST /citas`). Manejo de 409 (aviso + recarga de disponibilidad), 403 (bloqueado), 422.
- **Mis citas**: `GET /citas/mias`, cruce con `serviciosMap` para el nombre. Etiquetas **derivadas** (Reservada/Realizada/No asistió/Cancelada). Cancelar (con modal de confirmación) solo en citas futuras activas.
- **Correcciones aplicadas sobre el plan**:
  - La etiqueta "pasada/futura" y el botón Cancelar usan **fecha + hora** (no solo la fecha), alineado con el criterio del backend para "pasada".
  - Variables CSS verificadas/alineadas con `theme.css` (añadido `--c-border` si faltaba).
  - **Fallback** para citas de servicios desactivados (no estarán en `serviciosMap`).
  - Formato es-ES: precio "25,50 €", duración "30 min" / "1 h".
  - "Realizada" en verde apagado/neutro (no ámbar).
- **Pulido posterior**:
  - **Tipografía** más grande: inputs/cuerpo ≥ 16px (evita zoom de iOS), texto secundario/ayuda ≥ 14-15px; tokens de fuente centralizados; verificado el meta viewport.
  - **Transiciones / micro-interacciones** por defecto y con mesura: cambio de pestaña con animación de entrada (`@keyframes` re-disparada por `key`, no `transition` a secas) + indicador deslizante; hover/seleccionado en tarjetas, horas y calendario; modal de cancelar; solo `transform`/`opacity`; **respeta `prefers-reduced-motion`**; tokens de transición en `theme.css`.

---

## Herramienta de desarrollo — Compartir en local con el peluquero (sesión actual)

Montado para que el peluquero pruebe la app desde su móvil con una URL pública temporal.

- **Un solo túnel** de Cloudflare gracias a un **proxy de Vite**: `vite.config.js` proxya `/api` → `http://localhost:8000` (con rewrite que quita `/api`), `server.host: true`, `allowedHosts` incluye `.trycloudflare.com`. `VITE_API_URL=/api` en `.env.local`. Así frontend y API salen por el mismo origen (sin CORS). *Solo afecta a dev; en producción `VITE_API_URL` será la URL absoluta del backend.*
- Comando: `cloudflared tunnel --url http://localhost:5173`. Si da errores QUIC, añadir `--protocol http2` o desactivar la VPN (la VPN fue la causa de los timeouts).
- Existe un runbook corto en el repo. ⚠️ Expone el entorno local (incl. contraseñas sencillas) a internet: solo para demos cortas, **parar el túnel al terminar**.

---

## Pendiente — Frontend

- **Gestión de cuenta (frontend)**: pantalla "Mi cuenta" accesible desde la cabecera, componente reutilizable para cliente y admin. Decisión abierta: nombre + apellidos separados vs. campo único "Nombre completo".
- **Fase D**: dashboard del admin (agenda con estados derivados, marcar inasistencias, gestión de servicios y horario, bloquear clientes, y su propia "Mi cuenta").

## Pendiente — Configuración Telegram en producción

- Crear bot con `@BotFather` → `TELEGRAM_BOT_TOKEN`.
- Obtener `TELEGRAM_CHAT_ID` del peluquero via `getUpdates`.
- Añadir ambas variables en Render (env vars del backend).

## Pendiente — Despliegue

- Render: backend (Web Service de pago), PostgreSQL gestionado con backups, frontend (static site), variables de entorno y seed de admins en producción (con `VITE_API_URL` absoluta y **contraseñas fuertes**).

---

## Decisiones de diseño (acordadas)

- Estética **premium negro/oro**, modo claro/oscuro **manual** (por defecto oscuro). Mobile-first.
- Logo como **imagen** (`src/assets/logo-rm.png`, transparente).
- Estados de cita **derivados** (no hay "Confirmada").
- En reservar, solo las horas que el servicio puede ocupar; **calendario propio**.
- Micro-interacciones con mesura, solo `transform`/`opacity`, respetando `prefers-reduced-motion`.
- Fuentes **self-hosted** por RGPD.
- Email no editable (login id). Verificación SMS = V2.

## Decisiones técnicas del frontend

- **JavaScript** (no TypeScript). **axios** con interceptores 401/409. Token JWT en localStorage. Rol vía `/usuarios/me`.
- **CSS Modules + variables CSS**. Sin frameworks de UI ni librerías de fechas pesadas.
- En dev, las llamadas a la API pasan por el **proxy de Vite** (`/api`), tanto en local normal como por el túnel.

---

## Siguiente paso (mañana)

1. Implementar el **backend de gestión de cuenta**: `PATCH /usuarios/me` y `PATCH /usuarios/me/password` + tests (Plan Mode; el prompt ya está redactado).
2. Luego el **frontend "Mi cuenta"** (componente reutilizable, desde la cabecera). Decidir ahí el tema nombre/apellidos vs nombre completo.
3. Después, arrancar la **Fase D — dashboard del admin**.
