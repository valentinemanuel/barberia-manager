import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol
from app.models.auditoria import Auditoria, AccionAuditoria

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_usuarios.db"
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


def test_degradar_ultimo_admin_devuelve_409_sin_auditoria(client):
    db = TestingSessionLocal()
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    barbero = _crear_usuario(db, "barbero1", Rol.BARBERO)
    token = _token(client, "admin1")
    admin_id = admin.id
    db.close()

    r = client.put(
        f"/api/usuarios/{admin_id}",
        json={"rol": "barbero"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409

    db = TestingSessionLocal()
    try:
        assert db.query(Usuario).filter(Usuario.id == admin_id).first().rol == Rol.ADMIN
        assert db.query(Auditoria).count() == 0
    finally:
        db.close()


def test_cambiar_rol_registra_auditoria(client):
    db = TestingSessionLocal()
    admin = _crear_usuario(db, "admin1", Rol.ADMIN)
    admin2 = _crear_usuario(db, "admin2", Rol.ADMIN)
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    token = _token(client, "admin1")
    barbero_id = db.query(Usuario).filter(Usuario.usuario == "barbero1").first().id
    db.close()

    r = client.put(
        f"/api/usuarios/{barbero_id}",
        json={"rol": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    db = TestingSessionLocal()
    try:
        registros = db.query(Auditoria).filter(Auditoria.accion == AccionAuditoria.CAMBIAR_ROL).all()
        assert len(registros) == 1
        assert registros[0].usuario_afectado_id == barbero_id
        assert registros[0].valor_anterior == {"rol": "barbero"}
        assert registros[0].valor_nuevo == {"rol": "admin"}
    finally:
        db.close()


def test_crear_usuario_registra_auditoria(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "admin1", Rol.ADMIN)
    token = _token(client, "admin1")
    db.close()

    r = client.post(
        "/api/usuarios/",
        json={
            "nombre": "Nuevo",
            "apellido": "Barbero",
            "email": "nuevo@test.com",
            "usuario": "nuevousuario",
            "password": "pass123",
            "rol": "barbero",
            "porcentaje_ganancia": 50,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201

    db = TestingSessionLocal()
    try:
        registros = db.query(Auditoria).filter(Auditoria.accion == AccionAuditoria.CREAR_USUARIO).all()
        assert len(registros) == 1
        assert registros[0].valor_anterior is None
    finally:
        db.close()


def test_barbero_recibe_403(client):
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero1", Rol.BARBERO)
    token = _token(client, "barbero1")
    db.close()

    r = client.get("/api/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
