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


def db_id(login):
    db = TestingSessionLocal()
    uid = db.query(Usuario).filter(Usuario.usuario == login).first().id
    db.close()
    return uid


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


def _abrir_hoy(client, token, fecha=None):
    from app.services.jornada_service import fecha_negocio
    from datetime import datetime

    hoy = (fecha or fecha_negocio(datetime.utcnow())).isoformat()
    r = client.post("/api/jornadas/abrir", headers=_headers(token), json={"fecha": hoy})
    assert r.status_code == 201, r.text
    return hoy


def _corte_simple(client, token, servicio_id):
    r = client.post("/api/cortes/", headers=_headers(token),
                    json={"servicio_id": servicio_id, "metodo_pago": "efectivo"})
    assert r.status_code == 201
    return r.json()["id"]


def _imputacion_de(db, uuid_val):
    from app.models.imputacion_corte import ImputacionMovimiento

    return db.query(ImputacionMovimiento).filter(ImputacionMovimiento.movimiento_uuid == uuid_val).first()


def test_abono_imputa_en_jornada_real_abierta(client):
    """T75 (RF-45): momento en jornada abierta → imputado allí."""
    from decimal import Decimal
    from app.models.servicio import Servicio as ServicioT75

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j75", Rol.ADMIN)
    _crear_usuario(db, "barb_j75", Rol.BARBERO)
    db.add(ServicioT75(nombre="Corte J75", descripcion="x", precio=Decimal("100.00"), duracion_minutos=30, activo=True))
    db.commit()
    servicio_id = db.query(ServicioT75).first().id
    db.close()
    hoy = _abrir_hoy(client, _token(client, "admin_j75"))
    corte_id = _corte_simple(client, _token(client, "barb_j75"), servicio_id)
    uuid_val = client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(_token(client, "barb_j75")),
        json={"concepto": "cliente", "importe": "40.00", "metodo_pago": "efectivo"},
    ).json()["uuid"]
    db = TestingSessionLocal()
    fila = _imputacion_de(db, uuid_val)
    assert fila is not None
    assert fila.estado.value == "imputado"
    assert fila.jornada_real.isoformat() == hoy
    db.close()


def test_real_cerrada_ajusta_a_abierta_actual(client):
    """T75 (RF-45): real cerrada + abierta actual → ajuste con referencia."""
    from datetime import datetime, timedelta
    from decimal import Decimal
    from app.models.servicio import Servicio as ServicioT75b

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j75b", Rol.ADMIN)
    _crear_usuario(db, "barb_j75b", Rol.BARBERO)
    db.add(ServicioT75b(nombre="Corte J75b", descripcion="x", precio=Decimal("100.00"), duracion_minutos=30, activo=True))
    db.commit()
    servicio_id = db.query(ServicioT75b).first().id
    db.close()
    token_admin = _token(client, "admin_j75b")
    ayer = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    assert client.post("/api/jornadas/abrir", headers=_headers(token_admin), json={"fecha": ayer}).status_code == 201
    assert client.post("/api/jornadas/cerrar", headers=_headers(token_admin), json={"fecha": ayer}).status_code == 200
    hoy = _abrir_hoy(client, token_admin)
    corte_id = _corte_simple(client, _token(client, "barb_j75b"), servicio_id)
    momento_ayer = f"{ayer}T10:00:00"
    uuid_val = client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(token_admin),
        json={"concepto": "cliente", "importe": "40.00", "metodo_pago": "efectivo", "momento_real": momento_ayer},
    ).json()["uuid"]
    db = TestingSessionLocal()
    fila = _imputacion_de(db, uuid_val)
    assert fila.estado.value == "imputado"
    assert fila.jornada_real.isoformat() == ayer
    assert fila.jornada_destino_id is not None
    from app.models.jornada_caja import JornadaCaja

    destino = db.query(JornadaCaja).filter(JornadaCaja.id == fila.jornada_destino_id).first()
    assert destino.fecha_negocio.isoformat() == hoy
    db.close()


def test_sin_abierta_pendiente_con_saldo(client):
    """T75 (RF-50): sin abierta → pendiente, el saldo igual se mueve, pide apertura."""
    from decimal import Decimal
    from app.models.servicio import Servicio as ServicioT75c

    db = TestingSessionLocal()
    _crear_usuario(db, "barb_j75c", Rol.BARBERO)
    db.add(ServicioT75c(nombre="Corte J75c", descripcion="x", precio=Decimal("100.00"), duracion_minutos=30, activo=True))
    db.commit()
    servicio_id = db.query(ServicioT75c).first().id
    db.close()
    token = _token(client, "barb_j75c")
    corte_id = _corte_simple(client, token, servicio_id)
    uuid_val = client.post(
        f"/api/cortes/{corte_id}/movimientos", headers=_headers(token),
        json={"concepto": "cliente", "importe": "40.00", "metodo_pago": "efectivo"},
    ).json()["uuid"]
    db = TestingSessionLocal()
    fila = _imputacion_de(db, uuid_val)
    assert fila.estado.value == "pendiente"
    assert fila.jornada_destino_id is None
    db.close()
    saldos = client.get(f"/api/cortes/{corte_id}/saldos", headers=_headers(token)).json()
    assert saldos["cliente"]["abonado"] == "40.00"


