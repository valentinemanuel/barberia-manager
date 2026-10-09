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
