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
- **Autenticación:** JWT (enviado en cabecera `Authorization: Bearer`).
- **Rate limiting:** slowapi.
- **Tests:** pytest.
- **Hosting:** Render (backend como Web Service de pago, PostgreSQL gestionado con backups, frontend como static site).

**Modelo de concurrencia:** sin tiempo real. La disponibilidad se refresca al recargar la página. No usar WebSockets en la V1.

---

## Convenciones

- Nombres del dominio en **español** (`Usuario`, `Cita`, `Servicio`, etc.).
- Nada de credenciales ni secretos hardcodeados: todo por variables de entorno (`.env`).
- Cada endpoint nuevo debe ir acompañado de su test en `pytest`.
- En FastAPI, las rutas literales (p. ej. `/citas/mias`) se declaran **antes** que las rutas con parámetro (`/citas/{cita_id}`).
- Esquemas de entrada y de salida separados (p. ej. `CitaCreate` vs `CitaRead`).

---

## Roles y autenticación

Dos roles:

1. **admin** — el peluquero y el desarrollador. **Solo 2 cuentas, fijas.**
   - Se crean por *seed* (`seed.py` o migración). **No existe registro público de administradores.**
2. **cliente** — usuarios normales que reservan.
   - Se registran con: `email`, `password`, `telefono`, `nombre_completo`.

El endpoint público `/registro` **solo** puede crear usuarios con rol `cliente`.
Dependencias de seguridad: `get_usuario_actual`, `solo_admin`.

---

## Modelo de datos

- **Usuario**: `id`, `email` (único), `password_hash`, `telefono`, `nombre_completo`, `rol` (`'admin'` | `'cliente'`).
- **Servicio**: `id`, `nombre`, `duracion_minutos`, `precio`.
- **HorarioPeluquero**: días y tramos horarios de apertura.
- **Cita**: `id`, `cliente_id`, `servicio_id`, `fecha`, `hora_inicio`, `hora_fin`, `estado` (`'activa'` | `'cancelada'`).

**Duraciones:** franja base de **30 minutos**. Corte = 1 franja (30 min); tinte = 2 franjas (**60 min fijos** a efectos de disponibilidad).

---

## REGLA CRÍTICA: no permitir reservas duplicadas

La exclusividad del hueco la garantiza la **base de datos**, no el código de aplicación.

- **Índice único PARCIAL** sobre `(fecha, hora_inicio)` **solo para citas con `estado = 'activa'`** (`WHERE estado = 'activa'`).
  - Es parcial a propósito: así una cita **cancelada NO bloquea** que ese hueco se vuelva a reservar.
- Dos peticiones simultáneas: PostgreSQL acepta la primera y rechaza la segunda con error de integridad.
- El endpoint captura ese error y devuelve **`409 Conflict`**; el frontend muestra "ese hueco se acaba de ocupar, recarga la página".

---

## Lógica de disponibilidad

Huecos disponibles = tramos de `HorarioPeluquero` − citas activas, comprobando que la `duracion_minutos` del servicio **cabe entera** sin solaparse con la siguiente cita.

---

## Lógica de cancelación (casos límite a respetar)

- Cancelar = poner `estado = 'cancelada'` (no se borra la fila).
- Solo puede cancelar el **dueño** de la cita o un **admin**.
- No se puede cancelar una cita ya cancelada (idempotencia) ni una cita pasada.
- Al cancelar, el hueco queda libre gracias al índice único parcial.
- Antes de implementar esta lógica, razonar los casos límite con extended thinking (`ultrathink`) en Plan Mode.

---

## Fuera de alcance en la V1 (NO implementar todavía)

- Pagos online / pasarela de pago (pago presencial). Previsto para V2.
- Recordatorios por WhatsApp / SMS / email. Previsto para V2.
- Tiempo real / actualización en vivo del calendario.

---

## Seguridad (OWASP Top 10:2025)

**Control de acceso (riesgo nº1, prioritario):**
- Autorización **por objeto** en cada endpoint: verificar que el recurso pertenece al usuario que lo pide, o que es admin (defensa anti-IDOR). No basta con estar autenticado.
- El panel de admin se protege con `solo_admin` en el **backend**, no solo ocultando botones en el frontend.
- El `cliente_id` de una cita se deduce **del token**, nunca del cuerpo de la petición (anti mass-assignment). Un cliente nunca puede fijar su `rol` ni reservar a nombre de otro.

**Validación de entradas (anti-inyección):**
- Cada endpoint recibe un esquema Pydantic tipado y estricto (`EmailStr`, longitudes, regex en `telefono`, enteros para ids, enums para `rol`/`estado`). Entrada inválida → `422`.
- SQL Injection: usar siempre SQLAlchemy ORM con consultas parametrizadas. Nunca concatenar SQL.
- Reglas de negocio validadas en servidor (fecha futura, dentro de horario, servicio existente).

**Transporte y cabeceras:**
- HTTPS forzado (Render aporta el certificado). Cabecera `Strict-Transport-Security` (HSTS).
- Middleware de cabeceras de seguridad: `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Content-Security-Policy`, `frame-ancestors`.
- Manejo correcto de `X-Forwarded-Proto` (la app va tras el proxy de Render).
- Cookies (si las hay) con `Secure`, `HttpOnly`, `SameSite`.

**CSRF / XSS:**
- JWT en cabecera `Authorization: Bearer` (mitiga CSRF; el navegador no lo adjunta solo).
- XSS: React escapa por defecto; nunca usar `dangerouslySetInnerHTML`.

**Rate limiting (slowapi), por capas:**
- `/login` y `/registro`: estricto por IP (~5/min) contra fuerza bruta.
- `POST /citas` (reserva): por **usuario autenticado** (5–10/min + tope diario), respaldo por IP.
- Límite global por IP (~100/min). Respuesta `429` con `Retry-After`.

**Contraseñas y secretos:**
- Contraseñas hasheadas con `bcrypt`/`argon2` (passlib). Nunca en texto plano.
- Secretos (clave JWT, credenciales BD) solo en variables de entorno.

**Errores y datos personales (RGPD/LOPDGDD):**
- No filtrar stack traces al cliente: devolver `500` genérico, registrar el detalle en el log del servidor.
- No registrar datos personales ni contraseñas en los logs.
- Minimización de datos: guardar solo lo necesario.
- Poder exportar y borrar/anonimizar los datos de un cliente (derecho al olvido).

---

## Cómo debes trabajar (instrucciones para Claude Code)

- Trabaja **en Plan Mode primero**: propón el plan, espera aprobación, y solo entonces escribe código.
- Avanza por fases pequeñas y verificables.
- Escribe tests `pytest` para cada endpoint nuevo.
- Nunca metas secretos en el código.
- Si algo no está claro, **pregunta antes de inventar**.