def test_una_sola_jornada_abierta(client):
    """T75: no hay dos abiertas a la vez; cerrar habilita abrir otra."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j75d", Rol.ADMIN)
    db.close()
    auth = _headers(_token(client, "admin_j75d"))
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-08"}).status_code == 201
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-09"}).status_code == 409
    assert client.post("/api/jornadas/cerrar", headers=auth, json={"fecha": "2026-10-08"}).status_code == 200
    assert client.post("/api/jornadas/abrir", headers=auth, json={"fecha": "2026-10-09"}).status_code == 201


def _servicio_y_usuarios(db, barbero, porcentaje="50", precio="100.00"):
    from decimal import Decimal
    from app.models.servicio import Servicio as ServicioT76

    _crear_usuario(db, barbero, Rol.BARBERO)
    db.query(Usuario).filter(Usuario.usuario == barbero).first().porcentaje_ganancia = Decimal(porcentaje)
    db.add(ServicioT76(nombre=f"Servicio {barbero}", descripcion="x", precio=Decimal(precio), duracion_minutos=30, activo=True))
    db.commit()
    return db.query(ServicioT76).filter(ServicioT76.nombre == f"Servicio {barbero}").first().id


def test_cierre_bloquea_cortes_para_barbero(client):
    """T76 (RF-24): incorporado al cierre → 409 barbero; admin con motivo → 200."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j76", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j76")
    db.close()
    auth_admin = _headers(_token(client, "admin_j76"))
    auth = _headers(_token(client, "barb_j76"))
    assert client.post("/api/jornadas/abrir", headers=auth_admin, json={"fecha": "2026-10-08"}).status_code == 201
    momento = "2026-10-08T10:00:00"
    corte_id = client.post("/api/cortes/", headers=auth_admin, json={
        "servicio_id": servicio_id, "metodo_pago": "efectivo",
        "barbero_id": db_id("barb_j76"), "momento_real": momento,
    }).json()["id"]
    assert client.post("/api/jornadas/cerrar", headers=auth_admin, json={"fecha": "2026-10-08"}).status_code == 200
    assert client.patch(f"/api/cortes/{corte_id}", json={"metodo_pago": "tarjeta"}, headers=auth).status_code == 409
    assert client.post(f"/api/cortes/{corte_id}/anular", json={}, headers=auth).status_code == 409
    r = client.patch(f"/api/cortes/{corte_id}", json={"metodo_pago": "tarjeta", "motivo": "ajuste"},
                     headers=auth_admin)
    assert r.status_code == 200


def test_tardio_vinculado_por_ajuste_sin_tocar_snapshot(client):
    """T76 (RF-49): aceptado tras el cierre → vinculado por ajuste, snapshot intacto."""
    import uuid as uuid_lib
    from app.models.jornada_caja import PertenenciaCierre

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j76b", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j76b")
    db.close()
    auth_admin = _headers(_token(client, "admin_j76b"))
    token = _token(client, "barb_j76b")
    assert client.post("/api/jornadas/abrir", headers=auth_admin, json={"fecha": "2026-10-08"}).status_code == 201
    assert client.post("/api/jornadas/cerrar", headers=auth_admin, json={"fecha": "2026-10-08"}).status_code == 200
    uuid_val = str(uuid_lib.uuid4())
    r = client.post("/api/sync/", headers=_headers(token), json={"operaciones": [{
        "id": uuid_val, "accion": "crear_corte_v2", "datos": {
            "operacion_uuid": uuid_val, "servicio_id": servicio_id,
            "metodo_pago": "efectivo", "modo_captura": "offline",
            "momento_real": "2026-10-08T10:00:00",
        },
    }]})
    assert r.json()["resultados"][0]["aceptada"] is True
    corte_id = r.json()["resultados"][0]["corte_id"]
    db = TestingSessionLocal()
    pertenencias = db.query(PertenenciaCierre).filter(PertenenciaCierre.corte_id == corte_id).all()
    assert len(pertenencias) == 1
    assert pertenencias[0].es_tardio is True
    assert pertenencias[0].precio == 100
    db.close()
    assert client.patch(f"/api/cortes/{corte_id}", json={"metodo_pago": "tarjeta"},
                        headers=_headers(token)).status_code == 409


