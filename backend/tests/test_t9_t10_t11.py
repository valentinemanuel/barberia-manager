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

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_t9_t10_t11.db"
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


# ---------- T9 ----------

def test_barbero_accede_a_corte_ajeno_recibe_404(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barb1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barb2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    corte_ajeno = _crear_corte(db, barbero2, servicio)
    token = _token(client, "barb1")
    r = client.get(f"/api/cortes/{corte_ajeno.id}", headers=_headers(token))
    assert r.status_code == 404
    db.close()


def test_barbero_accede_a_corte_propio_200(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barb1", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    corte = _crear_corte(db, barbero1, servicio)
    token = _token(client, "barb1")
    r = client.get(f"/api/cortes/{corte.id}", headers=_headers(token))
    assert r.status_code == 200
    db.close()


def test_admin_accede_a_cualquier_corte(client):
    db = TestingSessionLocal()
    barbero2 = _crear_usuario(db, "barb2", Rol.BARBERO)
    _crear_usuario(db, "admin1", Rol.ADMIN)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    corte = _crear_corte(db, barbero2, servicio)
    token = _token(client, "admin1")
    r = client.get(f"/api/cortes/{corte.id}", headers=_headers(token))
    assert r.status_code == 200
    db.close()


def test_admin_ve_lo_propio_en_mi_historial(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    token = _token(client, "admin1")
    r = client.get("/api/cortes/mi/historial", headers=_headers(token))
    assert r.status_code == 200
    assert r.json() == []
    db.close()


# ---------- T10 ----------

CAMPOS_PROHIBIDOS = ("costo", "margen", "utilidad", "precio_compra", "precio_costo", "ganancia_bruta")


def _verificar_solo_precio_venta(items):
    assert len(items) > 0
    for item in items:
        for campo in item.keys():
            assert not any(p in campo.lower() for p in CAMPOS_PROHIBIDOS), f"Campo prohibido: {campo}"
        # Solo expone el precio de venta
        assert "precio" in item


def test_servicios_no_exponen_costos_ni_margenes(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barb1", Rol.BARBERO)
    db.add(Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True))
    db.commit()
    token = _token(client, "barb1")
    r = client.get("/api/servicios/", headers=_headers(token))
    assert r.status_code == 200
    _verificar_solo_precio_venta(r.json())
    db.close()


def test_productos_no_exponen_costos_ni_margenes(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barb1", Rol.BARBERO)
    db.add(Producto(nombre="Gel", precio=Decimal("50.00"), stock=10, activo=True))
    db.commit()
    token = _token(client, "barb1")
    r = client.get("/api/productos/", headers=_headers(token))
    assert r.status_code == 200
    _verificar_solo_precio_venta(r.json())
    db.close()


def test_consumibles_no_exponen_costos_ni_margenes(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barb1", Rol.BARBERO)
    db.add(Consumible(nombre="Navaja", precio=Decimal("20.00"), stock=10, activo=True))
    db.commit()
    token = _token(client, "barb1")
    r = client.get("/api/consumibles/", headers=_headers(token))
    assert r.status_code == 200
    _verificar_solo_precio_venta(r.json())
    db.close()


# ---------- T11 ----------

def test_resumen_dia_filtra_por_barbero_actual(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barb1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barb2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero2, servicio)
    token = _token(client, "barb1")
    r = client.get("/api/cortes/mi/resumen/dia", headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["total_cortes"] == 2
    db.close()


def test_resumen_semana_y_mes_filtran_por_barbero_actual(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barb1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barb2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero2, servicio)
    token = _token(client, "barb1")
    r_semana = client.get("/api/cortes/mi/resumen/semana", headers=_headers(token))
    r_mes = client.get("/api/cortes/mi/resumen/mes", headers=_headers(token))
    assert r_semana.status_code == 200 and r_semana.json()["total_cortes"] == 1
    assert r_mes.status_code == 200 and r_mes.json()["total_cortes"] == 1
    db.close()


def test_historial_filtra_por_barbero_actual(client):
    db = TestingSessionLocal()
    barbero1 = _crear_usuario(db, "barb1", Rol.BARBERO)
    barbero2 = _crear_usuario(db, "barb2", Rol.BARBERO)
    servicio = Servicio(nombre="Corte", precio=Decimal("100.00"), duracion_minutos=30, activo=True)
    db.add(servicio)
    db.commit()
    _crear_corte(db, barbero1, servicio)
    _crear_corte(db, barbero2, servicio)
    token = _token(client, "barb1")
    r = client.get("/api/cortes/mi/historial", headers=_headers(token))
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 1
    assert datos[0]["barbero_id"] == barbero1.id
    db.close()
