"""Jornadas de negocio (paquete 11, T74): zona, apertura y cierre admin."""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_jornadas.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def _crear_usuario(db, nombre, rol, password="pass123"):
    u = Usuario(
        nombre=nombre,
        apellido="Test",
        email=f"{nombre}@test.com",
        usuario=nombre,
        hashed_password=pwd_context.hash(password),
        rol=rol,
        porcentaje_ganancia=50,
        activo=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _token(client, usuario, password="pass123"):
    r = client.post("/api/auth/login", data={"username": usuario, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_fecha_negocio_zona_buenos_aires():
    """T74 (RNF-2): la jornada cambia a las 00:00 de Buenos Aires (UTC-3)."""
    from app.services.jornada_service import fecha_negocio

    assert fecha_negocio(datetime(2026, 10, 8, 2, 59)) == date(2026, 10, 7)
    assert fecha_negocio(datetime(2026, 10, 8, 3, 1)) == date(2026, 10, 8)


def test_abrir_jornada_admin(client):
    """T74: apertura explícita admin crea la jornada abierta."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j74", Rol.ADMIN)
    db.close()
    r = client.post("/api/jornadas/abrir", headers=_headers(_token(client, "admin_j74")),
                    json={"fecha": "2026-10-08"})
    assert r.status_code == 201
    assert r.json()["estado"] == "abierta"
    assert r.json()["fecha_negocio"] == "2026-10-08"


def test_abrir_duplicada_409_y_cierre_inmutable(client):
    """T74: segunda apertura → 409; cerrada no se reabre ni se cierra dos veces."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j74b", Rol.ADMIN)
    db.close()
    auth = _headers(_token(client, "admin_j74b"))
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-08"}).status_code == 201
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-08"}).status_code == 409
    r = client.post("/api/jornadas/cerrar", headers=auth, json={"fecha": "2026-10-08"})
    assert r.status_code == 200
    assert r.json()["estado"] == "cerrada"
    assert client.post("/api/jornadas/cerrar", headers=auth, json={"fecha": "2026-10-08"}).status_code == 409
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-08"}).status_code == 409


def test_barbero_no_abre_ni_cierra(client):
    """T74: apertura y cierre solo admin (403)."""
    db = TestingSessionLocal()
    _crear_usuario(db, "barb_j74", Rol.BARBERO)
    db.close()
    auth = _headers(_token(client, "barb_j74"))
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-08"}).status_code == 403
    assert client.post("/api/jornadas/cerrar", headers=auth, json={"fecha": "2026-10-08"}).status_code == 403