def test_momento_sync_se_conserva(client):
    """T76 (RF-9/51): crear_corte_v2 conserva el momento real (no now)."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j76c", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j76c")
    db.close()
    token = _token(client, "barb_j76c")
    uuid_val = str(uuid_lib.uuid4())
    r = client.post("/api/sync/", headers=_headers(token), json={"operaciones": [{
        "id": uuid_val, "accion": "crear_corte_v2", "datos": {
            "operacion_uuid": uuid_val, "servicio_id": servicio_id,
            "metodo_pago": "efectivo", "modo_captura": "offline",
            "momento_real": "2020-05-05T10:00:00",
        },
    }]})
    corte_id = r.json()["resultados"][0]["corte_id"]
    detalle = client.get(f"/api/cortes/{corte_id}", headers=_headers(token)).json()
    assert detalle["fecha"].startswith("2020-05-05T10:00:00")


def test_cierre_legacy_no_bloquea(client):
    """T76: compartir fecha con un cierre legacy no es pertenencia (sin evidencia)."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j76d", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j76d")
    db.close()
    auth_admin = _headers(_token(client, "admin_j76d"))
    assert client.post("/api/cierre-caja/", headers=auth_admin, json={
        "fecha": "2026-10-08T10:00:00", "total_cortes": "100.00", "total_productos": "0.00",
        "total_consumibles": "0.00", "total_ingresos": "100.00", "total_gastos": "0.00",
        "total_en_caja": "100.00", "monto_retirado": "0.00",
    }).status_code in (200, 201)
    token = _token(client, "barb_j76d")
    corte_id = _corte_simple(client, token, servicio_id)
    assert client.patch(f"/api/cortes/{corte_id}", json={"metodo_pago": "tarjeta"},
                        headers=_headers(token)).status_code == 200


def test_resumen_separa_devengado_de_caja(client):
    """T77 (RF-45): servicios vs dinero cobrado/pagado por método."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j77", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j77")
    db.close()
    auth_admin = _headers(_token(client, "admin_j77"))
    hoy = _abrir_hoy(client, _token(client, "admin_j77"))
    token = _token(client, "barb_j77")
    corte_id = _corte_simple(client, token, servicio_id)
    assert client.post(f"/api/cortes/{corte_id}/movimientos", headers=_headers(token), json={
        "concepto": "cliente", "importe": "40.00", "metodo_pago": "tarjeta",
    }).status_code == 201
    r = client.get(f"/api/jornadas/resumen?fecha={hoy}", headers=auth_admin)
    assert r.status_code == 200
    data = r.json()
    assert data["devengado"]["cortes"] == 1
    assert data["devengado"]["total"] == "100.00"
    assert data["cobros"]["total"] == "40.00"
    assert data["cobros"]["por_metodo"]["tarjeta"] == "40.00"
    assert data["pagos"]["total"] == "0.00"


def test_correccion_sobre_cerrado_genera_ajuste(client):
    """T77 (RF-39): corregir corte de jornada cerrada deja ajuste sin mutar el cierre."""
    from app.models.jornada_caja import AjusteCierre, PertenenciaCierre

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j77b", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j77b")
    db.close()
    auth_admin = _headers(_token(client, "admin_j77b"))
    hoy = _abrir_hoy(client, _token(client, "admin_j77b"))
    token = _token(client, "barb_j77b")
    corte_id = _corte_simple(client, token, servicio_id)
    assert client.post("/api/jornadas/cerrar", headers=auth_admin, json={"fecha": hoy}).status_code == 200
    r = client.patch(f"/api/cortes/{corte_id}", json={"metodo_pago": "tarjeta", "motivo": "corrige método"},
                     headers=auth_admin)
    assert r.status_code == 200
    db = TestingSessionLocal()
    ajustes = db.query(AjusteCierre).filter(AjusteCierre.corte_id == corte_id).all()
    assert len(ajustes) == 1
    assert ajustes[0].tipo.value == "correccion"
    assert db.query(PertenenciaCierre).filter(PertenenciaCierre.corte_id == corte_id).count() == 1
    db.close()


def test_legacy_resumen_intacto(client):
    """T77 (RNF-3): el resumen legacy sigue respondiendo igual."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j77c", Rol.ADMIN)
    db.close()
    r = client.get("/api/cierre-caja/resumen/dia", headers=_headers(_token(client, "admin_j77c")))
    assert r.status_code == 200
    assert "total_cortes" in r.json()


