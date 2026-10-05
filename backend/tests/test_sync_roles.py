import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol
from app.models.servicio import Servicio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sync_roles.db"
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


def _crear_usuario(db, nombre, rol, password="pass123", activo=True):
    u = Usuario(
        nombre=nombre,
        apellido="Test",
        email=f"{nombre}@test.com",
        usuario=nombre,
        hashed_password=pwd_context.hash(password),
        rol=rol,
        porcentaje_ganancia=50,
        activo=activo,
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


def _crear_servicio(db):
    s = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ---------- T12: validación de rol al sincronizar offline (RF-17/18) ----------

def test_operacion_permitida_se_acepta(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barb1", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb1")
    r = client.post(
        "/api/sync/",
        headers=_headers(token),
        json={"operaciones": [{
            "id": "op-1",
            "accion": "crear_corte",
            "datos": {"servicio_id": servicio.id, "metodo_pago": "efectivo"},
        }]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["aceptadas"] == 1
    assert data["rechazadas"] == 0
    assert data["resultados"][0]["aceptada"] is True
    assert data["resultados"][0]["status_code"] == 201
    db.close()


def test_usuario_desactivado_offline_se_rechaza_con_409_y_notifica(client):
    """El barbero se desactiva mientras estaba offline: su cola se rechaza."""
    db = TestingSessionLocal()
    barbero = _crear_usuario(db, "barb_off", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_off")
    # Mientras estaba offline, un admin lo desactiva
    barbero.activo = False
    db.commit()
    r = client.post(
        "/api/sync/",
        headers=_headers(token),
        json={"operaciones": [{
            "id": "op-1",
            "accion": "crear_corte",
            "datos": {"servicio_id": servicio.id, "metodo_pago": "efectivo"},
        }]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["aceptadas"] == 0
    assert data["rechazadas"] == 1
    resultado = data["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 409
    assert resultado["motivo"] == "usuario_desactivado"
    assert resultado["notificacion"]
    db.close()


def test_rol_degradado_offline_rechaza_operacion_no_permitida(client):
    """Admin degradado a barbero mientras offline: sus ops admin se rechazan (409)."""
    db = TestingSessionLocal()
    usuario = _crear_usuario(db, "exadmin", Rol.ADMIN)
    token = _token(client, "exadmin")
    servicio = _crear_servicio(db)
    # Mientras estaba offline, lo degradan a barbero
    usuario.rol = Rol.BARBERO
    db.commit()
    r = client.post(
        "/api/sync/",
        headers=_headers(token),
        json={"operaciones": [
            {"id": "op-admin", "accion": "crear_servicio", "datos": {}},
            {"id": "op-ok", "accion": "crear_corte", "datos": {"servicio_id": servicio.id, "metodo_pago": "efectivo"}},
        ]},
    )
    assert r.status_code == 200
    data = r.json()
    por_id = {res["id"]: res for res in data["resultados"]}
    assert por_id["op-admin"]["aceptada"] is False
    assert por_id["op-admin"]["status_code"] == 409
    assert por_id["op-admin"]["motivo"] == "rol_no_permitido"
    assert por_id["op-admin"]["notificacion"]
    # La operación permitida para barbero sí se acepta
    assert por_id["op-ok"]["aceptada"] is True
    assert por_id["op-ok"]["status_code"] == 201
    db.close()
