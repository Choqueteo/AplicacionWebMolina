# CLAUDE.md — Gestor de Citas Peluquería RM

> Archivo de contexto del proyecto para Claude Code. Léelo antes de generar o modificar código y respeta todas las decisiones.

---

## Contexto

App web de gestión de citas para una peluquería/barbería real ("RM — Peluquería · Barbería"), un único peluquero. Proyecto en producción, desarrollador único. **Uso principal en móvil**, pero responsiva.

---

## Stack (fijado)

- Backend: FastAPI (Python). Frontend: React + Vite. BD: PostgreSQL.
- ORM: SQLAlchemy + Alembic. Validación: Pydantic. Auth: JWT (cabecera `Authorization: Bearer`). Rate limiting: slowapi. Tests: pytest.
- Entorno local: PostgreSQL en contenedor Docker (docker-compose) + HeidiSQL.
- Hosting: Render (backend Web Service de pago, PostgreSQL gestionado con backups, frontend static site).
- Sin tiempo real: la disponibilidad se refresca al recargar.

---

## Convenciones

- Dominio en español (`Usuario`, `Cita`, `Servicio`...). Secretos solo en variables de entorno.
- Cada endpoint nuevo con su test pytest. Esquemas de entrada y salida separados.
- En FastAPI, rutas literales antes que rutas con parámetro.

---

## Roles y autenticación

- **admin**: peluquero y desarrollador. Solo 2 cuentas fijas, creadas por seed (env vars). No hay registro público de admins.
- **cliente**: se registra él mismo.

Registro de cliente (`POST /registro`, solo crea rol cliente; el rol nunca se acepta del body):
- `nombre_completo`: obligatorio. Validar que contenga **al menos nombre y apellido** (mínimo dos palabras), solo letras/espacios/guiones/acentos. (No se puede garantizar que sea real; esto solo rechaza basura.)
- `telefono`: obligatorio, formato válido. Sirve para **contactar** al cliente.
- `email`: obligatorio, válido y único.
- `password`: obligatorio, hasheado con bcrypt (passlib). Nunca en texto plano.

Dependencias de seguridad: `get_usuario_actual`, `solo_admin`.

---

## Modelo de datos (basado en FRANJAS de 30 min)

- **Usuario**: `id`, `email` (único), `password_hash`, `telefono`, `nombre_completo`, `rol` ('admin' | 'cliente'), `bloqueado` (bool, def. false).
- **Servicio**: `id`, `nombre`, `duracion_minutos` (múltiplo de 30), `precio`, `activo` (bool, borrado lógico).
- **HorarioPeluquero**: tramos de apertura por día (admite varios tramos/día, p. ej. 9:00–14:00 y 17:00–21:00). Validación de solapamiento en el router antes del commit.
- **Cita**: `id`, `cliente_id`, `servicio_id`, `fecha`, `hora_inicio`, `hora_fin`, `estado` ('activa' | 'cancelada' | 'no_asistida').
- **FranjaOcupada**: `id`, `cita_id` (FK), `fecha`, `hora`. Ocupación real; fuente de verdad de la disponibilidad.

Corte = 30 min = 1 franja. Tinte/mechas = 60 min = 2 franjas (siempre, sin reposo).

---

## REGLA CRÍTICA: no reservas solapadas

`UNIQUE (fecha, hora)` en `FranjaOcupada`: cada franja pertenece a una sola cita. Crear cita = insertar la Cita + sus N franjas en UNA transacción; si una franja ya existe -> IntegrityError -> rollback -> `409 Conflict` -> el frontend pide recargar. Concurrencia resuelta a nivel de BD.

---

## Disponibilidad

`GET /disponibilidad?fecha=&servicio_id=` devuelve SOLO las horas de inicio válidas para ese servicio: las N franjas consecutivas libres y dentro de un mismo tramo de apertura. Un tinte (60 min) solo ofrece inicios donde caben 2 franjas. Si la fecha es hoy, no se ofrecen horas pasadas. El frontend solo muestra esas horas reservables.