def test_acumulados_dia_semana_mes(client):
    """T78 (RF-52): ventanas en jornada de negocio; comisiones por servicio, dinero aparte."""
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j78", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j78")
    db.close()
    auth_admin = _headers(_token(client, "admin_j78"))
    hoy = _abrir_hoy(client, _token(client, "admin_j78"))
    token = _token(client, "barb_j78")
    corte_id = _corte_simple(client, token, servicio_id)
    assert client.post(f"/api/cortes/{corte_id}/movimientos", headers=_headers(token), json={
        "concepto": "cliente", "importe": "40.00", "metodo_pago": "efectivo",
    }).status_code == 201
    for periodo in ("dia", "semana", "mes"):
        r = client.get(f"/api/jornadas/acumulados?periodo={periodo}&fecha={hoy}", headers=auth_admin)
        assert r.status_code == 200, periodo
        data = r.json()
        assert data["comisiones"]["devengada"] == "50.00", periodo
        assert data["comisiones"]["pendiente"] == "50.00", periodo
        assert data["cobros"]["neto"] == "40.00", periodo
    r = client.get(f"/api/jornadas/acumulados?periodo=total&fecha={hoy}", headers=auth_admin)
    assert r.json()["comisiones"]["devengada"] == "50.00"


def test_acumulados_separan_revision_y_desconocido(client):
    """T78 (RF-12/53): revisión y desconocidos fuera de confirmados."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j78b", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j78b")
    db.close()
    auth_admin = _headers(_token(client, "admin_j78b"))
    hoy = _abrir_hoy(client, _token(client, "admin_j78b"))
    token = _token(client, "barb_j78b")
    corte_id = _corte_simple(client, token, servicio_id)
    uuid_val = str(uuid_lib.uuid4())
    assert client.post("/api/sync/", headers=_headers(token), json={"operaciones": [{
        "id": uuid_val, "accion": "registrar_abono_v2", "datos": {
            "operacion_uuid": uuid_val, "corte_id": corte_id, "concepto": "cliente",
            "importe": "150.00", "metodo_pago": "efectivo", "modo_captura": "offline",
        },
    }]}).json()["resultados"][0]["estado"] == "revision"
    assert client.post(f"/api/cortes/{corte_id}/evidencia-financiera", headers=auth_admin, json={
        "concepto": "comision", "conocido": False, "evidencia": "legajo",
    }).status_code == 200
    r = client.get(f"/api/jornadas/acumulados?periodo=dia&fecha={hoy}", headers=auth_admin)
    data = r.json()
    assert data["revision"]["total"] == "150.00"
    assert data["revision"]["cantidad"] == 1
    assert data["comisiones"]["desconocida"] == "50.00"
    assert data["comisiones"]["devengada"] == "0.00"


def test_acumulados_resumenes_viejos_intactos(client):
    """T78 (RNF-3): resúmenes personales y reportes viejos intactos."""
    db = TestingSessionLocal()
    _crear_usuario(db, "barb_j78c", Rol.BARBERO)
    db.close()
    token = _token(client, "barb_j78c")
    assert client.get("/api/cortes/mi/resumen/dia", headers=_headers(token)).status_code == 200


def test_resumen_cerrada_usa_snapshot_congelado(client):
    """T77 (RF-39/45, agregado en revisión): cerrada responde con el snapshot.

    La corrección posterior genera ajuste sin mutar el devengado original.
    """
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_j77d", Rol.ADMIN)
    servicio_id = _servicio_y_usuarios(db, "barb_j77d")
    db.close()
    auth_admin = _headers(_token(client, "admin_j77d"))
    hoy = _abrir_hoy(client, _token(client, "admin_j77d"))
    token = _token(client, "barb_j77d")
    corte_id = _corte_simple(client, token, servicio_id)
    assert client.post("/api/jornadas/cerrar", headers=auth_admin, json={"fecha": hoy}).status_code == 200
    data = client.get(f"/api/jornadas/resumen?fecha={hoy}", headers=auth_admin).json()
    assert data["estado"] == "cerrada"
    assert data["devengado"] == {"cortes": 1, "total": "100.00"}
    assert data["ajustes"] == 0
    assert client.patch(f"/api/cortes/{corte_id}", json={"metodo_pago": "tarjeta", "motivo": "rev"},
                        headers=auth_admin).status_code == 200
    data2 = client.get(f"/api/jornadas/resumen?fecha={hoy}", headers=auth_admin).json()
    assert data2["devengado"] == {"cortes": 1, "total": "100.00"}
    assert data2["ajustes"] == 1


def test_jornadas_lecturas_solo_admin(client):
    """T74/T77 (RF-15, agregado en revisión): barbero recibe 403 en listado/resumen/acumulados."""
    db = TestingSessionLocal()
    _crear_usuario(db, "barb_j77e", Rol.BARBERO)
    db.close()
    auth = _headers(_token(client, "barb_j77e"))
    assert client.get("/api/jornadas", headers=auth).status_code == 403
    assert client.get("/api/jornadas/resumen?fecha=2026-10-08", headers=auth).status_code == 403
    assert client.get("/api/jornadas/acumulados?periodo=dia&fecha=2026-10-08", headers=auth).status_code == 403
