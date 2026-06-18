# Estado del proyecto — Gestor de Citas Peluquería RM

> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo.

## Qué es

App web de gestión de citas para una peluquería/barbería real (RM), un único peluquero. Stack: FastAPI + React (Vite) + PostgreSQL, desplegará en Render. Mobile-first. Desarrollador único.

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

### Seed de admins — ACTUALIZADO

- Correos **`admin@rmstyle.com`** (desarrollador) y **`peluquero@rmstyle.com`** (peluquero), desde variables de entorno.
- Contraseñas **sencillas solo para LOCAL** (`Admin1234` / `Peluquero1234`) en el `.env` local (gitignored). En `.env.example` solo los nombres.
- Seed **idempotente** (upsert por email, sin duplicados, tope de 2 admins).
- ⚠️ En **producción (Render)** las contraseñas deben ser **fuertes** y distintas de las de local.

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

## Frontend — Fase A COMPLETADA

Cimientos: Vite + React (JS), `react-router-dom`, `axios`. Cliente HTTP centralizado (`src/api/client.js`) con interceptor Bearer y manejo central de **401** (logout + a `/login`, salvo login fallido) y **409** (`error.isConflict`). AuthContext (usuario+rol, rehidratación vía `/usuarios/me`, token en localStorage). Rutas por rol.

## Frontend — Fase B COMPLETADA

Login y Registro reales con estética premium.

- **Tema claro/oscuro manual** (toggle persistido; por defecto oscuro, con `prefers-color-scheme` como inicial la primera vez). Tokens en `theme.css`.
- CSS Modules + variables CSS. Sin frameworks de UI.
- **Tipografía self-hosted** (RGPD): Cormorant Garamond (serif) + Inter (sans) vía `@fontsource/*`.
- **Logo**: `src/assets/logo-rm.png` (PNG transparente, ambos modos).
- **Login**: errores 401 / 429 / 5xx (mensajes distintos), loading, ver/ocultar contraseña con **icono SVG** (`currentColor`, respeta modo claro/oscuro).
- **Registro**: nombre + apellidos (se combinan en `nombre_completo`), teléfono, email, contraseña. Errores 422 por campo + 409 (email duplicado). **Auto-login tras registro**. Textos de ayuda por campo (`FormField` con prop `ayuda` + `aria-describedby`) + frase de privacidad. Password muestra "Mínimo 8 caracteres".

## Frontend — Fase C COMPLETADA

Dashboard del cliente.

- **Pestañas arriba** (Reservar | Mis citas). Cabecera con logo, nombre (botón), ThemeToggle y Logout.
- **Reservar (todo en una pantalla, progresivo)**: servicio → **calendario propio** (días pasados/cerrados deshabilitados usando `/horario`; hoy/seleccionado resaltados; accesible) → horas vía `/disponibilidad` → resumen + confirmar (`POST /citas`). Manejo de 409/403/422.
- **Mis citas**: `GET /citas/mias` cruzado con `serviciosMap`. Etiquetas derivadas (Reservada/Realizada/No asistió/Cancelada). Cancelar (con modal) solo en futuras activas.
- **Correcciones aplicadas**: etiqueta "pasada/futura" y botón Cancelar usan **fecha + hora** (alineado con el backend); variables CSS verificadas (`--c-border` añadido si faltaba); **fallback** para servicios desactivados; formato es-ES ("25,50 €", "30 min"/"1 h"); "Realizada" en verde apagado/neutro.
- **Pulido**: tipografía mayor (inputs/cuerpo ≥ 16px, secundario ≥ 14-15px; verificado meta viewport); transiciones/micro-interacciones con mesura (cambio de pestaña con `@keyframes` re-disparada por `key` + indicador deslizante; hover/seleccionado en tarjetas/horas/calendario; modal; solo `transform`/`opacity`; respeta `prefers-reduced-motion`; tokens de transición en `theme.css`).

## Frontend — Fase C.extra COMPLETADA — "Mi cuenta"

Pantalla de gestión del perfil propio, accesible tocando el nombre en la cabecera del dashboard.

- **Ruta protegida** `/mi-cuenta` (`PrivateRoute`, accesible a cualquier rol) con header propio (← Volver, título, ThemeToggle).
- **FormularioPerfil**: email read-only/disabled con nota, nombre completo y teléfono editables, pre-poblados con los datos actuales. Éxito refresca `AuthContext` para actualizar la cabecera al instante. Errores 422 campo a campo.
- **FormularioPassword**: contraseña actual (toggle visible con **icono SVG**), nueva (toggle visible con **icono SVG**, "Mínimo 8 caracteres"), repetir nueva. Validación cliente (no coinciden); errores 400 (contraseña actual incorrecta), 422, 429, resetea campos en éxito.
- Ambos componentes son **agnósticos al rol** (Phase D los reutiliza sin cambios).
- `refreshUsuario()` añadido a `AuthContext` para re-fetch `/usuarios/me` y actualizar estado.

---

## Notificaciones al peluquero (Telegram) — COMPLETADO y VERIFICADO

Aviso al peluquero por Telegram cuando un cliente reserva o cancela.

