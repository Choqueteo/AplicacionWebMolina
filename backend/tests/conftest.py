from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Cita, ExcepcionFecha, FranjaOcupada, HorarioPeluquero, Rol, Servicio, TipoExcepcion, Usuario
from app.security import create_access_token, hash_password


@pytest.fixture()
def db_session():
    # StaticPool: todas las operaciones comparten la misma conexión en memoria,
    # por lo que las tablas creadas son visibles desde los endpoints bajo test.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    with engine.connect() as conn:
        # usuarios: ORM directo (sin constraints problemáticas en SQLite)
        Usuario.__table__.create(bind=conn)

        # servicios: SQL raw — la CheckConstraint usa mod() que SQLite no tiene;
        # la validación equivalente la hace Pydantic en la capa de aplicación.
        conn.execute(text("""
            CREATE TABLE servicios (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre           VARCHAR(100) NOT NULL,
                duracion_minutos INTEGER NOT NULL,
                precio           NUMERIC(8,2) NOT NULL,
                activo           BOOLEAN NOT NULL DEFAULT 1
            )
        """))

        # horario_peluquero: ORM directo (constraints SQLite-compatibles)
        HorarioPeluquero.__table__.create(bind=conn)

        # citas: ORM directo (la CheckConstraint de estado es SQLite-compatible)
        Cita.__table__.create(bind=conn)

        # franja_ocupada: ORM directo — UNIQUE(fecha, hora) compatible con SQLite
        # Orden: después de citas porque tiene FK a citas.id
        FranjaOcupada.__table__.create(bind=conn)

        # excepcion_fecha: ORM directo (UNIQUE(fecha) compatible con SQLite)
        ExcepcionFecha.__table__.create(bind=conn)

        conn.commit()

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reinicia el almacenamiento del rate limiter antes de cada test para evitar falsos 429."""
    from app.rate_limit import limiter
    limiter._storage.reset()
    yield


# ---------------------------------------------------------------------------
# Fixtures de autenticación — generan JWT directamente (sin pasar por /login)
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_token(db_session):
    """Token JWT de admin generado directamente, sin pasar por /login (evita rate limiter)."""
    admin = Usuario(
        email="admin@test.com",
        password_hash=hash_password("adminpass123"),
        telefono="600000000",
        nombre_completo="Admin Test",
        rol=Rol.admin,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return create_access_token(admin.id, admin.rol.value)


@pytest.fixture()
def cliente_token(db_session):
    """Token JWT de cliente generado directamente, sin pasar por /registro ni /login (evita rate limiter)."""
    cliente = Usuario(
        email="cli@test.com",
        password_hash=hash_password("clientepass123"),
        telefono="600000001",
        nombre_completo="Cliente Test",
        rol=Rol.cliente,
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return create_access_token(cliente.id, cliente.rol.value)


# ---------------------------------------------------------------------------
# Fixtures auxiliares para tests de citas y disponibilidad
# ---------------------------------------------------------------------------

@pytest.fixture()
def fecha_test() -> date:
    """Mañana — siempre una fecha futura válida para reservas."""
    return date.today() + timedelta(days=1)


@pytest.fixture()
def servicio_corte(db_session) -> Servicio:
    """Servicio de 30 minutos activo."""
    s = Servicio(nombre="Corte", duracion_minutos=30, precio=Decimal("15.00"), activo=True)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture()
def servicio_tinte(db_session) -> Servicio:
    """Servicio de 60 minutos activo."""
    s = Servicio(nombre="Tinte", duracion_minutos=60, precio=Decimal("40.00"), activo=True)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s



@pytest.fixture()
def horario_dia(db_session, fecha_test) -> HorarioPeluquero:
    """Horario 09:00-18:00 para el día de la semana de fecha_test."""
    h = HorarioPeluquero(
        dia_semana=fecha_test.weekday(),
        hora_apertura=time(9, 0),
        hora_cierre=time(18, 0),
    )
    db_session.add(h)
    db_session.commit()
    db_session.refresh(h)
    return h
