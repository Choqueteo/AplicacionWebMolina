# Estado del proyecto — Gestor de Citas Peluquería RM

> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo.

> **ESTADO ACTUAL: 🟢 EN PRODUCCIÓN** en **https://rmolinastyle.com** (API en **https://api.rmolinastyle.com**). El núcleo (revert a franjas de 30, ventana de 30 días, tope 5 h, fix de zona horaria) está **desplegado y verificado**. El último bloque (días cerrados + letra + recordatorio diario) está **implementado y con tests en verde**; ver "Despliegue" y "Pendientes" para el estado exacto del deploy.

## Qué es

App web de gestión de citas para una peluquería/barbería real (RM), un único peluquero. Stack: FastAPI + React (Vite, JS) + PostgreSQL, en Render. Mobile-first. Desarrollador único (AceitunoDev). Piloto gratuito; uso intensivo previsto en verano.

---

## Modelo de franjas y servicios (IMPORTANTE — hubo idas y vueltas)

- **Franjas de 30 min** (unidad atómica). Constante única **`FRANJA_MINUTOS = 30`** centralizada en `app/constants.py` y usada en TODA la lógica (disponibilidad, creación de franjas, validación de hora). Nunca hardcodear el valor.
- **Servicios**: `duracion_minutos` debe ser **múltiplo de 30 y ≤ 300 min (5 h)**. Constante **`DURACION_MAX_MINUTOS = 300`**. Validado en el `CheckConstraint` de la BD Y en los validators Pydantic.
- ⚠️ **Histórico**: hubo un experimento de franjas de 15 min (servicios de 15/45/75…) que se **revirtió** a 30 por petición del peluquero. La centralización en `FRANJA_MINUTOS` hizo el revert casi trivial. Lección: el tamaño de franja es propenso a cambiar → mantenerlo SIEMPRE en la constante.

---

## Backend — COMPLETADO

Fases base (config/seguridad, modelos, auth, servicios+horario, disponibilidad+reserva, cancelación, inasistencias, validación de registro, gestión de cuenta, Telegram, purga RGPD) — ya descritas en versiones anteriores. Novedades y estado consolidado:

1. **Auth**: `POST /login` (solo token) + `GET /usuarios/me` (datos+rol). Seed CREATE-IF-MISSING de 2 admins. Registro solo clientes.
2. **Servicios/horario**: CRUD servicios (borrado lógico, reactivable vía PUT), horario con **N tramos/día** (jornada partida).
3. **Disponibilidad y reserva**: `/disponibilidad` devuelve solo inicios válidos (N franjas de 30 consecutivas en un tramo). `POST /citas` transaccional, 409 ante solape.
4. **Ventana de reserva (`DIAS_MAX_RESERVA = 30`)**: solo se reserva en **[hoy, hoy+30]** (rodante, "hoy" en Europe/Madrid). `/disponibilidad` vacío fuera de ventana; `POST /citas` → 422 fuera de ventana.
5. **Días cerrados (`ExcepcionFecha`)**: el peluquero marca fechas concretas como cerradas sin tocar el horario semanal. Modelo con discriminador `tipo` (solo "cerrado" por ahora; **diseñado para extender a "horarios especiales por fecha" en el futuro**). Endpoints admin (listar / añadir / eliminar) — al añadir, **409 si la fecha ya tiene citas activas** (con conteo) o ya está cerrada. `GET /excepciones/proximas` para el calendario del cliente. Fecha cerrada → `/disponibilidad` vacío y `POST /citas` 422.
6. **Recordatorio diario por Telegram (cron)**: `scripts/recordatorio_diario.py`. **Cada día a las 22:00 (Europe/Madrid)** envía al peluquero un resumen de las citas del día siguiente. Se envía **SIEMPRE**: si no hay citas, lo indica; si hay, lista cada una con **hora y nombre**. Sin campo en BD (idempotencia por el horario fijo del cron). "Mañana" calculado en Europe/Madrid (no depende de la hora UTC del cron). Reutiliza el helper `enviar_aviso_peluquero`.
7. **Avisos instantáneos Telegram** (existentes): al reservar/cancelar (cliente) en `BackgroundTasks`.
8. **Purga RGPD**: `scripts/purga_citas.py` (ventana 24 meses) — implementado, **cron NO programado** (innecesario en un piloto corto).

