"""Matriz de roles RF-1..RF-16 (Spec 000 — T13).

Cada test verifica una regla de la matriz rol × permiso de la spec.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol
from app.models.servicio import Servicio
from app.models.producto import Producto
from app.models.consumible import Consumible
from app.models.corte import Corte, MetodoPago

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_roles_permisos.db"
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


def _crear_usuario(db, nombre, rol, activo=True, password="pass123"):
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


def _crear_corte(db, barbero, servicio, precio=Decimal("100.00")):
    corte = Corte(
        barbero_id=barbero.id,
        servicio_id=servicio.id,
        precio=precio,
        porcentaje_barbero=Decimal("50.00"),
        parte_barbero=precio / 2,
        parte_barberia=precio / 2,
        metodo_pago=MetodoPago.EFECTIVO,
        fecha=datetime.utcnow(),
    )
    db.add(corte)
    db.commit()
    db.refresh(corte)
    return corte


# ---------- Gestión de usuarios (RF-1, RF-2, RF-3) ----------

def test_rf1_admin_crea_usuario(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    token = _token(client, "admin1")
    db.close()
    r = client.post("/api/usuarios/", json={
        "nombre": "Nuevo", "apellido": "Barbero", "email": "n@test.com",
        "usuario": "nuevousuario", "password": "pass123",
        "rol": "barbero", "porcentaje_ganancia": 50,
    }, headers=_headers(token))
    assert r.status_code == 201


def test_rf2_rol_elegido_se_asigna(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    token = _token(client, "admin1")
    db.close()
    r = client.post("/api/usuarios/", json={
        "nombre": "Nuevo", "apellido": "Admin", "email": "n2@test.com",
        "usuario": "nuevoadmin", "password": "pass123",
        "rol": "admin", "porcentaje_ganancia": 50,
    }, headers=_headers(token))
    assert r.status_code == 201
    assert r.json()["rol"] == "admin"


def test_rf3_barbero_no_crea_usuarios_403(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    token = _token(client, "barbero1")
    db.close()
    r = client.post("/api/usuarios/", json={
        "nombre": "X", "apellido": "Y", "email": "x@test.com",
        "usuario": "usuario_x", "password": "pass123",
        "rol": "barbero", "porcentaje_ganancia": 50,
    }, headers=_headers(token))
    assert r.status_code == 403


def test_rf3_barbero_no_modifica_ni_desactiva_usuarios_403(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    objetivo = _crear_usuario(db, "barbero2", Rol.BARBERO)
    objetivo_id = objetivo.id
    token = _token(client, "barbero1")
    db.close()
    r1 = client.put(f"/api/usuarios/{objetivo_id}", json={"activo": False}, headers=_headers(token))
    r2 = client.delete(f"/api/usuarios/{objetivo_id}", headers=_headers(token))
    assert r1.status_code == 403
    assert r2.status_code == 403


# ---------- Invariante del administrador (RF-4, RF-4b, RF-5, RF-6) ----------

def test_rf4_degradar_ultimo_admin_409(client):
    db = TestingSessionLocal()
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    admin_id = admin.id
    token = _token(client, "admin1")
    db.close()
    r = client.put(f"/api/usuarios/{admin_id}", json={"rol": "barbero"}, headers=_headers(token))
    assert r.status_code == 409


def test_rf4_desactivar_ultimo_admin_409(client):
    db = TestingSessionLocal()
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    admin_id = admin.id
    token = _token(client, "admin1")
    db.close()
    r = client.put(f"/api/usuarios/{admin_id}", json={"activo": False}, headers=_headers(token))
    assert r.status_code == 409


def test_rf4b_admin_se_auto_desactiva_con_otro_admin_200(client):
    db = TestingSessionLocal()
    admin1 = _crear_usuario(db, "admin1", Rol.ADMIN)
    _crear_usuario(db, "admin2", Rol.ADMIN)
    admin1_id = admin1.id
    token = _token(client, "admin1")
    db.close()
    r = client.put(f"/api/usuarios/{admin1_id}", json={"activo": False}, headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["activo"] is False


def test_rf5_degradar_otro_admin_con_otro_activo_permitido(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    admin2 = _crear_usuario(db, "admin2", Rol.ADMIN)
    _crear_usuario(db, "admin3", Rol.ADMIN)
    admin2_id = admin2.id
    token = _token(client, "admin1")
    db.close()
    r = client.put(f"/api/usuarios/{admin2_id}", json={"rol": "barbero"}, headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["rol"] == "barbero"


def test_rf6_promover_a_admin_200(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    barbero_id = barbero.id
    token = _token(client, "admin1")
    db.close()
    r = client.put(f"/api/usuarios/{barbero_id}", json={"rol": "admin"}, headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["rol"] == "admin"


# ---------- Barbero: privacidad (RF-7, RF-8, RF-9, RF-10, RF-11) ----------

def test_rf7_catalogo_solo_precio_venta(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    db.add(Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True))
    db.add(Producto(nombre="Gel", precio=Decimal("50.00"), stock=10, activo=True))
    db.add(Consumible(nombre="Navaja", precio=Decimal("20.00"), stock=10, activo=True))
    db.commit()
    token = _token(client, "barbero1")
    db.close()
    prohibidos = ("costo", "margen", "utilidad", "ganancia_bruta", "precio_compra")
    for ruta in ("/api/servicios/", "/api/productos/", "/api/consumibles/"):
        r = client.get(ruta, headers=_headers(token))
        assert r.status_code == 200
        assert len(r.json()) > 0
        for item in r.json():
            for campo in item:
                assert not any(p in campo.lower() for p in prohibidos), f"{ruta} expone {campo}"
            assert "precio" in item


def test_rf9_barbero_no_ve_corte_ajeno_404(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barbero1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barbero2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    corte_ajeno = _crear_corte(db, barbero2, servicio)
    corte_ajeno_id = corte_ajeno.id
    token = _token(client, "barbero1")
    db.close()
    r = client.get(f"/api/cortes/{corte_ajeno_id}", headers=_headers(token))
    assert r.status_code == 404


def test_rf11_barbero_solo_consulta_sus_cortes(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barbero1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barbero2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero2, servicio)
    barbero1_id = barbero1.id
    token = _token(client, "barbero1")
    db.close()
    r = client.get("/api/cortes/mi/historial", headers=_headers(token))
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 1
    assert datos[0]["barbero_id"] == barbero1_id


def test_rf8_resumen_barbero_solo_agregados_propios(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barbero1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barbero2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero2, servicio)
    token = _token(client, "barbero1")
    db.close()
    r = client.get("/api/cortes/mi/resumen/dia", headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["total_cortes"] == 2


# ---------- Admin también barbero (RF-12) ----------

def test_rf12_admin_ve_solo_lo_propio_en_mi(client):
    db = TestingSessionLocal()
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    _crear_corte(db, admin, servicio)
    _crear_corte(db, barbero, servicio)
    admin_id = admin.id
    token = _token(client, "admin1")
    db.close()
    r = client.get("/api/cortes/mi/historial", headers=_headers(token))
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 1
    assert datos[0]["barbero_id"] == admin_id


# ---------- Auditoría (RF-14) ----------

def test_rf14_auditoria_admin_200_barbero_403(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    db.close()
    token_admin = _token(client, "admin1")
    token_barbero = _token(client, "barbero1")
    r_admin = client.get("/api/auditoria/", headers=_headers(token_admin))
    r_barbero = client.get("/api/auditoria/", headers=_headers(token_barbero))
    assert r_admin.status_code == 200
    assert r_barbero.status_code == 403


# ---------- Reportes (RF-14b, RF-7) ----------

def test_rf14b_reportes_solo_admin(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    db.close()
    token_barbero = _token(client, "barbero1")
    r = client.get("/api/reportes/dashboard", headers=_headers(token_barbero))
    assert r.status_code == 403


# ---------- Gastos / cierre de caja / catálogo admin (matriz) ----------

def test_matriz_gastos_y_cierre_solo_admin(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    db.close()
    token_barbero = _token(client, "barbero1")
    assert client.get("/api/gastos/", headers=_headers(token_barbero)).status_code == 403
    assert client.get("/api/cierre-caja/", headers=_headers(token_barbero)).status_code == 403


def test_matriz_crud_catalogo_solo_admin(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    db.close()
    token_admin = _token(client, "admin1")
    token_barbero = _token(client, "barbero1")
    body = {"nombre": "Corte", "precio": 100, "duracion_minutos": 30}
    assert client.post("/api/servicios/", json=body, headers=_headers(token_barbero)).status_code == 403
    assert client.post("/api/servicios/", json=body, headers=_headers(token_admin)).status_code == 201


# ---------- Autorización con rol de DB (RF-15, RF-16) ----------

def test_rf15_token_con_claim_admin_pero_degradado_usa_rol_db(client):
    db = TestingSessionLocal()
    admin2 = _crear_usuario(db, "admin2", Rol.ADMIN)
    usuario = _crear_usuario(db, "admin1", Rol.ADMIN)
    token = _token(client, "admin1")  # claim rol=admin
    usuario.rol = Rol.BARBERO
    db.commit()
    db.close()
    r = client.get("/api/usuarios/", headers=_headers(token))
    assert r.status_code == 403


def test_rf16_usuario_desactivado_reciba_error_inmediato(client):
    db = TestingSessionLocal()
    usuario = _crear_usuario(db, "barbero1", Rol.BARBERO)
    token = _token(client, "barbero1")
    usuario.activo = False
    db.commit()
    db.close()
    r = client.get("/api/servicios/", headers=_headers(token))
    assert r.status_code in (401, 403)


# ---------- Sync offline (RF-17, RF-18) ----------

def test_rf18_sync_rechaza_op_no_permitida_409(client):
    db = TestingSessionLocal()
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    barbero_id = barbero.id
    token = _token(client, "barbero1")
    db.close()
    r = client.post("/api/sync/", json={
        "operaciones": [{"id": "op1", "accion": "crear_servicio", "datos": {}}]
    }, headers=_headers(token))
    assert r.status_code == 200
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 409
    assert resultado["notificacion"]


def test_rf18_sync_rechaza_si_usuario_desactivado(client):
    db = TestingSessionLocal()
    usuario = _crear_usuario(db, "barbero1", Rol.BARBERO)
    token = _token(client, "barbero1")
    usuario.activo = False
    db.commit()
    db.close()
    r = client.post("/api/sync/", json={
        "operaciones": [{"id": "op1", "accion": "crear_corte", "datos": {}}]
    }, headers=_headers(token))
    assert r.status_code == 200
    resultado = r.json()["resultados"][0]
    assert resultado["aceptada"] is False
    assert resultado["status_code"] == 409
    assert resultado["motivo"] == "usuario_desactivado"


def test_rf18_sync_acepta_op_permitida(client):
    db = TestingSessionLocal()
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    servicio_id = servicio.id
    token = _token(client, "barbero1")
    db.close()
    r = client.post("/api/sync/", json={
        "operaciones": [{"id": "op1", "accion": "crear_corte", "datos": {"servicio_id": servicio_id, "metodo_pago": "efectivo"}}]
    }, headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["resultados"][0]["aceptada"] is True
