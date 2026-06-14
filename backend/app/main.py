from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.rate_limit import limiter
from app.routers import auth, citas, disponibilidad, horario, servicios

_STATIC_SWAGGER = Path(__file__).parent / "static" / "swagger-ui"
_STATIC_REDOC   = Path(__file__).parent / "static" / "redoc"


# ---------------------------------------------------------------------------
# Middlewares personalizados
# ---------------------------------------------------------------------------

class ProxySchemeMiddleware(BaseHTTPMiddleware):
    """Corrige request.scope['scheme'] cuando la app corre tras el proxy de Render."""

    async def dispatch(self, request: Request, call_next):
        if request.headers.get("X-Forwarded-Proto") == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras de seguridad OWASP en todas las respuestas."""

    _DOCS_PATHS = {"/docs", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        # /docs y /redoc en desarrollo necesitan inline scripts para inicializarse;
        # la CSP estricta los bloquea. Se omite el header solo en esas rutas en dev.
        is_dev_docs = (
            settings.environment != "production"
            and request.url.path in self._DOCS_PATHS
        )
        if not is_dev_docs:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none'"
            )
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Peluquería Molina API",
    docs_url=None,   # siempre desactivado — servimos /docs manualmente desde static local
    redoc_url=None,  # siempre desactivado — servimos /redoc manualmente desde static local
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)

# Slowapi
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# El orden importa: los middlewares se aplican de abajo a arriba
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ProxySchemeMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(servicios.router)
app.include_router(horario.router)
app.include_router(disponibilidad.router)
app.include_router(citas.router)

# ---------------------------------------------------------------------------
# Documentación interactiva local (solo en desarrollo)
# ---------------------------------------------------------------------------

if settings.environment != "production":
    app.mount(
        "/static/swagger-ui",
        StaticFiles(directory=str(_STATIC_SWAGGER)),
        name="swagger-ui-static",
    )
    app.mount(
        "/static/redoc",
        StaticFiles(directory=str(_STATIC_REDOC)),
        name="redoc-static",
    )

    @app.get("/docs", include_in_schema=False)
    def swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Peluquería Molina API — Swagger UI",
            swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    def redoc_html():
        return get_redoc_html(
            openapi_url="/openapi.json",
            title="Peluquería Molina API — ReDoc",
            redoc_js_url="/static/redoc/redoc.standalone.js",
            with_google_fonts=False,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["infraestructura"])
def health():
    return {"status": "ok"}