**~127 tests pytest en verde** (los del experimento de 15 min se revirtieron; añadidos los de tope 300, días cerrados y recordatorio).

### Zona horaria — BUG IMPORTANTE YA CORREGIDO
Hubo un bug en producción: `/disponibilidad` y `POST /citas` usaban referencias de "hoy" distintas (una en UTC), de modo que una hora válida del tramo para HOY se ofrecía como disponible pero al reservar daba **422 "fuera de horario"**. Se unificó el uso de **Europe/Madrid** en ambos endpoints. **Lección**: toda lógica de fecha/hora ("hoy", día de la semana, filtros) debe usar la MISMA zona (Europe/Madrid) y de forma idéntica en todos los endpoints. Pendiente recomendado: un test que reserve a una hora válida **para HOY** (los tests reservaban en días futuros y no cazaron el bug).

### Cadena de migraciones Alembic (relevante)
… → `a1b2c3d4e5f6` (franja 15, del experimento) → `b2c3d4e5f6a1` (franja 30 + tope 300) → `c3d4e5f6a1b2` (tabla `excepcion_fecha`). El recordatorio **no** añadió migración.

---

## Frontend — COMPLETADO

Fases A–D completas (cimientos, login/registro, dashboard cliente, "Mi cuenta", panel admin) + novedades:

- **Calendario del cliente** (`Calendario.jsx`): deshabilita días **pasados**, **cerrados por horario**, **fuera de ventana (>hoy+30)** y **días cerrados (`ExcepcionFecha`)**. Fechas con componentes locales del `Date` (nunca `toISOString()`).
- **Panel admin (TabHorario)**: sección **"Días cerrados"** — añadir fecha (calendario), lista, quitar; aviso del 409 si la fecha tiene citas activas.
- **Crear servicio (TabServicios)**: desplegable de duración **30 min → 5 h** (30, 60, …, 300), default 30.
- **Tamaño de letra aumentado**: escala tipográfica subida en `theme.css` (cuerpo ~17-18px), respetando el mínimo de 16px en móvil (accesibilidad / evita zoom iOS).
- **Favicon**: monograma "RM" dorado sobre fondo oscuro — set completo (`favicon.svg`, PNGs, `apple-touch-icon.png`, `favicon.ico`, `site.webmanifest`). Funciona en escritorio y móvil.
- Estética premium negro/oro, modo claro/oscuro manual, tipografía self-hosted (Cormorant Garamond + Inter).

---

## Despliegue (Render + Cloudflare)

### Producción — en vivo
- **Frontend**: `https://rmolinastyle.com` (+ `www` → redirige al apex).
- **Backend/API**: `https://api.rmolinastyle.com`.
- URLs internas: `rm-backend-z7zb.onrender.com`, `rm-frontend-4wr6.onrender.com` (los nombres base estaban ocupados → sufijo).
- **Dominio**: `rmolinastyle.com` en **Cloudflare Registrar** (~10,46 $/año a coste, WHOIS privacy, auto-renew). DNS: 3 CNAME (`api`, `www`, `@`) en **"DNS only"**. HTTPS por Render.

### Piezas en Render
- `rm-backend` (web, Python, Starter, Frankfurt) — pre-deploy `alembic upgrade head && python seed.py`.
- `rm-frontend` (static site, Frankfurt) — rewrite SPA.
- `rm-postgres` (basic-256mb, Frankfurt, `ipAllowList: []`).
- **`rm-recordatorios` (cron, NUEVO)** — `schedule "0 20 * * *"` (20:00 UTC = 22:00 Madrid en verano), `python scripts/recordatorio_diario.py`.
- **Coste**: ~17,50 $/mes (backend + Postgres; frontend gratis) + el cron (coste mínimo por ejecución) + dominio ~10 €/año.

