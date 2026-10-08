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


# ---------- T51: camino v2 con UUID obligatoria + estados (RF-30/RF-32/RF-57) ----------

def _op_v2(uuid_val, servicio_id, metodo="efectivo", modo="offline"):
    datos = {"servicio_id": servicio_id, "metodo_pago": metodo, "modo_captura": modo}
    if uuid_val is not None:
        datos["operacion_uuid"] = uuid_val
    return {"id": uuid_val or "sin-uuid", "accion": "crear_corte_v2", "datos": datos}


def test_crear_corte_v2_sin_uuid_se_rechaza(client):
    """T51: v2 exige UUID; legacy `crear_corte` sin UUID sigue intacto."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_v2a", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_v2a")
    r = client.post(
        "/api/sync/",
        headers=_headers(token),
        json={"operaciones": [_op_v2(None, servicio.id)]},
    )
    assert r.status_code == 200
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 400
    # Legacy intacto: sin UUID por el camino viejo se acepta
    r2 = client.post(
        "/api/sync/",
        headers=_headers(token),
        json={"operaciones": [{
            "id": "op-legacy",
            "accion": "crear_corte",
            "datos": {"servicio_id": servicio.id, "metodo_pago": "efectivo"},
        }]},
    )
    assert r2.json()["resultados"][0]["aceptada"] is True
    db.close()


def test_crear_corte_v2_reintento_no_duplica_y_trae_mapping(client):
    """T51: misma UUID reenviada devuelve el mismo acuse sin crear otro corte."""
    import uuid as uuid_lib
    from app.models.corte import Corte

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_v2b", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_v2b")
    uuid_val = str(uuid_lib.uuid4())
    body = {"operaciones": [_op_v2(uuid_val, servicio.id)]}
    r1 = client.post("/api/sync/", headers=_headers(token), json=body)
    r2 = client.post("/api/sync/", headers=_headers(token), json=body)
    assert r1.json()["resultados"][0]["aceptada"] is True
    assert r2.json()["resultados"][0]["aceptada"] is True
    assert r1.json()["resultados"][0]["corte_id"] == r2.json()["resultados"][0]["corte_id"]
    assert r1.json()["resultados"][0]["estado"] == "aceptada"
    assert r1.json()["resultados"][0]["snapshot"]["precio"] == "100.00"
    db2 = TestingSessionLocal()
    assert db2.query(Corte).count() == 1
    db2.close()
    db.close()


def test_crear_corte_v2_conflicto_misma_uuid_distinto_payload_409(client):
    """T51: misma UUID con distinto contenido → 409 sin efecto."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_v2c", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_v2c")
    uuid_val = str(uuid_lib.uuid4())
    r1 = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_op_v2(uuid_val, servicio.id, metodo="efectivo")]},
    )
    assert r1.json()["resultados"][0]["aceptada"] is True
    r2 = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_op_v2(uuid_val, servicio.id, metodo="tarjeta")]},
    )
    resultado = r2.json()["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 409
    db.close()