- Disparadores: `POST /citas` con éxito ("nueva reserva") y `PATCH /citas/{id}/cancelar` **solo si cancela el cliente** (no si cancela el admin).
- Envío en **segundo plano** (`BackgroundTasks`) y **tras confirmar la transacción** en la BD; los fallos se capturan/registran y **nunca** rompen ni retrasan la reserva/cancelación. No envía si faltan las variables de entorno.
- Mensaje conciso: nombre, teléfono, servicio, fecha y hora, acción. Minimización RGPD.
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env` local (gitignored); en `.env.example` solo los nombres.
- **Verificado**: el aviso llega correctamente al chat del peluquero.
- ⚠️ En **producción (Render)** hay que configurar esas dos variables de entorno (con el `chat_id` del peluquero).

---

## Herramienta de desarrollo — Compartir en local con el peluquero

- **Un solo túnel** de Cloudflare con **proxy de Vite**: `vite.config.js` proxya `/api` → `http://localhost:8000` (rewrite que quita `/api`), `server.host: true`, `allowedHosts` incluye `.trycloudflare.com`. `VITE_API_URL=/api` en `.env.local`. Mismo origen, sin CORS. *Solo dev; en producción `VITE_API_URL` será la URL absoluta del backend.*
- Comando: `cloudflared tunnel --url http://localhost:5173`. Si da errores QUIC, añadir `--protocol http2` o desactivar la VPN (la VPN fue la causa de los timeouts).
- ⚠️ Expone el entorno local a internet: solo demos cortas, **parar el túnel al terminar**.

---

## Purga de citas (RGPD) — IMPLEMENTADA

- **Contador almacenado**: `Usuario.inasistencias` (campo int, migración `c7e4a1d9f2b3` con backfill). Ya no se calcula dinámicamente.
- **Script**: `backend/scripts/purga_citas.py` — borrado real, dry-run, ventana 24 meses (configurable via `RETENCION_MESES`).
- **Pendiente**: configurar el Render Cron Job al desplegar (diario o semanal, comando `python scripts/purga_citas.py`).

---

## Frontend — Fase D COMPLETADA

Dashboard del admin (panel del peluquero), mobile-first con barra de navegación inferior fija (4 secciones).

- **Shell `PanelAdmin.jsx`** + `DashboardAdmin.module.css`: cabecera con logo, botón Mi cuenta (→ `/mi-cuenta`), ThemeToggle y Salir. Barra inferior fija (56px) con Agenda / Servicios / Horario / Clientes.
- **TabAgenda**: agenda del día seleccionado. Navegación ← [fecha] → [Hoy] [icono SVG calendario]. Citas con nombre + teléfono (clicable), servicio y etiqueta derivada. "No asistió" solo para citas pasadas activas; "Cancelar" solo para futuras activas. Modal de confirmación inline.
- **TabServicios**: lista con badges Activo/Inactivo. Edición inline (form dentro de la tarjeta). Crear, desactivar (`DELETE`) y reactivar (`PUT` con `{activo: true}`).
- **TabHorario**: 7 días de la semana; cada día lista **todos sus tramos** (jornada partida). Botón "+ Añadir tramo" siempre visible. Editar/eliminar cada tramo por separado con formulario inline y confirmación inline.
- **TabClientes**: lista filtrada a `rol === 'cliente'`. Badges de inasistencias (ámbar) y Bloqueado/Activo. Bloquear/desbloquear con modal de confirmación; actualiza el item localmente sin refetch.
- `Calendario.jsx` extendido con prop `permitirPasados` (false por defecto) para que el admin pueda consultar fechas pasadas.
- Botón del nombre en cabecera → `/mi-cuenta` (reutiliza `FormularioPerfil` y `FormularioPassword` ya implementados).

### Cambios de backend acompañando a Fase D

- `ServicioUpdate` acepta ahora `activo: bool | None` → permite reactivar servicios vía `PUT`.
- `GET /citas` admite parámetro opcional `?fecha=YYYY-MM-DD` → filtra agenda por día.
- Test `test_reactivar_servicio_via_put` y `test_listar_citas_filtro_fecha` añadidos.

### Correcciones frontend (pulido)

- **Calendario — bug "hoy" en columna errónea**: normalizado `hoy` a medianoche local (`new Date(y, m, d)` en lugar de `new Date()`) y cambiado `key` de celdas de `toISOString()` (UTC, desfasa en UTC+2) a componentes locales `${y}-${m+1}-${d}`. Elimina el desplazamiento de columna en horario de verano.
- **Iconos SVG inline**: sustituidos los emojis 📅 (botón calendario en TabAgenda) y 🙈/👁 (ver/ocultar contraseña en Login y FormularioPassword) por SVG `currentColor` sin librería. Respetan modo claro/oscuro y escalan con el tema.
- **Login — distinguir 5xx de 401**: añadido `else if (status >= 500)` → "Error en el servidor, inténtalo más tarde"; el 401 sigue mostrando "Email o contraseña incorrectos".

### Múltiples tramos por día (jornada partida)

- Eliminado `UniqueConstraint("dia_semana")` de `HorarioPeluquero`; migración `c70da527d6e9` aplica el `DROP CONSTRAINT` en la BD.
- `POST /horario` y `PUT /horario/{id}` validan solapamiento manualmente con `_validar_sin_solapamiento` (409 si los rangos se cruzan).
- `GET /disponibilidad` itera sobre **todos** los tramos del día (`.all()` + loop) y acumula los huecos disponibles de cada bloque.
- 3 tests nuevos en `test_horario.py`: tramos no solapados OK, solapamiento exacto rechazado, solapamiento parcial rechazado, disponibilidad con dos bloques.

## Pendiente — Despliegue

- Render: backend (Web Service de pago), PostgreSQL gestionada con backups, frontend (static site), variables de entorno y seed de admins en producción (con `VITE_API_URL` absoluta, contraseñas fuertes y las variables de **Telegram**).

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
- En dev, las llamadas a la API pasan por el **proxy de Vite** (`/api`).

---

## Siguiente paso

1. **Smoke test manual** de la Fase D (ver checklist en CLAUDE.md plan — D1 a D4 + móvil 375 px).
2. **Despliegue en Render**: backend (Web Service), PostgreSQL gestionada, frontend (static site), variables de entorno (`TELEGRAM_*`, `RETENCION_MESES`, seed admins con contraseñas fuertes), Cron Job para la purga.