### ⚠️ Incidente de migración en producción (resuelto)
Al desplegar el tope de 300 min, el `CheckConstraint` nuevo (`≤300 AND mod 30`) **falló al crearse** porque existía en la BD un servicio que lo violaba (creado cuando la regla vieja no tenía máximo). Render abortó el deploy (la web siguió viva con la versión anterior). **Solución**: IP allowlist temporal + `UPDATE servicios SET duracion_minutos = 60 WHERE id = <ofensor>` + relanzar deploy. **Lección**: una migración que ENDURECE un constraint falla si hay filas que lo incumplen → revisar/corregir datos antes.

### Variables secretas
`SECRET_KEY` autogenerada; `DATABASE_URL` inyectada (normalizada a `postgresql+psycopg://`). Secretos `sync:false` (ADMIN*, TELEGRAM_*) introducidos a mano en el panel. ⚠️ **Los `sync:false` NO se comparten entre servicios**: el cron `rm-recordatorios` necesita sus PROPIOS `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en su panel (y todos los campos obligatorios de `Settings`: `SECRET_KEY`, etc.).

---

## Monitorización
- **BetterStack (uptime)**: monitor sobre `https://api.rmolinastyle.com/health` cada 3 min, **avisos por email**. En verde. (Plan free.)

---

## Cuentas admin
- `admin@rmolinastyle.com` y `peluquero@rmolinastyle.com`, ambas funcionando. (El login del peluquero falló al principio: era un **typo de un carácter** en la contraseña, no un problema de seed. Resuelto.)
- La cuenta de cliente registrada en pruebas es la **cuenta personal de Cristian** para pedir cita → NO se borra.

---

## Pendientes

1. **Confirmar/realizar el despliegue del último bloque** (días cerrados + letra + recordatorio) en un único push, si no se ha hecho ya. (El núcleo previo —revert/ventana/tope/zona horaria— ya está en producción.)
2. **Cron `rm-recordatorios`**: tras el deploy, meter `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (y los campos obligatorios de Settings) en SU panel; probar con **"Run now"** sin esperar a las 22:00.
3. **Cerrar el viernes 26** (y los días que el peluquero quiera) desde el panel → "Días cerrados".
4. **Configurar servicios y horario reales** con el peluquero (a su ritmo).
5. **Test de zona horaria**: añadir un test que reserve a hora válida **para HOY** (cubre el bug ya corregido).
6. **Sentry (backend)** — diferido (inversión de producto, no urgente para el piloto).
7. **Status page** `status.rmolinastyle.com` — diferida (cuando AceitunoDev tenga varios clientes).
8. **RGPD**: la purga periódica no aplica en un piloto corto (retención 24 meses). SÍ recordar **borrar/anonimizar los datos personales al apagar el piloto** (nombres, teléfonos, emails de clientes reales).

---

## Aprendizajes clave (para AceitunoDev)

- **Centralizar constantes** (`FRANJA_MINUTOS`, `DURACION_MAX_MINUTOS`, `DIAS_MAX_RESERVA`) y **modelos extensibles** (`ExcepcionFecha.tipo`) absorbe el cambio de requisitos del cliente con poco esfuerzo.
- **Zona horaria coherente** (Europe/Madrid) e IDÉNTICA en todos los endpoints de fecha/hora. Tener tests que cubran "hoy".
- **Migraciones que endurecen constraints** en producción: corregir los datos que los incumplen ANTES de migrar.
- **Render**: variables de entorno **por servicio** (los `sync:false` no se heredan); nombres de servicio pueden llevar sufijo; el cron corre en **UTC** (calcular fechas locales dentro del script).
- **Disciplina de despliegue**: agrupar cambios relacionados en un solo deploy; el pre-deploy fallido NO tumba la versión viva.
- **Continuidad**: `CLAUDE.md` como fuente de verdad para Claude Code (actualizar tras cada decisión); chats cortos por fase; este `ESTADO_PROYECTO.md` como memoria entre sesiones.

---

## Cómo se trabaja (metodología)
Planificación/revisión en el chat (Claude) → ejecución en Claude Code (VS Code, Plan Mode: propone plan → se revisa aquí → se aprueba → codifica). `CLAUDE.md` se actualiza aquí y Cristian lo reemplaza en el repo antes de lanzar cada fase. Tests pytest en verde antes de cada deploy.
