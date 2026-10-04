import pytest
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
