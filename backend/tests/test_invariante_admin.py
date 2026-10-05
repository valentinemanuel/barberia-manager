import os
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.usuario import Usuario, Rol
from app.services.admin_service import (
    ACCION_DEGRADAR,
    ACCION_DESACTIVAR,
    ACCION_PROMOVER,
    contar_admins_activos,
    es_ultimo_admin,
    validar_cambio_admin,
    validar_y_aplicar_cambio_admin,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_invariante.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _crear_usuario(db, nombre, rol, activo=True):
    u = Usuario(
        nombre=nombre,
        apellido="Test",
        email=f"{nombre}@test.com",
        usuario=nombre,
        hashed_password="x",
        rol=rol,
        porcentaje_ganancia=50,
        activo=activo,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------- T5: unitarios ----------

def test_ultimo_admin_no_puede_ser_degradado(db):
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    assert es_ultimo_admin(db, admin) is True
    error = validar_cambio_admin(db, admin, ACCION_DEGRADAR, actor=admin)
    assert error is not None
    assert error["status_code"] == 409


def test_ultimo_admin_no_puede_ser_desactivado(db):
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    error = validar_cambio_admin(db, admin, ACCION_DESACTIVAR, actor=admin)
    assert error is not None
    assert error["status_code"] == 409


def test_segundo_admin_si_puede_ser_degradado(db):
    admin1 = _crear_usuario(db, "admin1", Rol.ADMIN)
    admin2 = _crear_usuario(db, "admin2", Rol.ADMIN)
    assert es_ultimo_admin(db, admin1) is False
    error = validar_cambio_admin(db, admin2, ACCION_DEGRADAR, actor=admin1)
    assert error is None


def test_admin_puede_degradarse_o_desactivarse_si_hay_otro_admin(db):
    admin1 = _crear_usuario(db, "admin1", Rol.ADMIN)
    _crear_usuario(db, "admin2", Rol.ADMIN)
    assert validar_cambio_admin(db, admin1, ACCION_DEGRADAR, actor=admin1) is None
    assert validar_cambio_admin(db, admin1, ACCION_DESACTIVAR, actor=admin1) is None


def test_segundo_admin_activo_si_puede_ser_degradado_y_queda_uno(db):
    admin1 = _crear_usuario(db, "admin1", Rol.ADMIN)
    admin2 = _crear_usuario(db, "admin2", Rol.ADMIN)
    error = validar_y_aplicar_cambio_admin(
        db, admin2, ACCION_DEGRADAR, actor=admin1, cambios={"rol": Rol.BARBERO}
    )
    assert error is None
    db.refresh(admin1)
    assert contar_admins_activos(db) == 1


def test_promover_a_admin_siempre_permitido(db):
    admin1 = _crear_usuario(db, "admin1", Rol.ADMIN)
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    assert validar_cambio_admin(db, barbero, ACCION_PROMOVER, actor=admin1) is None


def test_es_ultimo_admin_falso_para_barbero_o_inactivo(db):
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    inactivo = _crear_usuario(db, "admin_inactivo", Rol.ADMIN, activo=False)
    assert es_ultimo_admin(db, barbero) is False
    assert es_ultimo_admin(db, inactivo) is False


# ---------- T6: concurrencia ----------

def test_concurrencia_degradacion_dos_admins(db):
    """Dos peticiones concurrentes degradando cada una a un admin distinto:
    una debe responder 409 y al final debe quedar al menos un admin activo."""
    admin1 = _crear_usuario(db, "admin1", Rol.ADMIN)
    admin2 = _crear_usuario(db, "admin2", Rol.ADMIN)
    id1, id2 = admin1.id, admin2.id

    barrera = threading.Barrier(2)
    resultados = {}

    def degradar(nombre, usuario_id):
        session = TestingSessionLocal()
        try:
            usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
            actor = session.query(Usuario).filter(Usuario.rol == Rol.ADMIN).first()
            barrera.wait(timeout=10)
            error = validar_y_aplicar_cambio_admin(
                session, usuario, ACCION_DEGRADAR, actor=actor,
                cambios={"rol": Rol.BARBERO},
            )
            resultados[nombre] = error
        finally:
            session.close()

    t1 = threading.Thread(target=degradar, args=("t1", id1))
    t2 = threading.Thread(target=degradar, args=("t2", id2))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    errores = [r for r in resultados.values() if r is not None]
    exitos = [r for r in resultados.values() if r is None]

    assert len(exitos) == 1
    assert len(errores) == 1
    assert errores[0]["status_code"] == 409

    verificacion = TestingSessionLocal()
    try:
        assert contar_admins_activos(verificacion) >= 1
    finally:
        verificacion.close()
