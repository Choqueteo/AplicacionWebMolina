from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def get_real_ip(request: Request) -> str:
    """Extrae la IP real teniendo en cuenta el proxy inverso de Render."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_real_ip, default_limits=["100/minute"])


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

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
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
    # Oculta la documentación en producción para reducir superficie de ataque
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["infraestructura"])
def health():
    return {"status": "ok"}
