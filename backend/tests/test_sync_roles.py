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


# ---------- T52: abonos offline a revisión (RF-38/RF-51) ----------

def _abono_v2(uuid_val, corte_id, concepto="cliente", importe="10.00", momento=None):
    datos = {
        "operacion_uuid": uuid_val,
        "corte_id": corte_id,
        "concepto": concepto,
        "importe": importe,
        "metodo_pago": "efectivo",
        "modo_captura": "offline",
    }
    if momento is not None:
        datos["momento_real"] = momento
    return {"id": uuid_val, "accion": "registrar_abono_v2", "datos": datos}


def test_abono_offline_exceso_a_revision_sin_mover_saldo(client):
    """T52 (RF-38): exceso offline conserva importe real en revisión; saldo intacto."""
    import uuid as uuid_lib
    from datetime import datetime

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_ab1", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_ab1")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    uuid_val = str(uuid_lib.uuid4())
    r = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_abono_v2(uuid_val, corte_id, importe="150.00")]},
    )
    resultado = r.json()["resultados"][0]
    assert resultado["estado"] == "revision"
    assert resultado["status_code"] == 202
    saldos = client.get(f"/api/cortes/{corte_id}/saldos", headers=_headers(token)).json()
    assert saldos["cliente"]["abonado"] == "0.00"
    assert saldos["cliente"]["restante"] == "100.00"
    db.close()


def test_abono_online_exceso_sigue_rechazado_400(client):
    """T52: regresión RF-41, el exceso online por POST se rechaza."""
    db = TestingSessionLocal()
    _crear_usuario(db, "barb_ab2", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_ab2")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    r = client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(token),
        json={"concepto": "cliente", "importe": "150.00", "metodo_pago": "efectivo"},
    )
    assert r.status_code == 400
    db.close()


def test_abono_offline_reloj_adelantado_a_revision(client):
    """T52 (RF-51): momento futuro (>5min) conserva operación en revisión."""
    import uuid as uuid_lib
    from datetime import datetime, timedelta

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_ab3", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_ab3")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    futuro = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    r = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_abono_v2(str(uuid_lib.uuid4()), corte_id, momento=futuro)]},
    )
    resultado = r.json()["resultados"][0]
    assert resultado["estado"] == "revision"
    assert resultado["status_code"] == 202
    db.close()


def test_abono_offline_momento_pasado_no_es_reloj(client):
    """RF-51: el atraso de sync no invalida; momento de hace 2h se acepta."""
    import uuid as uuid_lib
    from datetime import datetime, timedelta

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_ab4", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_ab4")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    pasado = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    r = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_abono_v2(str(uuid_lib.uuid4()), corte_id, importe="30.00", momento=pasado)]},
    )
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is True
    assert resultado["status_code"] == 201
    db.close()


