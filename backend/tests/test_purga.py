"""Tests del script de purga de citas."""
from datetime import date, time, timedelta

from app.models import Cita, EstadoCita, FranjaOcupada, Rol, Usuario
from app.security import hash_password
from scripts.purga_citas import purgar


def _cliente(db, email="purga@test.com"):
    u = Usuario(
        email=email,
        password_hash=hash_password("x"),
        telefono="600000099",
        nombre_completo="Purga Test",
        rol=Rol.cliente,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _cita(db, usuario, servicio, dias_atras: int, estado=EstadoCita.activa):
    fecha = date.today() - timedelta(days=dias_atras)
    c = Cita(
        cliente_id=usuario.id,
        servicio_id=servicio.id,
        fecha=fecha,
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=estado,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _franja(db, cita):
    f = FranjaOcupada(cita_id=cita.id, fecha=cita.fecha, hora=cita.hora_inicio)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_purga_borra_citas_antiguas(db_session, servicio_corte):
    """Citas cuya fecha es anterior al límite deben borrarse."""
    u = _cliente(db_session)
    # 2 años y 1 día atrás → supera la ventana de 24 meses
    cita = _cita(db_session, u, servicio_corte, dias_atras=365 * 2 + 1)

    limite = date.today() - timedelta(days=1)  # límite forzado: ayer
    n = purgar(db=db_session, _limite=limite)

    assert n == 1
    assert db_session.get(Cita, cita.id) is None


def test_purga_conserva_recientes(db_session, servicio_corte):
    """Citas dentro de la ventana no deben borrarse."""
    u = _cliente(db_session)
    cita = _cita(db_session, u, servicio_corte, dias_atras=10)

    limite = date.today() - timedelta(days=30)  # límite forzado: hace 30 días
    n = purgar(db=db_session, _limite=limite)

    assert n == 0
    assert db_session.get(Cita, cita.id) is not None


def test_purga_borra_franjas(db_session, servicio_corte):
    """La FranjaOcupada asociada a una cita antigua también debe borrarse."""
    u = _cliente(db_session)
    cita = _cita(db_session, u, servicio_corte, dias_atras=400)
    franja = _franja(db_session, cita)

    limite = date.today() - timedelta(days=1)
    purgar(db=db_session, _limite=limite)

    assert db_session.get(FranjaOcupada, franja.id) is None


def test_purga_dry_run(db_session, servicio_corte):
    """Con dry_run=True no se borra nada, pero devuelve el conteo correcto."""
    u = _cliente(db_session)
    _cita(db_session, u, servicio_corte, dias_atras=400)

    limite = date.today() - timedelta(days=1)
    n = purgar(dry_run=True, db=db_session, _limite=limite)

    assert n == 1
    # La cita sigue en la BD
    assert db_session.query(Cita).filter_by(cliente_id=u.id).count() == 1


def test_purga_no_afecta_contador(db_session, servicio_corte):
    """Purgar citas no_asistida antiguas no altera usuario.inasistencias."""
    u = _cliente(db_session)
    u.inasistencias = 3
    db_session.commit()

    # Cita no_asistida antigua
    _cita(db_session, u, servicio_corte, dias_atras=400, estado=EstadoCita.no_asistida)

    limite = date.today() - timedelta(days=1)
    purgar(db=db_session, _limite=limite)

    db_session.refresh(u)
    assert u.inasistencias == 3
