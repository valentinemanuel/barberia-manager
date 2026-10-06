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
    # T13/T16: comparacion Decimal exacta, sin floats; el DTO personal
    # ya no expone parte_barberia (paquete 3).
    assert data["parte_barbero"] == "50.00"
    assert "parte_barberia" not in data

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
    assert "parte_barberia" not in data


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
    assert "parte_barberia" not in data


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
    # T16: la API personal ya no expone parte_barberia, pero la fila
    # conserva el resto exacto (modelo intacto).
    assert "parte_barberia" not in data
    db = TestingSessionLocal()
    fila = db.query(Corte).filter(Corte.id == corte_id).first()
    assert fila.parte_barberia == Decimal("50.00")
    db.close()


def _payload_servicio_crear(precio):
    return {
        "nombre": "Servicio T8bis",
        "descripcion": "Validacion de precio canonico",
        "precio": precio,
        "duracion_minutos": 30,
    }

def test_servicio_rechaza_precio_con_mas_de_dos_decimales():
    """T8-bis: '10.005' se rechaza en la carga del catálogo (RF-41)."""
    from pydantic import ValidationError
    from app.schemas.servicio import ServicioCrear, ServicioActualizar

    with pytest.raises(ValidationError):
        ServicioCrear(**_payload_servicio_crear("10.005"))
    with pytest.raises(ValidationError):
        ServicioActualizar(precio="10.005")


def test_servicio_acepta_precio_canonico_sin_normalizar():
    """T8-bis: '100.00' y '0.05' pasan conservando representación."""
    from app.schemas.servicio import ServicioCrear

    assert ServicioCrear(**_payload_servicio_crear("100.00")).precio == Decimal("100.00")
    assert ServicioCrear(**_payload_servicio_crear("0.05")).precio == Decimal("0.05")


def _payload_corte_respuesta():
    from datetime import datetime
    return {
        "id": 1,
        "barbero_id": 1,
        "servicio_id": 1,
        "precio": Decimal("100.00"),
        "porcentaje_barbero": Decimal("50"),
        "parte_barbero": Decimal("50.00"),
        "metodo_pago": "efectivo",
        "fecha": datetime(2026, 10, 6, 12, 0, 0),
        "sincronizado": False,
    }


def test_dto_personal_excluye_parte_barberia():
    """T14: CortePersonal acepta el corte sin parte_barberia."""
    from app.schemas.corte import CortePersonal

    personal = CortePersonal(**_payload_corte_respuesta())
    assert "parte_barberia" not in personal.model_dump()
    assert personal.parte_barbero == Decimal("50.00")


def test_dto_compat_conserva_parte_barberia_para_admin():
    """T14: CorteResponse sigue intacto con el campo (compat admin)."""
    from app.schemas.corte import CorteResponse

    completo = CorteResponse(
        **{**_payload_corte_respuesta(), "parte_barberia": Decimal("50.00")}
    )
    assert completo.parte_barberia == Decimal("50.00")