def test_abono_v2_corte_inexistente_404_sin_aplicar(client):
    """T54 (RF-57): abono a corte inexistente se conserva sin aplicar (404)."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_ab5", Rol.BARBERO)
    _crear_servicio(db)
    token = _token(client, "barb_ab5")
    r = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_abono_v2(str(uuid_lib.uuid4()), 9999, importe="10.00")]},
    )
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 404
    db.close()


def test_abono_uuid_distinto_payload_409(client):
    """T86 (RF-32): misma UUID con distinto importe → 409, sin efecto."""
    import uuid as uuid_lib
    from app.models.finanzas_corte import MovimientoCorte as MovimientoT86b

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_t86", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_t86")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    db.close()
    uuid_val = str(uuid_lib.uuid4())
    r1 = client.post("/api/sync/", headers=_headers(token),
                     json={"operaciones": [_abono_v2(uuid_val, corte_id, importe="10.00")]})
    assert r1.json()["resultados"][0]["aceptada"] is True
    r2 = client.post("/api/sync/", headers=_headers(token),
                     json={"operaciones": [_abono_v2(uuid_val, corte_id, importe="20.00")]})
    resultado = r2.json()["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 409
    db = TestingSessionLocal()
    assert db.query(MovimientoT86b).filter(MovimientoT86b.uuid == uuid_val).count() == 1
    db.close()


def test_momento_iso_equivalente_mismo_hash(client):
    """T86: '10:00:00' y '10:00:00.000000' con misma UUID → un solo corte."""
    import uuid as uuid_lib
    from app.models.corte import Corte as CorteT86

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_t86m", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_t86m")
    db.close()
    uuid_val = str(uuid_lib.uuid4())
    for momento in ("2026-10-08T10:00:00", "2026-10-08T10:00:00.000000"):
        r = client.post("/api/sync/", headers=_headers(token), json={"operaciones": [{
            "id": uuid_val, "accion": "crear_corte_v2", "datos": {
                "operacion_uuid": uuid_val, "servicio_id": servicio.id,
                "metodo_pago": "efectivo", "modo_captura": "offline",
                "momento_real": momento,
            },
        }]})
        assert r.json()["resultados"][0]["aceptada"] is True
    db = TestingSessionLocal()
    assert db.query(CorteT86).count() == 1
    db.close()


def test_abono_v2_reintento_misma_uuid_no_duplica(client):
    """T52: misma UUID de abono reenviada no crea otro movimiento."""
    import uuid as uuid_lib
    from app.models.finanzas_corte import MovimientoCorte

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_ab4", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_ab4")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    body = {"operaciones": [_abono_v2(str(uuid_lib.uuid4()), corte_id, importe="10.00")]}
    client.post("/api/sync/", headers=_headers(token), json=body)
    client.post("/api/sync/", headers=_headers(token), json=body)
    db2 = TestingSessionLocal()
    assert db2.query(MovimientoCorte).filter(
        MovimientoCorte.corte_id == corte_id
    ).count() == 1
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


# ---------- T56: revalidación al sincronizar (RF-31/RF-34/RF-56) ----------

def test_sync_corte_servicio_desactivado_se_acepta_con_valores_actuales(client):
    """T56 (RF-31): desactivado después del registro offline no invalida."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_rv1", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_rv1")
    servicio.activo = False
    db.commit()
    r = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_op_v2(str(uuid_lib.uuid4()), servicio.id)]},
    )
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is True
    assert resultado["snapshot"]["precio"] == "100.00"
    db.close()


def test_sync_corte_servicio_inexistente_a_revision(client):
    """T56 (RF-56): sin valores recuperables → revisión, sin inventar nada."""
    import uuid as uuid_lib
    from app.models.corte import Corte

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_rv2", Rol.BARBERO)
    _crear_servicio(db)
    token = _token(client, "barb_rv2")
    r = client.post(
        "/api/sync/", headers=_headers(token),
        json={"operaciones": [_op_v2(str(uuid_lib.uuid4()), 9999)]},
    )
    resultado = r.json()["resultados"][0]
    assert resultado["estado"] == "revision"
    assert resultado["status_code"] == 202
    db2 = TestingSessionLocal()
    assert db2.query(Corte).count() == 0
    db2.close()
    db.close()


# ---------- T68: sync editar/anular + RF-40 (LWW offline e intervención) ----------

def _editar_v2(uuid_val, corte_id, cambios, instante="2026-10-08T10:00:00", motivo=None):
    datos = {
        "operacion_uuid": uuid_val,
        "corte_id": corte_id,
        "cambios": cambios,
        "instante_cambio": instante,
        "modo_captura": "offline",
    }
    if motivo is not None:
        datos["motivo"] = motivo
    return {"id": uuid_val, "accion": "editar_corte_v2", "datos": datos}


