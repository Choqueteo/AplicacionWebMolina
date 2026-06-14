# CLAUDE.md — Gestor de Citas para Peluquería

> Archivo de contexto del proyecto para Claude Code.
> Lee este archivo antes de generar o modificar código. Respeta todas las decisiones aquí descritas.

---

## Contexto del proyecto

Aplicación web de gestión de citas para una **peluquería real** (un único peluquero).
Es un proyecto en producción, no un ejercicio de aprendizaje. Desarrollador único.

**Funcionalidades de la V1:**
- Registro e inicio de sesión de clientes.
- Catálogo de servicios con duraciones distintas (corte, tinte, etc.).
- Reserva de cita eligiendo servicio + fecha + hora disponible.
- Panel de administración para el peluquero (gestión de citas, servicios y horario).

---

## Stack tecnológico (fijado, no cambiar sin acordarlo)

- **Backend:** FastAPI (Python).
- **Frontend:** React con Vite.
- **Base de datos:** PostgreSQL.
- **ORM:** SQLAlchemy + migraciones con Alembic.
- **Validación:** Pydantic.
- **Autenticación:** JWT (cabecera `Authorization: Bearer`).
- **Rate limiting:** slowapi.
- **Tests:** pytest.
- **Hosting:** Render (backend Web Service de pago, PostgreSQL gestionado con backups, frontend static site).

**Modelo de concurrencia:** sin tiempo real. La disponibilidad se refresca al recargar la página. No usar WebSockets en la V1.

---

## Convenciones

- Nombres del dominio en **español** (`Usuario`, `Cita`, `Servicio`, etc.).
- Nada de credenciales ni secretos hardcodeados: todo por variables de entorno (`.env`).
- Cada endpoint nuevo va acompañado de su test en `pytest`.
- En FastAPI, rutas literales (`/citas/mias`) antes que rutas con parámetro (`/citas/{cita_id}`).
- Esquemas de entrada y salida separados (`CitaCreate` vs `CitaRead`).

---

## Roles y autenticación

1. **admin** — peluquero y desarrollador. **Solo 2 cuentas, fijas.** Se crean por *seed*. **No hay registro público de admins.**
2. **cliente** — se registra con `email`, `password`, `telefono`, `nombre_completo`.

El endpoint público `/registro` **solo** crea usuarios con rol `cliente`.
Dependencias de seguridad: `get_usuario_actual`, `solo_admin`.

---

## Modelo de datos (basado en FRANJAS de 30 min)

- **Usuario**: `id`, `email` (único), `password_hash`, `telefono`, `nombre_completo`, `rol` (`'admin'` | `'cliente'`).
- **Servicio**: `id`, `nombre`, `duracion_minutos` (múltiplo de 30), `precio`.
- **HorarioPeluquero**: días y tramos horarios de apertura.
- **Cita**: `id`, `cliente_id`, `servicio_id`, `fecha`, `hora_inicio`, `hora_fin`, `estado` (`'activa'` | `'cancelada'`). Es la cita lógica; se conserva para histórico y para mostrarla al cliente. `hora_fin` se deriva de `hora_inicio` + `duracion_minutos`.
- **FranjaOcupada**: `id`, `cita_id` (FK), `fecha`, `hora` (inicio de la franja de 30 min). Es la **ocupación real** y la fuente de verdad de la disponibilidad.

**Duraciones:** franja base de **30 minutos**. Corte = 30 min = 1 franja; tinte = 60 min = 2 franjas.

---

## REGLA CRÍTICA: no permitir reservas solapadas (modelo de franjas)

La unidad de ocupación es la **franja de 30 min**. Un servicio ocupa **N franjas consecutivas** (`N = duracion_minutos / 30`).

La exclusividad la garantiza un **`UNIQUE (fecha, hora)` en `FranjaOcupada`**: cada franja solo puede pertenecer a una cita.

