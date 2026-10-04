import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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


def test_login_exitoso(client):
    # Crear usuario de prueba
    db = TestingSessionLocal()
    usuario = Usuario(
        nombre="Test",
        apellido="User",
        email="test@test.com",
        usuario="testuser",
        hashed_password=pwd_context.hash("testpass"),
        rol=Rol.BARBERO,
        porcentaje_ganancia=50,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.close()

    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_fallido(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "wrong", "password": "wrong"}
    )
    assert response.status_code == 401
