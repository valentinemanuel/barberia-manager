import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auditoria_router.db"
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


def test_barbero_recibe_403(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barb", Rol.BARBERO)
    db.close()
    token = _token(client, "barb")
    r = client.get("/api/auditoria", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_admin_recibe_200_con_paginacion(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    db.close()
    token = _token(client, "admin1")
    headers = {"Authorization": f"Bearer {token}"}
    # Generar registros de auditoría
    client.post("/api/usuarios/", headers=headers, json={
        "nombre": "Nuevo", "apellido": "User", "email": "nuevo@test.com",
        "usuario": "nuevo", "password": "pass123", "rol": "barbero",
        "porcentaje_ganancia": 50,
    })
    r = client.get("/api/auditoria?skip=0&limit=10", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data
    assert data["skip"] == 0 and data["limit"] == 10
    assert data["total"] >= 1
