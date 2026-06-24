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
- **Servicio**: `id`, `nombre`, `duracion_minutos` (**múltiplo de 30, máximo 300 min = 5 h**), `precio`, `activo` (bool, borrado lógico).
- **HorarioPeluquero**: tramos de apertura por día de la semana (admite varios tramos/día, p. ej. 9:00–14:00 y 17:00–21:00). Horario **recurrente semanal**.
- **Cita**: `id`, `cliente_id`, `servicio_id`, `fecha`, `hora_inicio`, `hora_fin`, `estado` ('activa' | 'cancelada' | 'no_asistida').
- **FranjaOcupada**: `id`, `cita_id` (FK), `fecha`, `hora`. Ocupación real; fuente de verdad de la disponibilidad. Los valores de `hora` caen en :00/:30.
- **ExcepcionHorario** (días cerrados): excepción por **fecha concreta** que tiene prioridad sobre el horario semanal. Ver sección "Excepciones de horario".

**Tamaño de franja = 30 min**, centralizado en UNA constante única (`FRANJA_MINUTOS = 30`) usada en TODA la lógica de franjas — nunca hardcodear el valor por el código. Nº de franjas de un servicio = `duracion_minutos / FRANJA_MINUTOS`. Duración máxima de un servicio = `DURACION_MAX_MINUTOS = 300` (5 h).

Ejemplos: corte 30 min = 1 franja · tinte 60 min = 2 franjas · servicio de 90 min = 3 franjas · … · servicio largo de 300 min (5 h) = 10 franjas. (Sin reposo entre franjas.)

---

## REGLA CRÍTICA: no reservas solapadas

`UNIQUE (fecha, hora)` en `FranjaOcupada`: cada franja pertenece a una sola cita. Crear cita = insertar la Cita + sus N franjas (de 30 min) en UNA transacción; si una franja ya existe -> IntegrityError -> rollback -> `409 Conflict` -> el frontend pide recargar. Concurrencia resuelta a nivel de BD.

---

## Disponibilidad

`GET /disponibilidad?fecha=&servicio_id=` devuelve SOLO las horas de inicio válidas para ese servicio: las **N franjas de 30 min consecutivas** libres y dentro de un mismo tramo de apertura (N = `duracion_minutos / FRANJA_MINUTOS`). Un servicio de 60 min solo ofrece inicios donde caben 2 franjas; uno de 5 h, donde caben 10 franjas seguidas. Si la fecha es hoy, no se ofrecen horas pasadas. Solo se ofrecen fechas **dentro de la ventana de reserva** y que **no sean un día cerrado** (ver secciones siguientes); en esos casos, sin horas. El frontend solo muestra esas horas reservables.

---

## Ventana de reserva (horizonte de días)

Un cliente solo puede reservar dentro de una ventana **rodante** de como máximo **`DIAS_MAX_RESERVA = 30`** días naturales desde hoy: rango **[hoy, hoy + 30 días]** (ambos inclusive). "Hoy" se calcula SIEMPRE en **Europe/Madrid**. Como se computa en cada petición, la ventana se desplaza sola con el paso de los días (sin cron). Objetivo: evitar reservas en fechas absurdamente lejanas.

- Constante única/configurable (`DIAS_MAX_RESERVA`), definida en el backend.
- **Backend (defensa real)**: `GET /disponibilidad` devuelve `horas_disponibles` vacío para fechas fuera de la ventana (no error). `POST /citas` rechaza con **422** (mensaje claro) si la fecha está fuera de `[hoy, hoy+DIAS_MAX_RESERVA]`.
- **Frontend**: el calendario de Reservar deshabilita los días fuera de la ventana (los pasados Y los posteriores a hoy+30). Construir fechas con componentes locales del `Date` (nunca `toISOString()`). Mantener el valor 30 en sintonía con el backend.

---

## Excepciones de horario (días cerrados)

El peluquero puede marcar **fechas concretas como cerradas** (vacaciones, festivo, un día suelto) SIN tocar el horario semanal recurrente — los demás días de esa misma semana siguen abiertos. Una fecha cerrada **tiene prioridad sobre el horario semanal**: ese día no hay disponibilidad aunque su día de la semana tenga tramos.

- **Modelo (`ExcepcionHorario`)**: excepción por **fecha** (solo la fecha, **sin campo motivo**). Diseñado para poder **extenderse en el futuro** a "horarios especiales por fecha" (un día con tramos distintos a los semanales): incluir un discriminador `tipo` que de momento es siempre "cerrado". **En esta fase SOLO se implementa el cierre de día completo**; no construir aún los horarios especiales.
- **Endpoints admin (`solo_admin`)**:
  - Listar días cerrados.
  - Añadir un día cerrado. **Si esa fecha YA tiene citas activas → RECHAZA con 409** y mensaje claro (cuántas citas hay); no se cierra un día por encima de citas vivas. El admin debe cancelarlas antes.
  - Eliminar un día cerrado.