- **Crear cita:** en **una sola transacción**, insertar la `Cita` + sus N filas de `FranjaOcupada` (una por cada franja de 30 min que ocupa). Si alguna franja ya existe → `IntegrityError` → **rollback de toda la transacción** → devolver **`409 Conflict`** → el frontend pide recargar.
- Esto impide solapamientos de cualquier duración automáticamente: un corte a las 10:30 chocaría con la franja de las 10:30 de un tinte de 10:00–11:00.
- **Concurrencia:** si dos peticiones piden la misma franja a la vez, el `UNIQUE` deja pasar a una y rechaza la otra. Seguro a nivel de base de datos.

---

## Lógica de disponibilidad

- Una franja `(fecha, hora)` está **libre** si no existe fila en `FranjaOcupada` para ella y cae dentro del `HorarioPeluquero`.
- Un servicio de N franjas es reservable a una hora dada si **las N franjas consecutivas** están todas libres y dentro del horario.

---

## Lógica de cancelación (casos límite a respetar)

- Cancelar = poner `estado = 'cancelada'` **y borrar sus filas de `FranjaOcupada`** (libera los huecos), todo en una transacción.
- La `Cita` permanece como histórico.
- Solo puede cancelar el **dueño** de la cita o un **admin**.
- No se puede cancelar una cita ya cancelada (idempotencia) ni una cita pasada.
- Antes de implementar esta lógica, razonar los casos límite con extended thinking (`ultrathink`) en Plan Mode.

---

## Fuera de alcance en la V1 (NO implementar todavía)

- Pagos online (pago presencial). V2.
- Recordatorios por WhatsApp / SMS / email. V2.
- Tiempo real / actualización en vivo del calendario.

---

## Seguridad (OWASP Top 10:2025)

**Control de acceso (prioritario):**
- Autorización **por objeto** en cada endpoint: verificar que el recurso pertenece al usuario que lo pide, o que es admin (anti-IDOR). No basta con estar autenticado.
- Panel de admin protegido con `solo_admin` en el **backend**, no solo ocultando botones.
- El `cliente_id` de una cita se deduce **del token**, nunca del cuerpo (anti mass-assignment). Un cliente nunca fija su `rol` ni reserva a nombre de otro.

**Validación de entradas (anti-inyección):**
- Esquema Pydantic tipado y estricto por endpoint (`EmailStr`, longitudes, regex en `telefono`, enteros en ids, enums en `rol`/`estado`). Inválido → `422`.
- SQL Injection: siempre SQLAlchemy ORM con consultas parametrizadas. Nunca concatenar SQL.
- Reglas de negocio validadas en servidor (fecha futura, dentro de horario, servicio existente).

**Transporte y cabeceras:**
- HTTPS forzado (Render aporta certificado). Cabecera HSTS (`Strict-Transport-Security`).
- Middleware de cabeceras: `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Content-Security-Policy`, `frame-ancestors`.
- Manejo correcto de `X-Forwarded-Proto` (la app va tras el proxy de Render).
- Cookies (si las hay): `Secure`, `HttpOnly`, `SameSite`.

**CSRF / XSS:**
- JWT en cabecera `Authorization: Bearer` (mitiga CSRF).
- React escapa por defecto; nunca usar `dangerouslySetInnerHTML`.

**Rate limiting (slowapi), por capas:**
- `/login` y `/registro`: estricto por IP (~5/min).
- `POST /citas`: por **usuario autenticado** (5–10/min + tope diario), respaldo por IP.
- Límite global por IP (~100/min). Respuesta `429` con `Retry-After`.

**Contraseñas y secretos:**
- Contraseñas hasheadas con `bcrypt`/`argon2` (passlib). Nunca en texto plano.
- Secretos solo en variables de entorno.

**Errores y datos personales (RGPD/LOPDGDD):**
- No filtrar stack traces al cliente: `500` genérico, detalle en el log del servidor.
- No registrar datos personales ni contraseñas en los logs.
- Minimización de datos: guardar solo lo necesario.
- Poder exportar y borrar/anonimizar los datos de un cliente (derecho al olvido).

---

## Cómo debes trabajar (instrucciones para Claude Code)

- **Plan Mode primero**: propón el plan, espera aprobación, y solo entonces escribe código.
- Avanza por fases pequeñas y verificables.
- Escribe tests `pytest` para cada endpoint nuevo.
- Nunca metas secretos en el código.
- Si algo no está claro, **pregunta antes de inventar**.
