import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol
from app.models.servicio import Servicio
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_cortes.db"
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
    # Restaurar el override propio: otro archivo de tests pudo pisarlo al importarse
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_crear_corte_calcula_porcentaje(client):
    db = TestingSessionLocal()

    # Crear barbero con 50%
    barbero = Usuario(
        nombre="Barbero",
        apellido="Test",
        email="barbero@test.com",
        usuario="barbero1",
        hashed_password=pwd_context.hash("pass"),
        rol=Rol.BARBERO,
        porcentaje_ganancia=50,
        activo=True,
    )
    db.add(barbero)

    # Crear servicio
    servicio = Servicio(
        nombre="Corte Clásico",
        descripcion="Corte de cabello clásico",
        precio=100.00,
        duracion_minutos=30,
        activo=True,
    )
    db.add(servicio)
    db.commit()

    # Login
    response = client.post(
        "/api/auth/login",
        data={"username": "barbero1", "password": "pass"}
    )
    token = response.json()["access_token"]

    # Crear corte
    response = client.post(
        "/api/cortes/",
        json={"servicio_id": servicio.id, "metodo_pago": "efectivo"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    # Los Decimal se serializan como string ("50.00")
    assert float(data["parte_barbero"]) == 50.00
    assert float(data["parte_barberia"]) == 50.00

    db.close()


def _crear_barbero_y_servicio(db, usuario_login, porcentaje, precio):
    """Alta directa de barbero y servicio con Decimal exactos para T7."""
    barbero = Usuario(
        nombre="Barbero",
        apellido="Test",
        email=f"{usuario_login}@test.com",
        usuario=usuario_login,
        hashed_password=pwd_context.hash("pass"),
        rol=Rol.BARBERO,
        porcentaje_ganancia=porcentaje,
        activo=True,
    )
    db.add(barbero)
    servicio = Servicio(
        nombre="Servicio T7",
        descripcion="Servicio para redondeo exacto",
        precio=precio,
        duracion_minutos=30,
        activo=True,
    )
    db.add(servicio)
    db.commit()
    return barbero


def _login_y_registrar_corte(client, usuario_login, servicio_id):
    response = client.post(
        "/api/auth/login",
        data={"username": usuario_login, "password": "pass"}
    )
    token = response.json()["access_token"]
    return client.post(
        "/api/cortes/",
        json={"servicio_id": servicio_id, "metodo_pago": "efectivo"},
        headers={"Authorization": f"Bearer {token}"}
    )


def test_crear_corte_reparto_exactitud_centavo(client):
    """T7: 100.00 al 50% responde strings exactos 50.00/50.00 (sin floats)."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t7a", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    response = _login_y_registrar_corte(client, "barbero_t7a", servicio_id)
    assert response.status_code == 201
    data = response.json()
    assert data["parte_barbero"] == "50.00"
    assert data["parte_barberia"] == "50.00"


def test_crear_corte_redondeo_matematico_mitad_hacia_arriba(client):
    """T7: 0.05 al 50% -> comision 0.03 (ROUND_HALF_UP) y barberia 0.02 (resto)."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t7b", Decimal("50"), Decimal("0.05"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    response = _login_y_registrar_corte(client, "barbero_t7b", servicio_id)
    assert response.status_code == 201
    data = response.json()
    assert data["parte_barbero"] == "0.03"
    assert data["parte_barberia"] == "0.02"