def _crear_usuario(db, login, rol, porcentaje=Decimal("50")):
    usuario = Usuario(
        nombre="Nombre",
        apellido="Test",
        email=f"{login}@test.com",
        usuario=login,
        hashed_password=pwd_context.hash("pass"),
        rol=rol,
        porcentaje_ganancia=porcentaje,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _token_para(client, login):
    return client.post(
        "/api/auth/login", data={"username": login, "password": "pass"}
    ).json()["access_token"]


def test_historial_propio_sin_parte_barberia(client):
    """T15: el historial del barbero no expone parte_barberia y es solo propio."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t15a", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "barbero_t15b", RolModelo.BARBERO)
    db.close()

    _login_y_registrar_corte(client, "barbero_t15a", servicio_id)
    _login_y_registrar_corte(client, "barbero_t15b", servicio_id)

    respuesta = client.get(
        "/api/cortes/mi/historial",
        headers={"Authorization": f"Bearer {_token_para(client, 'barbero_t15a')}"},
    )
    assert respuesta.status_code == 200
    items = respuesta.json()
    assert len(items) == 1
    assert "parte_barberia" not in items[0]
    assert items[0]["parte_barbero"] == "50.00"
    assert "servicio_id" in items[0] and "metodo_pago" in items[0]


def test_historial_admin_ve_solo_lo_propio(client):
    """T15: el admin en /mi/historial ve únicamente sus cortes."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t15c", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t15", RolModelo.ADMIN, Decimal("0"))
    db.close()

    _login_y_registrar_corte(client, "barbero_t15c", servicio_id)
    _login_y_registrar_corte(client, "admin_t15", servicio_id)

    respuesta = client.get(
        "/api/cortes/mi/historial",
        headers={"Authorization": f"Bearer {_token_para(client, 'admin_t15')}"},
    )
    assert respuesta.status_code == 200
    items = respuesta.json()
    assert len(items) == 1
    assert "parte_barberia" not in items[0]
    db = TestingSessionLocal()
    admin_id = db.query(Usuario).filter(Usuario.usuario == "admin_t15").first().id
    db.close()
    assert items[0]["barbero_id"] == admin_id


def test_detalle_y_registro_sin_parte_barberia(client):
    """T16: detalle propio y registro responden sin parte_barberia."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t16a", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    registro = _login_y_registrar_corte(client, "barbero_t16a", servicio_id)
    assert registro.status_code == 201
    assert "parte_barberia" not in registro.json()

    detalle = client.get(
        f"/api/cortes/{registro.json()['id']}",
        headers={"Authorization": f"Bearer {_token_para(client, 'barbero_t16a')}"},
    )
    assert detalle.status_code == 200
    assert "parte_barberia" not in detalle.json()
    assert detalle.json()["parte_barbero"] == "50.00"


def test_detalle_ajeno_sigue_404(client):
    """T16 (RF-14 regresión): el detalle ajeno sigue 404 para el barbero."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t16b", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "barbero_t16c", RolModelo.BARBERO)
    db.close()

    registro = _login_y_registrar_corte(client, "barbero_t16b", servicio_id)
    corte_id = registro.json()["id"]

    detalle = client.get(
        f"/api/cortes/{corte_id}",
        headers={"Authorization": f"Bearer {_token_para(client, 'barbero_t16c')}"},
    )
    assert detalle.status_code == 404


CAMPOS_PROHIBIDOS_PERSONAL = ("parte_barberia", "costo", "margen", "bruto")


def _sin_campos_prohibidos(respuesta_json) -> list:
    """Devuelve los tokens prohibidos hallados (insensible a mayúsculas)."""
    import json

    texto = json.dumps(respuesta_json).lower()
    return [campo for campo in CAMPOS_PROHIBIDOS_PERSONAL if campo in texto]


def test_contratos_personales_sin_datos_del_negocio(client):
    """T17: ningún contrato personal expone datos del negocio ni ajenos."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t17", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    registro = _login_y_registrar_corte(client, "barbero_t17", servicio_id)
    assert registro.status_code == 201
    corte_id = registro.json()["id"]
    auth = {"Authorization": f"Bearer {_token_para(client, 'barbero_t17')}"}

    assert _sin_campos_prohibidos(registro.json()) == []
    historial = client.get("/api/cortes/mi/historial", headers=auth)
    assert historial.status_code == 200
    assert _sin_campos_prohibidos(historial.json()) == []
    detalle = client.get(f"/api/cortes/{corte_id}", headers=auth)
    assert detalle.status_code == 200
    assert _sin_campos_prohibidos(detalle.json()) == []
    for ruta in ("/mi/resumen/dia", "/mi/resumen/semana", "/mi/resumen/mes"):
        resumen = client.get(f"/api/cortes{ruta}", headers=auth)
        assert resumen.status_code == 200
        assert _sin_campos_prohibidos(resumen.json()) == []
