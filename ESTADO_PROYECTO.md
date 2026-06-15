# Estado del proyecto — Gestor de Citas Peluquería RM

> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo.

## Qué es

App web de gestión de citas para una peluquería/barbería real (RM), un único peluquero. Stack: FastAPI + React (Vite) + PostgreSQL, desplegará en Render. Mobile-first. Desarrollador único.

## Backend — COMPLETADO (fases 1 a 7 + ajuste de validación de registro)

1. **Configuración y seguridad base**: estructura backend/frontend, venv y dependencias, git + .gitignore, .env, Alembic, FastAPI con middleware de cabeceras de seguridad (HSTS, etc.), CORS, slowapi con límite global, endpoint `/health`.
2. **Modelos y migración inicial**: Usuario, Servicio, HorarioPeluquero, Cita, FranjaOcupada. Modelo de franjas de 30 min con `UNIQUE(fecha, hora)` que impide solapamientos.
3. **Autenticación**: registro (solo clientes), login con JWT, dependencias `get_usuario_actual` y `solo_admin`, seed de los 2 admin desde variables de entorno.
4. **Servicios y horario**: CRUD de servicios (admin) con borrado lógico (`activo`); horario del peluquero con varios tramos por día.
5. **Disponibilidad y reserva**: `/disponibilidad` (solo horas válidas por servicio), `POST /citas` con transacción todo-o-nada y `409` ante solapamiento, lectura de citas (mías / por id con autorización por objeto / agenda admin), rate limit por usuario.
6. **Cancelación**: `PATCH /citas/{id}/cancelar`, libera franjas, solo dueño o admin, no pasadas ni ya canceladas.
7. **Inasistencias**: estado `no_asistida`, `PATCH /citas/{id}/no-asistida` (admin, solo citas pasadas activas), contador calculado por cliente, campo `bloqueado` en Usuario que impide reservar.
8. **Ajuste de validación de registro (hecho)**: `nombre_completo` exige al menos nombre y apellido (mínimo dos palabras; solo letras/espacios/guiones/apóstrofos/acentos; cada palabra ≥ 2 letras; se guarda normalizada). `telefono` obligatorio, formato España (9 dígitos, prefijo +34/0034 opcional), normalizado a formato canónico. Mensajes de error en español. Tests pytest añadidos.

Todo verificado en Swagger y con pytest (**61 tests en verde**). BD local en contenedor Docker (PostgreSQL) + HeidiSQL.

### Contrato de autenticación (confirmado, lo usa el frontend)

- `POST /login` → `{ access_token, token_type: "bearer" }` (solo el token).
- `GET /usuarios/me` → `{ id, email, telefono, nombre_completo, rol }`.
- Claims del JWT: `sub` (user_id), `rol`, `exp`.
- Estrategia del frontend: tras login se guarda el token y se llama a `GET /usuarios/me` para obtener usuario+rol. **No se decodifica el JWT en el cliente.**

## Frontend — Fase A COMPLETADA

Cimientos funcionales (sin estética premium todavía):

- Proyecto **Vite + React (JavaScript, no TypeScript)**. Dependencias: `react-router-dom`, `axios`.
- `VITE_API_URL` desde `.env.local` (fallback a `http://localhost:8000` en dev).
- **Cliente HTTP centralizado** (`src/api/client.js`): instancia única de axios; interceptor de request que inyecta `Authorization: Bearer`; manejo central de **401** (logout + redirección a `/login`, vía callback registrado por AuthContext, no en login fallido) y **409** (flag `error.isConflict` para la futura pantalla de reservar).
- **AuthContext** (`src/context/AuthContext.jsx`): estado usuario+rol, `cargando` para la rehidratación, `login`/`logout`, `useAuth()`. Token persistido en localStorage; rehidratación al montar vía `/usuarios/me`.
- **Rutas por rol** (`src/routes/PrivateRoute.jsx`): `RoleRoute` (y `PrivateRoute` para uso futuro). Raíz redirige según sesión/rol. Ruta comodín `*` → `/`.
- **Placeholders** mínimos: Login y Registro (funcionales, llaman a la API), DashboardCliente y PanelAdmin (texto + logout).
- **Prerrequisito aplicado**: `localhost:5173` añadido a `ALLOWED_ORIGINS` del backend para CORS en dev.
- Smoke test manual de 10 pasos pasado (incluye ruta inventada, acceso cruzado por rol, rehidratación y 401 forzado).

## Pendiente — Frontend

- **Fase B (siguiente)**: login y registro reales, ya con estética premium (negro/oro, modo claro/oscuro, logo, micro-interacciones).
- **Fase C**: dashboard del cliente (servicios, disponibilidad, reservar, mis citas, cancelar).
- **Fase D**: dashboard del admin (agenda, servicios, horario, marcar inasistencias, bloquear clientes).

## Pendiente — Despliegue

- Render: backend (Web Service de pago), PostgreSQL gestionado con backups, frontend (static site), variables de entorno y seed de admins en producción.

## Decisiones de diseño (ya acordadas)

- Estética **premium en negro y oro** (paleta del logo RM), con **modo claro y oscuro**.
- **Mobile-first** y responsiva.
- Mostrar el **logo** (imagen), no el texto "RM". Falta una versión del logo con **fondo transparente** (PNG/SVG) para el modo claro.
- **Estados de cita derivados** (no hay "Confirmada"): Reservada/Próxima, Realizada (derivada), No asistió, Cancelada.
- En reservar, mostrar **solo las horas que el servicio sí puede ocupar**.
- **Micro-interacciones**: transiciones, hover en botones, animaciones de entrada sencillas, con mesura.
- Registro con nombre, apellidos, teléfono (contacto obligatorio), email y contraseña. No se puede garantizar nombre real por software; red de seguridad = inasistencias + bloqueo; verificación SMS queda para V2.

### Decisiones técnicas del frontend (Fase A)

- **JavaScript** (no TypeScript).
- **axios** con interceptores para el manejo central de 401/409.
- **Token JWT en localStorage** (coherente con la auth por cabecera `Bearer`).
- Obtención del rol vía `GET /usuarios/me`, sin decodificar el JWT en cliente.

Mockups de dirección visual ya revisados y aprobados (login, reservar, mis citas, panel admin).

## Cuestiones abiertas para la Fase B

- ¿El logo es solo el monograma "RM" o incluye el texto completo "RM — Peluquería · Barbería"? (Afecta a la cabecera en móvil.)
- Conmutador claro/oscuro: ¿manual, automático según el sistema, o ambos?
- Tener en el repo la versión del logo con **fondo transparente** para el modo claro.
- En la pantalla real de registro, leer `detail[0].msg` para mostrar los mensajes de validación 422 (los de `nombre_completo`/`telefono`); el placeholder actual cae en un error genérico.

## Siguiente paso

Frontend **Fase B** (login y registro reales con estética premium), en Plan Mode.