---

## Cancelación

`PATCH /citas/{id}/cancelar`: estado -> 'cancelada' Y borra sus franjas (libera huecos), en una transacción. Solo dueño o admin. No se cancela una pasada ni una ya cancelada.

---

## Inasistencias (no-show)

- `PATCH /citas/{id}/no-asistida`, solo admin: marca una cita PASADA y 'activa' como 'no_asistida'. No futuras, no canceladas, no ya marcadas. La marca es manual; la app no puede saber quién asistió.
- Contador de inasistencias: campo **almacenado** `inasistencias: int` (default 0) en `Usuario`. Se incrementa en la misma transacción que marca la cita. Visible para el admin. La migración `c7e4a1d9f2b3` backfilla el histórico existente al añadir la columna.
- Veto: campo `bloqueado` en Usuario, controlado por el admin. Si `bloqueado`, `POST /citas` devuelve 403. El cobro de inasistencias es presencial.

---

## Purga de citas antiguas (RGPD — minimización de datos)

- Script `backend/scripts/purga_citas.py`: borra citas cuya `fecha` sea anterior a la ventana de retención junto con sus `FranjaOcupada`. Idempotente.
- Ventana configurable: variable de entorno `RETENCION_MESES` (default 24 meses en `settings.retencion_meses`).
- Modo dry-run: `python scripts/purga_citas.py --dry-run` — cuenta sin borrar.
- Borrado real en transacción: primero `FranjaOcupada WHERE cita_id IN (...)`, luego `Cita`.
- El campo `inasistencias` almacenado garantiza que purgar citas `no_asistida` no pierde el histórico de vetos.
- Pensado para ejecutarse como **Render Cron Job** (diario o semanal). La configuración del cron se hace al desplegar en Render.

---

## Notificaciones al peluquero (Telegram)

El peluquero recibe un aviso por **Telegram** cuando un cliente **reserva** (`POST /citas` con éxito) o **cancela** una cita (`PATCH /citas/{id}/cancelar`, solo si cancela el cliente; no si cancela el propio admin).
- El envío ocurre **tras confirmar la transacción** en la BD y en **segundo plano** (`BackgroundTasks`). Si falla o tarda, la operación se completa igual: el aviso nunca bloquea ni ralentiza la reserva/cancelación; los fallos se capturan y registran (sin volcar datos personales ni el token en los logs).
- Mensaje **conciso y suficiente**: nombre del cliente, teléfono, servicio, fecha y hora, y la acción. Minimización de datos (RGPD).
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (del peluquero) en variables de entorno, nunca en el código. Si faltan, la app funciona igual (no envía; deja un aviso en el log).
- Es una notificación de salida hacia una sola persona, no un chat bidireccional.

## Estados de cita y su VISUALIZACIÓN (derivada — no hay paso de "confirmar")

El peluquero solo marca inasistencias; nunca confirma citas. La etiqueta mostrada se DERIVA de `estado` + fecha:
- 'activa' y futura -> "Reservada" / "Próxima".
- 'activa' y pasada (no marcada) -> "Realizada" (derivado: si no se marcó como inasistencia, se asume que vino).
- 'no_asistida' -> "No asistió".
- 'cancelada' -> "Cancelada".
NO usar nunca la etiqueta "Confirmada".

---

## Fuera de alcance en V1

- Pagos online (pago presencial). V2.
- Recordatorios WhatsApp/SMS. V2.
- Verificación del teléfono por SMS (OTP). V2 si hay abuso.
- Tiempo real / actualización en vivo.

---

## Notificaciones al peluquero (Telegram)

