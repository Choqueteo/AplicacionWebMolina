# RM — Peluquería · Barbería · Gestor de citas

Aplicación web de reservas para una peluquería/barbería real con un único peluquero. Los clientes se registran y reservan, cancelan o reprograman sus citas desde el móvil. El peluquero gestiona la agenda, los servicios, el horario y los días cerrados desde un panel de administración, y recibe los avisos por Telegram.

**En producción:** [rmolinastyle.com](https://rmolinastyle.com) · API en `https://api.rmolinastyle.com`

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · PyJWT · bcrypt · slowapi |
| Frontend | React 19 · Vite · React Router · Axios · CSS Modules |
| Base de datos | PostgreSQL 16 (Docker en local, gestionada en Render) |
| Tests | pytest (SQLite en memoria, sin necesidad de Docker) |
| Hosting | Render (Frankfurt): Web Service + Static Site + PostgreSQL + Cron Job |
| DNS / dominio | Cloudflare |

---

## Funcionalidades

**Cliente**
- Registro con validación (nombre y apellido, teléfono, email) y consentimiento RGPD explícito.
- Reserva: calendario limitado a **[hoy, hoy + 30 días]** que deshabilita los días cerrados. Solo muestra las horas de inicio en las que cabe el servicio entero.
- Mis citas: cancelar y **reprogramar** (con al menos 24 h de antelación).
- Mi cuenta: editar perfil, cambiar contraseña, **exportar mis datos** (JSON) y **eliminar la cuenta** (se anonimiza).

**Administrador (peluquero)**
- Agenda con estados derivados: *Próxima*, *Realizada*, *No asistió* y *Cancelada*.
- Marcar inasistencias; contador de inasistencias por cliente; bloquear y desbloquear clientes.
- CRUD de servicios (de 30 min a 5 h, en pasos de 30 min; se desactivan en vez de borrarse).
- Horario semanal con varios tramos por día (jornada partida) y **días cerrados** por fecha concreta.

**Notificaciones (Telegram, solo al peluquero)**
- Aviso instantáneo cuando un cliente reserva, cancela o reprograma.
- Recordatorio diario a las 22:00 (Madrid) con las citas del día siguiente.

---

## Reglas de negocio clave

- **Franjas de 30 min.** La agenda se divide en franjas definidas en [`backend/app/constants.py`](backend/app/constants.py) (`FRANJA_MINUTOS`, `DURACION_MAX_MINUTOS = 300` y `DIAS_MAX_RESERVA = 30`). No escribas estos valores a mano en otras partes del código.
- **Sin solapes, garantizado por la BD.** Cada cita ocupa N filas en `franjas_ocupadas`, que tiene `UNIQUE (fecha, hora)`. La cita y sus franjas se insertan en una sola transacción; si hay colisión, se devuelve `409 Conflict`.
- **Zona horaria.** "Hoy", "mañana" y "ahora" se calculan siempre en `Europe/Madrid` y de la misma forma en todos los endpoints.
- **Estados de cita:** `activa`, `cancelada` y `no_asistida`. La etiqueta que se muestra depende del estado y de la fecha. No existe el estado "confirmada".

El detalle completo de las decisiones de diseño está en [`CLAUDE.md`](CLAUDE.md).

---

## Estructura

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # App FastAPI, middlewares (CORS, cabeceras de seguridad), routers
│   │   ├── config.py          # Settings (pydantic-settings, lee .env)
│   │   ├── constants.py       # FRANJA_MINUTOS, DIAS_MAX_RESERVA, DURACION_MAX_MINUTOS
│   │   ├── models.py          # Modelos SQLAlchemy
│   │   ├── schemas.py         # Esquemas Pydantic (entrada / salida separados)
│   │   ├── security.py        # JWT + bcrypt
│   │   ├── dependencies.py    # get_usuario_actual, solo_admin
│   │   ├── rate_limit.py
│   │   ├── notificaciones/    # Telegram
│   │   └── routers/           # auth, usuarios, servicios, horario, disponibilidad, citas, excepciones
│   ├── alembic/               # Migraciones
│   ├── scripts/
│   │   ├── recordatorio_diario.py   # Cron diario (Telegram)
│   │   └── purga_citas.py           # Purga RGPD de citas antiguas
│   ├── tests/                 # pytest
│   └── seed.py                # Crea las 2 cuentas admin si no existen
├── frontend/
│   └── src/
│       ├── api/client.js      # Axios con Bearer automático y manejo central de 401/409
│       ├── context/           # AuthContext, ThemeContext
│       ├── pages/             # Login, Registro, DashboardCliente, PanelAdmin, MiCuenta, páginas legales
│       ├── components/        # admin/, cliente/, cuenta/, layout/, ui/
│       └── styles/theme.css   # Paleta negro/oro, modo claro/oscuro, escala tipográfica
├── docker-compose.yaml        # PostgreSQL local
└── render.yaml                # Infraestructura de Render (Blueprint)
```

---

## Puesta en marcha en local

### Requisitos

- Python 3.12+
- Node.js 20+
- Docker (para PostgreSQL)

### 1. Base de datos

```bash
docker compose up -d
```

Levanta PostgreSQL 16 en `localhost:5432` (usuario `peluqueria`, contraseña `dev_local_2024`, BD `peluqueria`). Puedes conectarte con HeidiSQL o con cualquier otro cliente.

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env        # y edita los valores (ver "Variables de entorno")

alembic upgrade head           # crea el esquema
python seed.py                 # crea las 2 cuentas admin (idempotente)

uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Documentación interactiva (solo fuera de producción): `http://localhost:8000/docs` y `/redoc`
- Health check: `http://localhost:8000/health`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env           # VITE_API_URL=/api
npm run dev
```

La app queda en `http://localhost:5173`. En desarrollo, Vite redirige `/api/*` a `http://localhost:8000` (ver [`vite.config.js`](frontend/vite.config.js)), así que no hace falta configurar CORS.

> Para enseñar una demo desde el entorno local a través de un túnel de Cloudflare, sigue [`TUNEL_LOCAL.md`](TUNEL_LOCAL.md).

---

## Variables de entorno

**Backend** (`backend/.env`; la plantilla con comentarios está en [`.env.example`](.env.example)):

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+psycopg://…`. Si llega `postgres://` (como la inyecta Render), se normaliza sola. |
| `SECRET_KEY` | ✅ | Firma de los JWT. Genérala con `openssl rand -hex 32`. |
| `ALGORITHM` | | Por defecto `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Por defecto `10080` (7 días). |
| `ALLOWED_ORIGINS` | | Array JSON, p. ej. `["http://localhost:5173"]`. |
| `ENVIRONMENT` | | `development` o `production`. En producción se desactivan `/docs` y `/openapi.json` y se activa HSTS. |
| `RETENCION_MESES` | | Ventana de retención para `purga_citas.py` (por defecto `24`). |
| `ADMIN1_*`, `ADMIN2_*` | Para el seed | `EMAIL`, `PASSWORD`, `NOMBRE` y `TELEFONO` de las dos cuentas admin. La contraseña solo se usa al crear la cuenta. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | | Si faltan, no se envía ningún aviso y la app sigue funcionando. |

**Frontend** (`frontend/.env`):

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | `/api` en desarrollo (a través del proxy de Vite); `https://api.rmolinastyle.com` en producción. |

Los secretos nunca se suben al repositorio: `.env` está en `.gitignore`.

---

## Tests

```bash
cd backend
pytest
```

Los tests usan SQLite en memoria (ver [`tests/conftest.py`](backend/tests/conftest.py)), así que no necesitan Docker ni una base de datos levantada. Cada endpoint tiene sus tests: autenticación, citas, disponibilidad, reprogramación, días cerrados, horario, servicios, usuarios, RGPD, notificaciones, recordatorio diario y purga.

Lint del frontend:

```bash
cd frontend
npm run lint
```

---

## API (resumen)

| Método | Ruta | Acceso |
|---|---|---|
| `POST` | `/registro`, `/login` | Público (5/min por IP) |
| `GET` · `PATCH` · `DELETE` | `/usuarios/me` | Autenticado (`DELETE` anonimiza la cuenta) |
| `GET` | `/usuarios/me/datos` | Autenticado (exportación RGPD) |
| `PATCH` | `/usuarios/me/password` | Autenticado |
| `GET` | `/usuarios`, `/usuarios/{id}` | Admin |
| `PATCH` | `/usuarios/{id}/bloquear`, `/usuarios/{id}/desbloquear` | Admin |
| `GET` | `/servicios`, `/servicios/{id}` | Público |
| `POST` · `PUT` · `DELETE` | `/servicios[/{id}]` | Admin |
| `GET` | `/horario` | Público |
| `POST` · `PUT` · `DELETE` | `/horario[/{id}]` | Admin |
| `GET` | `/disponibilidad?fecha=&servicio_id=` | Público |
| `GET` | `/excepciones/proximas` | Público |
| `GET` · `POST` · `DELETE` | `/excepciones[/{id}]` | Admin |
| `POST` | `/citas` | Cliente (10/min y 50/día por usuario) |
| `GET` | `/citas/mias` | Cliente |
| `GET` | `/citas` | Admin |
| `GET` | `/citas/{id}` | Dueño o admin |
| `PATCH` | `/citas/{id}/cancelar`, `/citas/{id}/reprogramar` | Dueño o admin |
| `PATCH` | `/citas/{id}/no-asistida` | Admin |
| `GET` | `/health` | Público |

Con el backend en local, la especificación completa está en `/docs`.

---

## Despliegue

La infraestructura está declarada en [`render.yaml`](render.yaml) (Blueprint de Render, región Frankfurt):

| Servicio | Tipo | Detalles |
|---|---|---|
| `rm-backend` | Web Service (Starter) | Pre-deploy: `alembic upgrade head && python seed.py` · health check en `/health` |
| `rm-frontend` | Static Site | `npm run build` → `dist/`, con rewrite SPA a `index.html` |
| `rm-postgres` | PostgreSQL gestionada | Backups diarios · `ipAllowList: []` (solo acceso interno) |
| `rm-recordatorios` | Cron Job | `0 20 * * *` (UTC) → `python scripts/recordatorio_diario.py` |

Ten en cuenta que:
- Los secretos con `sync: false` se introducen a mano en el panel de Render **de cada servicio**. El cron necesita sus propios `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
- El `schedule` del cron está en UTC: `20:00 UTC` son las 22:00 en Madrid en horario de verano y las 21:00 en invierno.
- Si una migración endurece una restricción (`CHECK`, `UNIQUE`…), corrige antes los datos que la incumplan. Si no, el pre-deploy falla.

El paso a paso está en [`DESPLIEGUE_RENDER.md`](DESPLIEGUE_RENDER.md).

---

## Seguridad y cumplimiento

- JWT en la cabecera `Authorization: Bearer`, contraseñas con bcrypt y rate limiting en login, registro y reservas.
- Control de acceso por objeto en cada endpoint. El `cliente_id` y el rol se toman siempre del token, nunca del body.
- Cabeceras de seguridad: CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy` y HSTS en producción.
- Los errores 500 son genéricos y no devuelven el stack trace. No se registran datos personales en los logs.
- **RGPD / LOPDGDD / LSSI-CE:**
  - Páginas `/aviso-legal`, `/politica-privacidad` y `/politica-cookies`, enlazadas desde el footer.
  - Consentimiento con versión y fecha guardadas en la BD.
  - Exportación de datos y anonimización de la cuenta.
  - Purga de citas antiguas con `scripts/purga_citas.py [--dry-run]`.
  - Solo se usa almacenamiento técnico (el JWT en `localStorage`), así que no hace falta banner de cookies.
  - Las fuentes están alojadas en el propio servidor.

> Los textos legales contienen marcadores `[…]` que debe completar el titular del negocio.

---

## Documentación adicional

- [`CLAUDE.md`](CLAUDE.md): especificación y decisiones de diseño (fuente de verdad).
- [`ESTADO_PROYECTO.md`](ESTADO_PROYECTO.md): estado actual, incidentes y tareas pendientes.
- [`DESPLIEGUE_RENDER.md`](DESPLIEGUE_RENDER.md): guía de despliegue.
- [`TUNEL_LOCAL.md`](TUNEL_LOCAL.md): demo local con un túnel de Cloudflare.

---

Desarrollado por **AceitunoDev**.