- **Endpoint para el cliente**: forma (accesible a clientes autenticados) de obtener las fechas cerradas dentro de `[hoy, hoy+DIAS_MAX_RESERVA]`, para que el calendario las deshabilite.
- **Disponibilidad / reserva**: `GET /disponibilidad` para una fecha cerrada → `horas_disponibles` vacío. `POST /citas` para una fecha cerrada → **422** con mensaje claro.
- **Frontend**:
  - Panel admin (TabHorario): sección "Días cerrados" — añadir una fecha (calendario), lista de las cerradas, quitar cada una. Aviso (del 409) al intentar cerrar un día con citas activas.
  - Calendario del cliente: las fechas cerradas salen **deshabilitadas**, igual que los días sin horario / pasados / fuera de ventana.
- ⚠️ **Coherencia de zona horaria**: el chequeo de "día cerrado" usa Europe/Madrid y se aplica de forma **IDÉNTICA** en `/disponibilidad` y `POST /citas` (misma lección que el bug de tz ya corregido). Incluir test con "hoy cerrado".

---

## Cancelación

`PATCH /citas/{id}/cancelar`: estado -> 'cancelada' Y borra sus franjas (libera huecos), en una transacción. Solo dueño o admin. No se cancela una pasada ni una ya cancelada.

---

## Inasistencias (no-show)

- `PATCH /citas/{id}/no-asistida`, solo admin: marca una cita PASADA y 'activa' como 'no_asistida'. No futuras, no canceladas, no ya marcadas. La marca es manual; la app no puede saber quién asistió.
- Contador de inasistencias por cliente: visible para el admin (campo `Usuario.inasistencias`).
- Veto: campo `bloqueado` en Usuario, controlado por el admin. Si `bloqueado`, `POST /citas` devuelve 403. El cobro de inasistencias es presencial.

---

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
- Horarios especiales por fecha (un día con tramos distintos a los semanales): previsto a futuro; el modelo de ExcepcionHorario se diseña para soportarlo, pero NO se implementa todavía.

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
- Pantallas: Login, Registro (nombre, apellidos, teléfono, email, contraseña), Reservar (mostrar solo horas válidas del servicio; **calendario limitado a la ventana [hoy, hoy+30 días] y con los días cerrados deshabilitados**), Mis citas (con cancelar), Panel admin (agenda con estados derivados, marcar inasistencia, gestión de servicios y horario, **días cerrados**, bloquear clientes).
- **Crear servicio (admin)**: desplegable de duración de **30 min a 5 h en pasos de 30 min** (30, 60, 90, …, 300).
- **Formateo de duración**: mostrar bien duraciones largas con media hora: "30 min", "1 h", "1 h 30 min", "2 h 30 min", "5 h", etc.

### Diseño visual (estética premium, paleta de la marca RM)
- Estética elegante/premium en **negro y oro**, con **modo claro y oscuro**.
- **Logo**: usar la imagen del logo RM (no texto). Versión con **fondo transparente** (PNG/SVG). Favicon: monograma "RM" dorado sobre fondo oscuro (set completo SVG + PNG + apple-touch-icon + site.webmanifest).
- Tipografía con un toque serif para la marca/títulos (Cormorant Garamond); sans para el resto (Inter). Self-hosted (RGPD).
- **Micro-interacciones**: transiciones suaves, `:hover` en botones, animaciones de entrada sencillas. Con mesura y cuidando el rendimiento en móvil; respetar `prefers-reduced-motion`.

Paleta de referencia:
- Oscuro: fondo #0B0B0C, superficie #161618, texto crema #F2ECDD, texto sec. #9A958A.
- Claro: fondo #FBF8F1, superficie #FFFFFF, texto carbón #1A1814, texto sec. #6E665C.
- Oro: principal #D4B35A, brillante #EBC76C, oscuro (sobre claro) #9C7A2A / #B8923A.
- Semánticos: verde #3B6D11 / #EAF3DE, ámbar #854F0B / #FAEEDA, rojo #A32D2D / #FCEBEB.

---

## Cómo trabajar (Claude Code)

- Plan Mode primero: propón el plan, espera aprobación, luego codifica.
- Fases pequeñas y verificables. Tests pytest por endpoint. Nunca secretos en el código. Si algo no está claro, pregunta antes de inventar.