def test_sync_edicion_respeta_lww_con_bases_viejas(client):
    """T68 (RF-36): edición offline con instante anterior → omitida, sin pisar."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_e68", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_e68")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    db.close()
    r = client.patch(f"/api/cortes/{corte_id}", headers=_headers(token), json={
        "metodo_pago": "tarjeta", "instante_cambio": "2026-10-08T11:00:00",
    })
    assert r.json()["metodo_pago"] == "tarjeta"
    r = client.post("/api/sync/", headers=_headers(token), json={"operaciones": [
        _editar_v2(str(uuid_lib.uuid4()), corte_id, {"metodo_pago": "transferencia"},
                   instante="2026-10-08T10:00:00"),
    ]})
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is True
    assert resultado["unidades"]["metodo"] == "omitida"
    detalle = client.get(f"/api/cortes/{corte_id}", headers=_headers(token)).json()
    assert detalle["metodo_pago"] == "tarjeta"


def test_sync_edicion_tras_bloqueo_a_intervencion_sin_aplicar(client):
    """T68 (RF-40): llega tras el primer pago → 202 conservada, sin aplicar ni duplicar."""
    import uuid as uuid_lib
    from app.models.intervencion_corte import IntervencionCorte

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_e68b", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_e68b")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    db.close()
    assert client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(token),
        json={"concepto": "cliente", "importe": "10.00", "metodo_pago": "efectivo"},
    ).status_code == 201
    uuid_val = str(uuid_lib.uuid4())
    body = {"operaciones": [_editar_v2(uuid_val, corte_id, {"metodo_pago": "tarjeta"})]}
    r1 = client.post("/api/sync/", headers=_headers(token), json=body)
    r2 = client.post("/api/sync/", headers=_headers(token), json=body)
    assert r1.json()["resultados"][0]["estado"] == "pendiente_intervencion"
    assert r1.json()["resultados"][0]["status_code"] == 202
    assert r2.json()["resultados"][0]["estado"] == "pendiente_intervencion"
    detalle = client.get(f"/api/cortes/{corte_id}", headers=_headers(token)).json()
    assert detalle["metodo_pago"] == "efectivo"
    db = TestingSessionLocal()
    assert db.query(IntervencionCorte).filter(IntervencionCorte.uuid == uuid_val).count() == 1
    db.close()


def test_anulacion_no_autorizada_no_terminaliza(client):
    """T68 (RF-36/40): anular bloqueado como barbero → intervención; el corte sigue activo."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_e68c", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_e68c")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    db.close()
    assert client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(token),
        json={"concepto": "cliente", "importe": "10.00", "metodo_pago": "efectivo"},
    ).status_code == 201
    r = client.post("/api/sync/", headers=_headers(token), json={"operaciones": [{
        "id": "anula-1", "accion": "anular_corte_v2", "datos": {
            "operacion_uuid": str(uuid_lib.uuid4()), "corte_id": corte_id,
            "instante_cambio": "2026-10-08T10:00:00", "modo_captura": "offline",
        },
    }]})
    assert r.json()["resultados"][0]["estado"] == "pendiente_intervencion"
    detalle = client.get(f"/api/cortes/{corte_id}", headers=_headers(token)).json()
    assert detalle["anulado_en"] is None


def test_admin_resuelve_intervencion_aplicar_y_descartar(client):
    """T68: el admin aplica con motivo o descarta con motivo (revisión manual)."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_e68d", Rol.BARBERO)
    _crear_usuario(db, "admin_e68d", Rol.ADMIN)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_e68d")
    token_admin = _token(client, "admin_e68d")
    corte_id = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    ).json()["id"]
    db.close()
    assert client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(token),
        json={"concepto": "cliente", "importe": "10.00", "metodo_pago": "efectivo"},
    ).status_code == 201
    uuid_a = str(uuid_lib.uuid4())
    uuid_b = str(uuid_lib.uuid4())
    client.post("/api/sync/", headers=_headers(token), json={"operaciones": [
        _editar_v2(uuid_a, corte_id, {"metodo_pago": "tarjeta"}),
        _editar_v2(uuid_b, corte_id, {"metodo_pago": "transferencia"}),
    ]})
    auth_admin = {"Authorization": f"Bearer {token_admin}"}
    r = client.post(f"/api/cortes/intervenciones/{uuid_a}/resolver",
                    json={"decision": "aplicar", "motivo": "verificado"}, headers=auth_admin)
    assert r.status_code == 200
    assert r.json()["estado"] == "aplicada"
    r = client.post(f"/api/cortes/intervenciones/{uuid_b}/resolver",
                    json={"decision": "descartar", "motivo": "ya corregido"}, headers=auth_admin)
    assert r.status_code == 200
    assert r.json()["estado"] == "descartada"
    detalle = client.get(f"/api/cortes/{corte_id}", headers=_headers(token)).json()
    assert detalle["metodo_pago"] == "tarjeta"


def test_post_online_servicio_inactivo_sigue_400(client):
    """T56: el registro online nuevo solo ofrece servicios activos."""
    db = TestingSessionLocal()
    _crear_usuario(db, "barb_rv3", Rol.BARBERO)
    servicio = _crear_servicio(db)
    token = _token(client, "barb_rv3")
    servicio.activo = False
    db.commit()
    r = client.post(
        "/api/cortes/", headers=_headers(token),
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
    )
    assert r.status_code == 400
    db.close()
