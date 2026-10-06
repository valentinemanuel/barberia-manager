import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.usuario import Usuario, Rol
from app.models.servicio import Servicio
from app.models.corte import Corte
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
    # T13: comparacion Decimal exacta, sin floats.
    assert data["parte_barbero"] == "50.00"
    assert data["parte_barberia"] == "50.00"

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


def test_crear_corte_rechaza_precio_con_mas_de_dos_decimales():
    """T8: precio 10.005 se rechaza con ValueError en español (el router lo vuelve 400).

    Nota: a nivel API con filas persistidas no se puede provocar, porque el
    ORM redondea a escala 2 al leer Numeric (verificado: raw 10.005 -> ORM
    Decimal('10.01')). Por eso se prueba el guard del servicio con objetos
    transient que conservan la precisión exacta de entrada.
    """
    from app.services.corte_service import crear_corte

    servicio = Servicio(
        nombre="Servicio T8",
        descripcion="Precision excesiva",
        precio=Decimal("10.005"),
        duracion_minutos=30,
        activo=True,
    )
    barbero = Usuario(
        nombre="Barbero",
        apellido="Test",
        email="barbero_t8a@test.com",
        usuario="barbero_t8a",
        hashed_password=pwd_context.hash("pass"),
        rol=Rol.BARBERO,
        porcentaje_ganancia=Decimal("50"),
        activo=True,
    )

    with pytest.raises(ValueError, match="dos decimales"):
        crear_corte(_DbNula(servicio), barbero, 1, "efectivo")


def test_crear_corte_rechaza_porcentaje_con_mas_de_dos_decimales():
    """T8: porcentaje 50.001 se rechaza con ValueError en español."""
    from app.services.corte_service import crear_corte

    servicio = Servicio(
        nombre="Servicio T8",
        descripcion="Precision excesiva",
        precio=Decimal("100.00"),
        duracion_minutos=30,
        activo=True,
    )
    barbero = Usuario(
        nombre="Barbero",
        apellido="Test",
        email="barbero_t8b@test.com",
        usuario="barbero_t8b",
        hashed_password=pwd_context.hash("pass"),
        rol=Rol.BARBERO,
        porcentaje_ganancia=Decimal("50.001"),
        activo=True,
    )

    with pytest.raises(ValueError, match="dos decimales"):
        crear_corte(_DbNula(servicio), barbero, 1, "efectivo")


def test_crear_corte_rechaza_valor_no_decimal_como_400():
    """T8: un float (p. ej. REAL leido sin escala) se rechaza, nunca 500."""
    from app.services.corte_service import crear_corte

    servicio = Servicio(
        nombre="Servicio T8",
        descripcion="Float infiltrado",
        precio=10.05,
        duracion_minutos=30,
        activo=True,
    )
    barbero = Usuario(
        nombre="Barbero",
        apellido="Test",
        email="barbero_t8c@test.com",
        usuario="barbero_t8c",
        hashed_password=pwd_context.hash("pass"),
        rol=Rol.BARBERO,
        porcentaje_ganancia=Decimal("50"),
        activo=True,
    )

    with pytest.raises(ValueError, match="Decimal"):
        crear_corte(_DbNula(servicio), barbero, 1, "efectivo")


class _DbNula:
    """Stub de sesión para T8: devuelve el servicio transient sin tocar DB."""

    def __init__(self, servicio):
        self._servicio = servicio

    def query(self, _modelo):
        return self

    def filter(self, *_criterios):
        return self

    def first(self):
        return self._servicio

    def add(self, _obj):
        pass

    def commit(self):
        pass

    def refresh(self, _obj):
        pass


def test_crear_corte_no_commitea_persiste_solo_con_commit_externo(client):
    """T9: el servicio hace flush sin commit; otra conexion no ve el corte
    hasta que el llamador commitea (UoW unica por operacion)."""
    from app.services.corte_service import crear_corte

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t9", Decimal("50"), Decimal("100.00"))
    barbero = db.query(Usuario).filter(Usuario.usuario == "barbero_t9").first()
    servicio_id = db.query(Servicio).first().id

    corte = crear_corte(db, barbero, servicio_id, "efectivo")

    otra_conexion = TestingSessionLocal()
    assert otra_conexion.query(Corte).filter(Corte.id == corte.id).first() is None
    otra_conexion.close()

    db.commit()
    verificacion = TestingSessionLocal()
    assert verificacion.query(Corte).filter(Corte.id == corte.id).first() is not None
    verificacion.close()
    db.close()


def _payload_usuario_crear(porcentaje):
    return {
        "nombre": "Nuevo",
        "apellido": "Barbero",
        "email": "nuevo@test.com",
        "usuario": "nuevousuario",
        "password": "pass123",
        "rol": "barbero",
        "porcentaje_ganancia": porcentaje,
    }


def test_usuario_rechaza_porcentaje_con_mas_de_dos_decimales():
    """T10: '50.000' y 50.001 se rechazan (RF-41), aunque estén en rango."""
    from pydantic import ValidationError
    from app.schemas.usuario import UsuarioCrear, UsuarioActualizar

    with pytest.raises(ValidationError):
        UsuarioCrear(**_payload_usuario_crear("50.000"))
    with pytest.raises(ValidationError):
        UsuarioCrear(**_payload_usuario_crear(50.001))
    with pytest.raises(ValidationError):
        UsuarioActualizar(porcentaje_ganancia="50.001")


def test_usuario_acepta_porcentaje_canonico_sin_normalizar():
    """T10: 50.25, 100 y 0 pasan conservando representación."""
    from app.schemas.usuario import UsuarioCrear

    assert UsuarioCrear(**_payload_usuario_crear("50.25")).porcentaje_ganancia == Decimal("50.25")
    assert UsuarioCrear(**_payload_usuario_crear(100)).porcentaje_ganancia == Decimal("100")
    assert UsuarioCrear(**_payload_usuario_crear(0)).porcentaje_ganancia == Decimal("0")


def test_corte_conserva_snapshot_ante_cambio_posterior_de_porcentaje(client):
    """T11 (RF-5 parcial): el corte conserva precio/porcentaje/reparto aplicados;
    cambiar despues el porcentaje del barbero no lo altera."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t11", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    response = _login_y_registrar_corte(client, "barbero_t11", servicio_id)
    assert response.status_code == 201
    corte_id = response.json()["id"]

    db = TestingSessionLocal()
    token_resp = client.post(
        "/api/auth/login", data={"username": "barbero_t11", "password": "pass"}
    )
    token = token_resp.json()["access_token"]
    db.query(Usuario).filter(Usuario.usuario == "barbero_t11").update(
        {"porcentaje_ganancia": Decimal("60")}
    )
    db.commit()
    db.close()

    detalle = client.get(
        f"/api/cortes/{corte_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert detalle.status_code == 200
    data = detalle.json()
    assert data["precio"] == "100.00"
    assert Decimal(data["porcentaje_barbero"]) == Decimal("50")
    assert data["parte_barbero"] == "50.00"
    assert data["parte_barberia"] == "50.00"