- Bot de Telegram → chat personal del peluquero. Solo salida (no responder al bot).
- Módulo: `app/notificaciones/telegram.py`, función `enviar_aviso_peluquero(mensaje: str)`.
- Variables de entorno: `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. Si alguna falta → warning en log y no envía (no rompe nada). Nunca en el código.
- Disparadores con `BackgroundTasks` (después del commit, sin bloquear la respuesta al cliente):
  - `POST /citas` éxito → "Nueva reserva" con nombre, teléfono, servicio, fecha y hora.
  - `PATCH /citas/{id}/cancelar` éxito **y quien cancela es el cliente** → "Cita cancelada por el cliente". Si cancela un admin → no se envía (ya lo sabe).
- Cualquier excepción en el envío se captura con `try/except Exception` y se registra como warning sin datos personales ni el token. La operación principal nunca falla por esto.
- `httpx.post` síncrono, timeout 5 s. Starlette lo ejecuta en thread pool (no bloquea el event loop).
- Tests: mockear `enviar_aviso_peluquero` en `app.routers.citas` para tests de endpoint; mockear `httpx.post` dentro del módulo para tests unitarios de la función.

---

## Seguridad (OWASP Top 10:2025)

- Control de acceso por objeto en cada endpoint (anti-IDOR). Panel admin protegido con `solo_admin` en el backend.
- `cliente_id` de una cita se toma del token, nunca del body (anti mass-assignment).
- Validación Pydantic estricta en todo endpoint (422 si inválido). SQLAlchemy ORM parametrizado (anti SQLi).
- HTTPS forzado (Render), HSTS y cabeceras de seguridad. JWT en cabecera (mitiga CSRF). React escapa por defecto (anti XSS); nunca dangerouslySetInnerHTML.
- Rate limiting: /login y /registro estricto por IP (~5/min); POST /citas por usuario (~5-10/min + tope diario).
- No filtrar stack traces (500 genérico). No registrar datos personales ni contraseñas. RGPD/LOPDGDD: minimización y derecho de borrado/anonimización.

---

## Frontend (React + Vite)

- **Mobile-first y responsiva** (uso principal en móvil).
- AuthContext (login/logout/usuario+rol). Rutas protegidas por rol (público / cliente / admin). Cliente HTTP centralizado con Bearer automático y manejo central de 401 (cerrar sesión -> login) y 409 ("ese hueco se acaba de ocupar, recarga").
- **Dos dashboards distintos**: cliente y admin.
- Pantallas: Login, Registro (nombre, apellidos, teléfono, email, contraseña), Reservar (mostrar solo horas válidas del servicio), Mis citas (con cancelar), Panel admin (agenda con estados derivados, marcar inasistencia, gestión de servicios y horario, bloquear clientes).

### Diseño visual (estética premium, paleta de la marca RM)
- Estética elegante/premium en **negro y oro**, con **modo claro y oscuro**.
- **Logo**: usar la imagen del logo RM (no texto). Necesita una versión con **fondo transparente** (PNG/SVG) para el modo claro.
- Tipografía con un toque serif para la marca/títulos; sans para el resto.
- **Micro-interacciones**: transiciones suaves, `:hover` en botones, animaciones de entrada sencillas. Con mesura y cuidando el rendimiento en móvil.

Paleta de referencia:
- Oscuro: fondo #0B0B0C, superficie #161618, texto crema #F2ECDD, texto sec. #9A958A.
- Claro: fondo #FBF8F1, superficie #FFFFFF, texto carbón #1A1814, texto sec. #6E665C.
- Oro: principal #D4B35A, brillante #EBC76C, oscuro (sobre claro) #9C7A2A / #B8923A.
- Semánticos: verde #3B6D11 / #EAF3DE, ámbar #854F0B / #FAEEDA, rojo #A32D2D / #FCEBEB.

---

## Cómo trabajar (Claude Code)

- Plan Mode primero: propón el plan, espera aprobación, luego codifica.
- Fases pequeñas y verificables. Tests pytest por endpoint. Nunca secretos en el código. Si algo no está claro, pregunta antes de inventar.
