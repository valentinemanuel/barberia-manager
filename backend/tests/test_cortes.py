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


def _registrar_corte_admin(client, token_admin, servicio_id, destino_id):
    return client.post(
        "/api/cortes/",
        json={
            "servicio_id": servicio_id,
            "metodo_pago": "efectivo",
            "barbero_id": destino_id,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )


def test_registro_admin_para_otro_barbero(client):
    """T20: el admin registra para otro barbero con el porcentaje del destino."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t20a", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t20", RolModelo.ADMIN, Decimal("0"))
    dest_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t20a").first().id
    db.close()

    respuesta = _registrar_corte_admin(
        client, _token_para(client, "admin_t20"), servicio_id, dest_id
    )
    assert respuesta.status_code == 201
    data = respuesta.json()
    assert data["barbero_id"] == dest_id
    assert data["parte_barbero"] == "50.00"


def test_registro_destino_inexistente_404(client):
    """T20: destino inexistente → 404 sin revelar nada."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t20b", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t20b", RolModelo.ADMIN, Decimal("0"))
    db.close()

    respuesta = _registrar_corte_admin(
        client, _token_para(client, "admin_t20b"), servicio_id, 9999
    )
    assert respuesta.status_code == 404


def test_barbero_no_puede_enviar_destino_403(client):
    """T20: el barbero no puede enviar barbero_id, ni siquiera el propio."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t20c", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    propio_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t20c").first().id
    db.close()

    respuesta = _registrar_corte_admin(
        client, _token_para(client, "barbero_t20c"), servicio_id, propio_id
    )
    assert respuesta.status_code == 403


def test_registro_destino_inactivo_con_porcentaje_201(client):
    """T20 (RF-56): destino inactivo con porcentaje → 201."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t20d", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t20d", RolModelo.ADMIN, Decimal("0"))
    db.query(Usuario).filter(Usuario.usuario == "barbero_t20d").update({"activo": False})
    db.commit()
    dest_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t20d").first().id
    db.close()

    respuesta = _registrar_corte_admin(
        client, _token_para(client, "admin_t20d"), servicio_id, dest_id
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["barbero_id"] == dest_id


def _registrar_corte_con_momento(client, token, servicio_id, momento):
    body = {"servicio_id": servicio_id, "metodo_pago": "efectivo"}
    if momento is not None:
        body["momento_real"] = momento
    return client.post(
        "/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"}
    )


def test_registro_admin_retroactivo_conserva_fecha(client):
    """T21: el admin registra en el pasado y se conserva esa fecha."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t21a", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t21a", RolModelo.ADMIN, Decimal("0"))
    db.close()

    respuesta = _registrar_corte_con_momento(
        client, _token_para(client, "admin_t21a"), servicio_id, "2020-05-01T10:00:00"
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["fecha"].startswith("2020-05-01T10:00:00")


def test_registro_admin_futuro_rechazado_400(client):
    """T21: momento futuro → 400."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t21b", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t21b", RolModelo.ADMIN, Decimal("0"))
    db.close()

    respuesta = _registrar_corte_con_momento(
        client, _token_para(client, "admin_t21b"), servicio_id, "2999-01-01T00:00:00"
    )
    assert respuesta.status_code == 400


def test_barbero_no_puede_enviar_momento_400(client):
    """T21 (RF-8): el barbero no introduce fecha manual."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t21c", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    respuesta = _registrar_corte_con_momento(
        client, _token_para(client, "barbero_t21c"), servicio_id, "2020-05-01T10:00:00"
    )
    assert respuesta.status_code == 400


def test_registro_sin_momento_usa_fecha_automatica(client):
    """T21: sin momento, la fecha es automática (≈ ahora UTC)."""
    from datetime import datetime

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t21d", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    antes = datetime.utcnow().replace(microsecond=0)
    respuesta = _registrar_corte_con_momento(
        client, _token_para(client, "barbero_t21d"), servicio_id, None
    )
    assert respuesta.status_code == 201
    fecha = respuesta.json()["fecha"]
    assert fecha[:10] == antes.strftime("%Y-%m-%d")


def test_reparto_usa_valores_actuales_del_destinatario(client):
    """T22 (RF-5 parcial): admin retroactivo para barbero 30% usa el % del
    destino (60.00/140.00 sobre 200.00), no el 0% del admin; fecha conservada."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t22", Decimal("30"), Decimal("200.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t22", RolModelo.ADMIN, Decimal("0"))
    dest_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t22").first().id
    db.close()

    respuesta = client.post(
        "/api/cortes/",
        json={
            "servicio_id": servicio_id,
            "metodo_pago": "tarjeta",
            "barbero_id": dest_id,
            "momento_real": "2021-03-15T09:30:00",
        },
        headers={"Authorization": f"Bearer {_token_para(client, 'admin_t22')}"},
    )
    assert respuesta.status_code == 201
    data = respuesta.json()
    assert data["barbero_id"] == dest_id
    assert data["precio"] == "200.00"
    assert Decimal(data["porcentaje_barbero"]) == Decimal("30")
    assert data["parte_barbero"] == "60.00"
    assert data["fecha"].startswith("2021-03-15T09:30:00")


def test_errores_exactos_sin_filtraciones(client):
    """T23: cada rechazo con su código y mensaje exacto, sin datos ajenos."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t23", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t23", RolModelo.ADMIN, Decimal("0"))
    db.close()

    token_admin = _token_para(client, "admin_t23")
    token_barbero = _token_para(client, "barbero_t23")

    r = _registrar_corte_admin(client, token_admin, servicio_id, 9999)
    assert r.status_code == 404
    assert r.json()["detail"] == "Barbero no encontrado"

    r = _registrar_corte_con_momento(client, token_barbero, servicio_id, None)
    assert r.status_code == 201
    r = client.post(
        "/api/cortes/",
        json={"servicio_id": servicio_id, "metodo_pago": "efectivo", "barbero_id": 1},
        headers={"Authorization": f"Bearer {token_barbero}"},
    )
    assert r.status_code == 403
    assert "admin" in r.json()["detail"].lower()

    r = _registrar_corte_con_momento(client, token_admin, servicio_id, "2999-06-01T00:00:00")
    assert r.status_code == 400
    assert "futuro" in r.json()["detail"].lower()

    r = client.post(
        "/api/cortes/",
        json={"servicio_id": "no-entero", "metodo_pago": "efectivo"},
        headers={"Authorization": f"Bearer {token_barbero}"},
    )
    assert r.status_code == 422


def test_listado_global_admin_contrato_completo(client):
    """T24: el listado global de admin conserva el contrato completo."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t24", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t24", RolModelo.ADMIN, Decimal("0"))
    db.close()

    _login_y_registrar_corte(client, "barbero_t24", servicio_id)
    respuesta = client.get(
        "/api/cortes/",
        headers={"Authorization": f"Bearer {_token_para(client, 'admin_t24')}"},
    )
    assert respuesta.status_code == 200
    items = respuesta.json()
    assert len(items) == 1
    assert items[0]["parte_barberia"] == "50.00"


def test_destino_admin_hacia_otro_admin_400(client):
    """Decisión RF-2: el destino de un admin debe ser barbero, no otro admin."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t26", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t26a", RolModelo.ADMIN, Decimal("0"))
    _crear_usuario(db, "admin_t26b", RolModelo.ADMIN, Decimal("0"))
    otro_id = db.query(Usuario).filter(Usuario.usuario == "admin_t26b").first().id
    db.close()

    respuesta = _registrar_corte_admin(
        client, _token_para(client, "admin_t26a"), servicio_id, otro_id
    )
    assert respuesta.status_code == 400
    assert "barbero" in respuesta.json()["detail"].lower()


def test_destino_propio_explicito_del_admin_201(client):
    """Decisión RF-2: el admin puede indicarse a sí mismo (registro propio)."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t26c", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t26c", RolModelo.ADMIN, Decimal("0"))
    propio_id = db.query(Usuario).filter(Usuario.usuario == "admin_t26c").first().id
    db.close()

    respuesta = _registrar_corte_admin(
        client, _token_para(client, "admin_t26c"), servicio_id, propio_id
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["barbero_id"] == propio_id


def _ejecutar_registro_idempotente(db, actor, servicio_id, op_id, ns="web"):
    """T27: registra un corte vía ejecutor idempotente (efecto único)."""
    import uuid as uuid_lib
    from app.services.corte_service import crear_corte
    from app.services.operacion_corte_service import ejecutar_operacion

    payload = {"servicio_id": servicio_id, "metodo_pago": "efectivo"}

    def _efecto():
        corte = crear_corte(db, actor, servicio_id, "efectivo")
        return {"corte_id": corte.id, "estado": "aceptada"}

    return ejecutar_operacion(
        db,
        actor_id=actor.id,
        namespace=ns,
        operacion_id=op_id or str(uuid_lib.uuid4()),
        accion="crear_corte",
        payload=payload,
        modo="online",
        ejecutar=_efecto,
    )


def test_operacion_replay_devuelve_acuse_sin_reejecutar(client):
    """T27: misma clave + mismo hash → un solo corte y mismo acuse."""
    import uuid as uuid_lib
    from app.models.corte import Corte

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t27", Decimal("50"), Decimal("100.00"))
    actor = db.query(Usuario).filter(Usuario.usuario == "barbero_t27").first()
    servicio_id = db.query(Servicio).first().id
    op_id = str(uuid_lib.uuid4())

    acuse1 = _ejecutar_registro_idempotente(db, actor, servicio_id, op_id)
    db.commit()
    acuse2 = _ejecutar_registro_idempotente(db, actor, servicio_id, op_id)
    db.commit()

    assert acuse1 == acuse2
    assert acuse1["estado"] == "aceptada"
    assert db.query(Corte).count() == 1
    db.close()


def test_post_doble_uuid_mismo_corte(client):
    """T28: doble POST con misma operacion_uuid → mismo id, un solo corte."""
    import uuid as uuid_lib
    from app.models.corte import Corte as CorteModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t28", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    token = _token_para(client, "barbero_t28")
    op_id = str(uuid_lib.uuid4())
    body = {
        "servicio_id": servicio_id,
        "metodo_pago": "efectivo",
        "operacion_uuid": op_id,
    }
    r1 = client.post("/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"})
    r2 = client.post("/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    db = TestingSessionLocal()
    assert db.query(CorteModelo).count() == 1
    db.close()


def test_post_sin_uuid_camino_legacy_intacto(client):
    """T28: sin UUID el registro funciona como siempre (RNF-3)."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t28b", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    respuesta = _login_y_registrar_corte(client, "barbero_t28b", servicio_id)
    assert respuesta.status_code == 201
    assert respuesta.json()["parte_barbero"] == "50.00"


def test_conflicto_identidad_mismo_uuid_distinto_contenido_409(client):
    """T29: misma UUID con otro servicio → 409 sin efecto; el acuse original sigue."""
    import uuid as uuid_lib
    from app.models.corte import Corte as CorteModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t29", Decimal("50"), Decimal("100.00"))
    servicio1 = db.query(Servicio).first().id
    db.add(
        Servicio(
            nombre="Servicio T29b",
            descripcion="Segundo servicio",
            precio=Decimal("200.00"),
            duracion_minutos=30,
            activo=True,
        )
    )
    db.commit()
    servicio2 = db.query(Servicio).filter(Servicio.nombre == "Servicio T29b").first().id
    db.close()

    token = _token_para(client, "barbero_t29")
    op_id = str(uuid_lib.uuid4())
    body1 = {"servicio_id": servicio1, "metodo_pago": "efectivo", "operacion_uuid": op_id}
    body2 = {"servicio_id": servicio2, "metodo_pago": "efectivo", "operacion_uuid": op_id}

    r1 = client.post("/api/cortes/", json=body1, headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 201
    r2 = client.post("/api/cortes/", json=body2, headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 409

    r3 = client.post("/api/cortes/", json=body1, headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 201
    assert r3.json()["id"] == r1.json()["id"]

    db = TestingSessionLocal()
    assert db.query(CorteModelo).count() == 1
    db.close()


def test_replay_con_catalogo_cambiado_no_recalcula(client):
    """T30: replay tras cambiar catálogo devuelve el acuse original intacto."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t30", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    token = _token_para(client, "barbero_t30")
    op_id = str(uuid_lib.uuid4())
    body = {
        "servicio_id": servicio_id,
        "metodo_pago": "efectivo",
        "operacion_uuid": op_id,
    }
    r1 = client.post("/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 201

    db = TestingSessionLocal()
    db.query(Servicio).filter(Servicio.id == servicio_id).update({"precio": Decimal("200.00")})
    db.query(Usuario).filter(Usuario.usuario == "barbero_t30").update(
        {"porcentaje_ganancia": Decimal("60")}
    )
    db.commit()
    db.close()

    r2 = client.post("/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]
    assert r2.json()["parte_barbero"] == "50.00"
    assert r2.json()["precio"] == "100.00"


def test_doble_envio_simultaneo_un_solo_corte(client):
    """T31: dos hilos con misma UUID → un solo corte y mismo id en ambos."""
    import threading
    import uuid as uuid_lib
    from app.models.corte import Corte as CorteModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t31", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    token = _token_para(client, "barbero_t31")
    op_id = str(uuid_lib.uuid4())
    body = {
        "servicio_id": servicio_id,
        "metodo_pago": "efectivo",
        "operacion_uuid": op_id,
    }
    resultados = []

    def _post():
        respuesta = client.post(
            "/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"}
        )
        resultados.append((respuesta.status_code, respuesta.json().get("id")))

    hilos = [threading.Thread(target=_post) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert sorted(r[0] for r in resultados) == [201, 201]
    assert resultados[0][1] == resultados[1][1] is not None

    db = TestingSessionLocal()
    assert db.query(CorteModelo).count() == 1
    db.close()


def _enviar_lote_sync(client, token, operaciones):
    return client.post(
        "/api/sync/",
        json={"operaciones": operaciones},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_sync_reenvio_con_uuid_no_duplica(client):
    """T32: reenviar el lote con operacion_uuid no duplica el corte."""
    import uuid as uuid_lib
    from app.models.corte import Corte as CorteModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t32", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    token = _token_para(client, "barbero_t32")
    lote = [
        {
            "id": "op-1",
            "accion": "crear_corte",
            "datos": {
                "servicio_id": servicio_id,
                "metodo_pago": "efectivo",
                "operacion_uuid": str(uuid_lib.uuid4()),
            },
        }
    ]
    r1 = _enviar_lote_sync(client, token, lote)
    r2 = _enviar_lote_sync(client, token, lote)
    assert r1.json()["aceptadas"] == 1
    assert r2.json()["aceptadas"] == 1

    db = TestingSessionLocal()
    assert db.query(CorteModelo).count() == 1
    db.close()


def _abonar(client, token, corte_id, concepto, importe, extra=None):
    body = {"concepto": concepto, "importe": importe, "metodo_pago": "efectivo"}
    if extra:
        body.update(extra)
    return client.post(
        f"/api/cortes/{corte_id}/movimientos",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


def _corte_para_abonos(client, login, porcentaje="50", precio="100.00"):
    from app.models.corte import Corte as CorteModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, login, Decimal(porcentaje), Decimal(precio))
    servicio_id = db.query(Servicio).first().id
    db.close()
    respuesta = _login_y_registrar_corte(client, login, servicio_id)
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def test_abono_parcial_por_concepto_201(client):
    """T35: abono cliente 30 sobre 100 conserva importe real."""
    corte_id = _corte_para_abonos(client, "barbero_t35")
    respuesta = _abonar(client, _token_para(client, "barbero_t35"), corte_id, "cliente", 30)
    assert respuesta.status_code == 201
    assert respuesta.json()["importe"] == "30.00"
    assert respuesta.json()["concepto"] == "cliente"


def test_abono_invalido_400(client):
    """T35: abono 0/negativo/3 decimales → 400 sin crear movimiento."""
    from app.models.finanzas_corte import MovimientoCorte

    corte_id = _corte_para_abonos(client, "barbero_t35b")
    token = _token_para(client, "barbero_t35b")
    for importe in (0, -10, "10.005"):
        assert _abonar(client, token, corte_id, "cliente", importe).status_code == 400
    db = TestingSessionLocal()
    assert db.query(MovimientoCorte).count() == 0
    db.close()


def test_abono_uuid_duplicado_un_solo_movimiento(client):
    """T35: reintento con misma UUID → un solo movimiento."""
    import uuid as uuid_lib
    from app.models.finanzas_corte import MovimientoCorte

    corte_id = _corte_para_abonos(client, "barbero_t35c")
    token = _token_para(client, "barbero_t35c")
    op_id = str(uuid_lib.uuid4())
    r1 = _abonar(client, token, corte_id, "cliente", 30, {"uuid": op_id})
    r2 = _abonar(client, token, corte_id, "cliente", 30, {"uuid": op_id})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    db = TestingSessionLocal()
    assert db.query(MovimientoCorte).count() == 1
    db.close()


def test_abono_uuid_invalida_422(client):
    """Revision P6: uuid de movimiento con formato invalido -> 422."""
    corte_id = _corte_para_abonos(client, "barbero_t35g")
    respuesta = _abonar(
        client, _token_para(client, "barbero_t35g"), corte_id, "cliente", 10,
        {"uuid": "no-es-uuid"},
    )
    assert respuesta.status_code == 422


def test_abono_corte_ajeno_404(client):
    """T35: titularidad — corte ajeno → 404."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t35d")
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero_t35e", RolModelo.BARBERO)
    db.close()
    respuesta = _abonar(
        client, _token_para(client, "barbero_t35e"), corte_id, "cliente", 10
    )
    assert respuesta.status_code == 404


def test_barbero_no_envia_momento_en_abono_400(client):
    """T35 (RF-51): momento manual solo admin."""
    corte_id = _corte_para_abonos(client, "barbero_t35f")
    respuesta = _abonar(
        client,
        _token_para(client, "barbero_t35f"),
        corte_id,
        "cliente",
        10,
        {"momento_real": "2020-01-01T00:00:00"},
    )
    assert respuesta.status_code == 400


def _saldos(client, token, corte_id):
    return client.get(
        f"/api/cortes/{corte_id}/saldos",
        headers={"Authorization": f"Bearer {token}"},
    )


def test_abono_no_mueve_otro_concepto(client):
    """T36 (RF-18/19): abono cliente no altera saldo comisión y viceversa."""
    corte_id = _corte_para_abonos(client, "barbero_t36")
    token = _token_para(client, "barbero_t36")

    assert _abonar(client, token, corte_id, "cliente", 40).status_code == 201
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "40.00"
    assert saldos["cliente"]["restante"] == "60.00"
    assert saldos["cliente"]["estado"] == "parcial"
    assert saldos["comision"]["abonado"] == "0.00"
    assert saldos["comision"]["restante"] == "50.00"
    assert saldos["comision"]["estado"] == "pendiente"

    assert _abonar(client, token, corte_id, "comision", 50).status_code == 201
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["comision"]["estado"] == "pagado"
    assert saldos["cliente"]["restante"] == "60.00"


def test_saldar_restante_exacta_paga_sin_flags(client):
    """T36 (RF-20): saldar el restante exacto cambia a pagado; no hay endpoint de pagado."""
    corte_id = _corte_para_abonos(client, "barbero_t36b")
    token = _token_para(client, "barbero_t36b")

    assert _abonar(client, token, corte_id, "cliente", 100).status_code == 201
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["estado"] == "pagado"
    assert saldos["cliente"]["restante"] == "0.00"

    assert "parte_barberia" not in saldos["cliente"]
    assert "parte_barberia" not in saldos["comision"]
    r = client.post(
        f"/api/cortes/{corte_id}/pagar", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code in (404, 405)


def test_matriz_pendiente_parcial_pagado(client):
    """T37: 0 → pendiente; 30 → parcial/70; 30+70 → pagado/0."""
    corte_id = _corte_para_abonos(client, "barbero_t37")
    token = _token_para(client, "barbero_t37")

    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["estado"] == "pendiente"
    assert saldos["cliente"]["abonado"] == "0.00"
    assert saldos["cliente"]["restante"] == "100.00"

    assert _abonar(client, token, corte_id, "cliente", 30).status_code == 201
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["estado"] == "parcial"
    assert saldos["cliente"]["abonado"] == "30.00"
    assert saldos["cliente"]["restante"] == "70.00"

    assert _abonar(client, token, corte_id, "cliente", 70).status_code == 201
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["estado"] == "pagado"
    assert saldos["cliente"]["abonado"] == "100.00"
    assert saldos["cliente"]["restante"] == "0.00"


def _registrar_con_cobro(client, token, servicio_id, cobro, importe=None):
    body = {
        "servicio_id": servicio_id,
        "metodo_pago": "efectivo",
        "cobro_inicial": cobro,
    }
    if importe is not None:
        body["importe_cobro"] = importe
    return client.post(
        "/api/cortes/", json=body, headers={"Authorization": f"Bearer {token}"}
    )


def test_cobro_inicial_pendiente_sin_abono(client):
    """T38: pendiente no crea abono."""
    from app.models.finanzas_corte import MovimientoCorte

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t38a", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    r = _registrar_con_cobro(client, _token_para(client, "barbero_t38a"), servicio_id, "pendiente")
    assert r.status_code == 201
    db = TestingSessionLocal()
    assert db.query(MovimientoCorte).count() == 0
    db.close()


def test_cobro_inicial_parcial_y_completo(client):
    """T38: parcial crea el importe real; completo, el precio mostrado."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t38b", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()
    token = _token_para(client, "barbero_t38b")

    r = _registrar_con_cobro(client, token, servicio_id, "parcial", 40)
    assert r.status_code == 201
    saldos = _saldos(client, token, r.json()["id"]).json()
    assert saldos["cliente"]["abonado"] == "40.00"
    assert saldos["comision"]["estado"] == "pendiente"

    r = _registrar_con_cobro(client, token, servicio_id, "completo")
    assert r.status_code == 201
    saldos = _saldos(client, token, r.json()["id"]).json()
    assert saldos["cliente"]["abonado"] == "100.00"
    assert saldos["cliente"]["estado"] == "pagado"
    assert saldos["comision"]["estado"] == "pendiente"


def test_cobro_parcial_sin_importe_400(client):
    """T38: parcial exige importe."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t38c", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    r = _registrar_con_cobro(client, _token_para(client, "barbero_t38c"), servicio_id, "parcial")
    assert r.status_code == 400


def _editar_corte(client, token, corte_id, body):
    return client.patch(
        f"/api/cortes/{corte_id}", json=body, headers={"Authorization": f"Bearer {token}"}
    )


def test_editar_metodo_conserva_importes(client):
    """T43: solo método → mismos precio/porcentaje/reparto."""
    corte_id = _corte_para_abonos(client, "barbero_t43")
    token = _token_para(client, "barbero_t43")

    respuesta = _editar_corte(client, token, corte_id, {"metodo_pago": "tarjeta"})
    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["metodo_pago"] == "tarjeta"
    assert data["precio"] == "100.00"
    assert data["parte_barbero"] == "50.00"


def test_editar_servicio_recalcula_valores_actuales(client):
    """T43 (RF-42): cambio de servicio → precio/porcentaje/reparto actuales."""
    from decimal import Decimal as DecimalT43

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t43b", Decimal("50"), Decimal("100.00"))
    db.add(
        Servicio(
            nombre="Servicio T43B",
            descripcion="Segundo servicio",
            precio=DecimalT43("200.00"),
            duracion_minutos=30,
            activo=True,
        )
    )
    db.commit()
    servicio2 = db.query(Servicio).filter(Servicio.nombre == "Servicio T43B").first().id
    db.close()

    corte_id = None
    db = TestingSessionLocal()
    servicio1 = db.query(Servicio).filter(Servicio.nombre == "Servicio T7").first()
    db.close()
    token = _token_para(client, "barbero_t43b")
    registro = client.post(
        "/api/cortes/",
        json={"servicio_id": servicio1.id, "metodo_pago": "efectivo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    corte_id = registro.json()["id"]

    respuesta = _editar_corte(client, token, corte_id, {"servicio_id": servicio2})
    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["precio"] == "200.00"
    assert data["parte_barbero"] == "100.00"


def test_editar_ajeno_404_y_servicio_invalido(client):
    """T43: ajeno → 404; servicio inexistente → 404."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t43c")
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero_t43d", RolModelo.BARBERO)
    db.close()

    assert _editar_corte(
        client, _token_para(client, "barbero_t43d"), corte_id, {"metodo_pago": "tarjeta"}
    ).status_code == 404
    assert _editar_corte(
        client, _token_para(client, "barbero_t43c"), corte_id, {"servicio_id": 9999}
    ).status_code == 404


def test_editar_bloqueado_409_y_abono_sigue_201(client):
    """T44 (RF-23/25): con pagos, el barbero no edita (409) pero sí abona."""
    corte_id = _corte_para_abonos(client, "barbero_t44")
    token = _token_para(client, "barbero_t44")

    assert _abonar(client, token, corte_id, "cliente", 10).status_code == 201
    respuesta = _editar_corte(client, token, corte_id, {"metodo_pago": "tarjeta"})
    assert respuesta.status_code == 409
    assert "bloqueado" in respuesta.json()["detail"].lower()
    assert _abonar(client, token, corte_id, "cliente", 10).status_code == 201


def test_admin_edita_bloqueado_200(client):
    """T44: el admin gestiona bloqueados (enforcement solo barbero)."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t44b")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t44", RolModelo.ADMIN)
    db.close()

    assert _abonar(
        client, _token_para(client, "barbero_t44b"), corte_id, "cliente", 10
    ).status_code == 201
    # T46: el admin en bloqueado exige motivo (contrato actualizado).
    respuesta = client.patch(
        f"/api/cortes/{corte_id}",
        json={"metodo_pago": "tarjeta", "motivo": "ajuste administrativo"},
        headers={"Authorization": f"Bearer {_token_para(client, 'admin_t44')}"},
    )
    assert respuesta.status_code == 200


def _anular_corte(client, token, corte_id, motivo=None):
    body = {"motivo": motivo} if motivo is not None else {}
    return client.post(
        f"/api/cortes/{corte_id}/anular",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_anular_propio_no_bloqueado_con_marca(client):
    """T45: anulación propia con marca visible; sin reactivación."""
    corte_id = _corte_para_abonos(client, "barbero_t45")
    token = _token_para(client, "barbero_t45")

    r = _anular_corte(client, token, corte_id)
    assert r.status_code == 200
    assert r.json()["anulado_en"] is not None

    historial = client.get(
        "/api/cortes/mi/historial", headers={"Authorization": f"Bearer {token}"}
    )
    assert historial.json()[0]["anulado_en"] is not None

    assert _anular_corte(client, token, corte_id).status_code == 409
    assert _editar_corte(client, token, corte_id, {"metodo_pago": "tarjeta"}).status_code == 409


def test_anular_bloqueado_barbero_409(client):
    """T45 (split T44): el barbero no anula bloqueados."""
    corte_id = _corte_para_abonos(client, "barbero_t45b")
    token = _token_para(client, "barbero_t45b")

    assert _abonar(client, token, corte_id, "cliente", 10).status_code == 201
    r = _anular_corte(client, token, corte_id)
    assert r.status_code == 409
    assert "bloqueado" in r.json()["detail"].lower()


def test_admin_corrige_bloqueado_exige_motivo(client):
    """T46 (RF-26): admin en bloqueado sin motivo → 400; con motivo → 200."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t46")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t46", RolModelo.ADMIN)
    db.close()
    token_admin = _token_para(client, "admin_t46")
    token_barbero = _token_para(client, "barbero_t46")

    assert _abonar(client, token_barbero, corte_id, "cliente", 10).status_code == 201

    r = _editar_corte(client, token_admin, corte_id, {"metodo_pago": "tarjeta"})
    assert r.status_code == 400
    r = client.patch(
        f"/api/cortes/{corte_id}",
        json={"metodo_pago": "tarjeta", "motivo": "corrige método mal cargado"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    assert r.json()["metodo_pago"] == "tarjeta"

    r = _anular_corte(client, token_admin, corte_id)
    assert r.status_code == 400
    r = _anular_corte(client, token_admin, corte_id, motivo="duplicado operativo")
    assert r.status_code == 200
    assert r.json()["anulado_motivo"] == "duplicado operativo"
    assert r.json()["anulado_en"] is not None


def test_journal_conserva_antes_despues_motivo_autor(client):
    """T46-bis (RF-26 pleno): cada edición/anulación deja journal con
    antes/después, motivo, autor y momento."""
    from app.models.auditoria_corte import AuditoriaCorte
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t46b")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t46b", RolModelo.ADMIN)
    db.close()
    token_admin = _token_para(client, "admin_t46b")

    r = client.patch(
        f"/api/cortes/{corte_id}",
        json={"metodo_pago": "tarjeta", "motivo": "corrige método"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200

    db = TestingSessionLocal()
    filas = db.query(AuditoriaCorte).filter(AuditoriaCorte.corte_id == corte_id).all()
    assert len(filas) == 1
    assert filas[0].accion == "edicion"
    assert filas[0].motivo == "corrige método"
    assert filas[0].antes["metodo_pago"] == "efectivo"
    assert filas[0].despues["metodo_pago"] == "tarjeta"
    assert filas[0].momento_utc is not None
    db.close()

    r = _anular_corte(client, token_admin, corte_id, motivo="cierre erróneo")
    assert r.status_code == 200

    db = TestingSessionLocal()
    filas = (
        db.query(AuditoriaCorte)
        .filter(AuditoriaCorte.corte_id == corte_id)
        .order_by(AuditoriaCorte.id)
        .all()
    )
    assert len(filas) == 2
    assert filas[1].accion == "anulacion"
    assert filas[1].motivo == "cierre erróneo"
    assert filas[1].antes["anulado_en"] is None
    assert filas[1].despues["anulado_en"] is not None
    db.close()


def test_anulado_fuera_de_devengado(client):
    """T47: el anulado no cuenta en reportes de devengado."""
    from app.models.usuario import Rol as RolModelo

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t47", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    _crear_usuario(db, "admin_t47", RolModelo.ADMIN)
    db.close()

    _login_y_registrar_corte(client, "barbero_t47", servicio_id)
    r2 = _login_y_registrar_corte(client, "barbero_t47", servicio_id)
    _anular_corte(client, _token_para(client, "barbero_t47"), r2.json()["id"])

    dashboard = client.get(
        "/api/reportes/dashboard",
        headers={"Authorization": f"Bearer {_token_para(client, 'admin_t47')}"},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["cortes_hoy"] == 1


def test_sin_abonos_al_anulado_y_movimientos_conservados(client):
    """T47 (RF-46 parcial): sin abonos ordinarios al anulado; previos visibles."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t47b")
    token = _token_para(client, "barbero_t47b")
    assert _abonar(client, token, corte_id, "cliente", 30).status_code == 201

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t47b", RolModelo.ADMIN)
    db.close()
    r = _anular_corte(
        client, _token_para(client, "admin_t47b"), corte_id, motivo="cierre con abono"
    )
    assert r.status_code == 200

    assert _abonar(client, token, corte_id, "cliente", 10).status_code == 409
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "30.00"


def test_edicion_anulacion_respetan_privacidad(client):
    """T48: ajeno → 404; respuestas sin datos del negocio; admin y listado OK."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t48")
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero_t48b", RolModelo.BARBERO)
    _crear_usuario(db, "admin_t48", RolModelo.ADMIN)
    db.close()
    token_ajeno = _token_para(client, "barbero_t48b")
    token_admin = _token_para(client, "admin_t48")

    assert _editar_corte(client, token_ajeno, corte_id, {"metodo_pago": "tarjeta"}).status_code == 404
    assert _anular_corte(client, token_ajeno, corte_id).status_code == 404

    r = _editar_corte(
        client, _token_para(client, "barbero_t48"), corte_id, {"metodo_pago": "tarjeta"}
    )
    assert r.status_code == 200
    assert _sin_campos_prohibidos(r.json()) == []

    r = _anular_corte(client, token_admin, corte_id, motivo="auditoría")
    assert r.status_code == 200
    assert _sin_campos_prohibidos(r.json()) == []

    listado = client.get(
        "/api/cortes/", headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert listado.status_code == 200
    assert listado.json()[0]["parte_barberia"] == "50.00"


def test_abono_mayor_al_restante_400(client):
    """T39: exceso online se rechaza sin crear movimiento."""
    from app.models.finanzas_corte import MovimientoCorte

    corte_id = _corte_para_abonos(client, "barbero_t39")
    token = _token_para(client, "barbero_t39")
    assert _abonar(client, token, corte_id, "cliente", 60).status_code == 201
    assert _abonar(client, token, corte_id, "cliente", 50).status_code == 400
    db = TestingSessionLocal()
    assert db.query(MovimientoCorte).count() == 1
    db.close()


def test_corte_bloqueado_desde_primer_abono(client):
    """T39 (RF-23/25 base): bloqueo calculado desde el primer pago."""
    from decimal import Decimal as DecimalT39
    from app.models.corte import MetodoPago as MetodoT39
    from app.models.finanzas_corte import ConceptoMovimiento as ConceptoT39
    from app.services.corte_service import crear_corte as crear_corte_t39
    from app.services.movimiento_corte_service import (
        corte_bloqueado,
        registrar_abono,
    )

    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t39b", Decimal("50"), Decimal("100.00"))
    actor = db.query(Usuario).filter(Usuario.usuario == "barbero_t39b").first()
    servicio_id = db.query(Servicio).first().id
    corte = crear_corte_t39(db, actor, servicio_id, "efectivo")
    assert corte_bloqueado(db, corte) is False
    registrar_abono(
        db,
        autor=actor,
        corte=corte,
        concepto=ConceptoT39.CLIENTE,
        importe=DecimalT39("10"),
        metodo=MetodoT39.EFECTIVO,
    )
    assert corte_bloqueado(db, corte) is True
    db.close()


def test_movimientos_respetan_privacidad(client):
    """T40: ajeno → 404; respuestas propias sin datos del negocio."""
    from app.models.usuario import Rol as RolModelo

    corte_id = _corte_para_abonos(client, "barbero_t40")
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero_t40b", RolModelo.BARBERO)
    db.close()
    token_ajeno = _token_para(client, "barbero_t40b")

    assert _abonar(client, token_ajeno, corte_id, "cliente", 10).status_code == 404
    assert _saldos(client, token_ajeno, corte_id).status_code == 404

    token = _token_para(client, "barbero_t40")
    assert _abonar(client, token, corte_id, "cliente", 10).status_code == 201
    assert _sin_campos_prohibidos(_saldos(client, token, corte_id).json()) == []

    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t40", RolModelo.ADMIN)
    db.close()
    assert _abonar(client, _token_para(client, "admin_t40"), corte_id, "cliente", 10).status_code == 201


def test_reintentos_agotados_sin_efecto_residual(client):
    """P2-3 paquete 5: contención persistente → ReintentosAgotados, sin filas."""
    from app.models.operacion_corte import OperacionCorte
    from app.services.operacion_corte_service import (
        ReintentosAgotados,
        ejecutar_operacion,
    )

    db = TestingSessionLocal()
    with pytest.raises(ReintentosAgotados):
        ejecutar_operacion(
            db,
            actor_id=1,
            namespace="web",
            operacion_id=None,
            accion="crear_corte",
            payload={"a": "b"},
            modo="online",
            ejecutar=lambda: {"estado": "aceptada"},
        )
    assert db.query(OperacionCorte).count() == 0
    db.close()


def test_resumen_personal_excluye_anulados(client):
    """Revisión paquete 7 (RF-27): el anulado no cuenta en resúmenes propios."""
    db = TestingSessionLocal()
    _crear_barbero_y_servicio(db, "barbero_t47c", Decimal("50"), Decimal("100.00"))
    servicio_id = db.query(Servicio).first().id
    db.close()

    _login_y_registrar_corte(client, "barbero_t47c", servicio_id)
    r2 = _login_y_registrar_corte(client, "barbero_t47c", servicio_id)
    _anular_corte(client, _token_para(client, "barbero_t47c"), r2.json()["id"])

    token = _token_para(client, "barbero_t47c")
    auth = {"Authorization": f"Bearer {token}"}
    for ruta in ("dia", "semana", "mes"):
        r = client.get(f"/api/cortes/mi/resumen/{ruta}", headers=auth)
        assert r.status_code == 200, ruta
        assert r.json()["total_cortes"] == 1, ruta


def _movimiento_directo(db, corte_id, actor_id, concepto, tipo, importe, estado=None):
    """T58: fila directa (simula estados que la API aún no produce)."""
    from app.models.corte import MetodoPago as MetodoAbono
    from app.models.finanzas_corte import MovimientoCorte as MovimientoModelo

    fila = MovimientoModelo(
        uuid=f"t58-{corte_id}-{concepto}-{tipo}-{importe}",
        corte_id=corte_id,
        concepto=concepto,
        tipo=tipo,
        importe=Decimal(importe),
        autor_id=actor_id,
        metodo_pago=MetodoAbono.EFECTIVO,
        estado=estado,
    )
    db.add(fila)
    db.commit()
    return fila


def test_saldos_exponen_excedente_sin_cambiar_restante(client):
    """T58 (RF-21): neto sobre obligación → excedente visible, restante 0."""
    from app.models.finanzas_corte import (
        ConceptoMovimiento as ConceptoT58,
        EstadoMovimiento as EstadoT58,
        TipoMovimiento as TipoT58,
    )

    corte_id = _corte_para_abonos(client, "barbero_t58")
    token = _token_para(client, "barbero_t58")
    db = TestingSessionLocal()
    actor_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t58").first().id
    _movimiento_directo(
        db, corte_id, actor_id, ConceptoT58.CLIENTE, TipoT58.ABONO, "150.00",
        EstadoT58.ACEPTADO,
    )
    db.close()
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "150.00"
    assert saldos["cliente"]["restante"] == "0.00"
    assert saldos["cliente"]["excedente"] == "50.00"


def test_revision_no_mueve_saldos_ni_excedente(client):
    """T58: la revisión sigue ignorada en saldos (RF-38/RF-53)."""
    from app.models.finanzas_corte import (
        ConceptoMovimiento as ConceptoT58b,
        EstadoMovimiento as EstadoT58b,
        TipoMovimiento as TipoT58b,
    )

    corte_id = _corte_para_abonos(client, "barbero_t58b")
    token = _token_para(client, "barbero_t58b")
    db = TestingSessionLocal()
    actor_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t58b").first().id
    _movimiento_directo(
        db, corte_id, actor_id, ConceptoT58b.CLIENTE, TipoT58b.ABONO, "150.00",
        EstadoT58b.REVISION,
    )
    db.close()
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "0.00"
    assert saldos["cliente"]["restante"] == "100.00"
    assert saldos["cliente"]["excedente"] == "0.00"


def test_compensacion_y_devolucion_mueven_neto(client):
    """T58 (RF-41/43): compensación con signo y devolución restan del neto."""
    from app.models.finanzas_corte import (
        ConceptoMovimiento as ConceptoT58c,
        EstadoMovimiento as EstadoT58c,
        TipoMovimiento as TipoT58c,
    )

    corte_id = _corte_para_abonos(client, "barbero_t58c")
    token = _token_para(client, "barbero_t58c")
    db = TestingSessionLocal()
    actor_id = db.query(Usuario).filter(Usuario.usuario == "barbero_t58c").first().id
    _movimiento_directo(
        db, corte_id, actor_id, ConceptoT58c.CLIENTE, TipoT58c.ABONO, "100.00",
        EstadoT58c.ACEPTADO,
    )
    _movimiento_directo(
        db, corte_id, actor_id, ConceptoT58c.CLIENTE, TipoT58c.COMPENSACION, "-30.00",
        EstadoT58c.ACEPTADO,
    )
    _movimiento_directo(
        db, corte_id, actor_id, ConceptoT58c.CLIENTE, TipoT58c.DEVOLUCION, "20.00",
        EstadoT58c.ACEPTADO,
    )
    db.close()
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "50.00"
    assert saldos["cliente"]["restante"] == "50.00"
    assert saldos["cliente"]["excedente"] == "0.00"


def _revision_por_exceso(client, login, importe="150.00"):
    """T59: genera una revisión vía sync offline (exceso sobre 100)."""
    import uuid as uuid_lib

    db = TestingSessionLocal()
    _crear_usuario(db, f"{login}_adm", Rol.ADMIN)
    db.close()
    corte_id = _corte_para_abonos(client, login)
    token = _token_para(client, login)
    uuid_val = str(uuid_lib.uuid4())
    r = client.post(
        "/api/sync/",
        headers={"Authorization": f"Bearer {token}"},
        json={"operaciones": [{
            "id": uuid_val,
            "accion": "registrar_abono_v2",
            "datos": {
                "operacion_uuid": uuid_val,
                "corte_id": corte_id,
                "concepto": "cliente",
                "importe": importe,
                "metodo_pago": "efectivo",
                "modo_captura": "offline",
            },
        }]},
    )
    assert r.json()["resultados"][0]["estado"] == "revision"
    return corte_id, uuid_val


def _resolver(client, admin_login, corte_id, mov_uuid, body):
    return client.post(
        f"/api/cortes/{corte_id}/revisiones/{mov_uuid}/resolver",
        json=body,
        headers={"Authorization": f"Bearer {_token_para(client, admin_login)}"},
    )


def test_resolver_revision_dinero_real_cubre_y_excedente(client):
    """T59 (RF-53): real íntegro → acepta original sin recorte; resto excedente."""
    corte_id, mov_uuid = _revision_por_exceso(client, "barbero_t59")
    admin = "barbero_t59_adm"
    r = _resolver(client, admin, corte_id, mov_uuid, {"veredicto": "real", "motivo": "verificado en caja"})
    assert r.status_code == 200
    assert r.json()["estado"] == "aceptado"
    assert r.json()["importe"] == "150.00"
    saldos = _saldos(client, _token_para(client, "barbero_t59"), corte_id).json()
    assert saldos["cliente"]["abonado"] == "150.00"
    assert saldos["cliente"]["restante"] == "0.00"
    assert saldos["cliente"]["excedente"] == "50.00"


def test_resolver_revision_erronea_crea_compensatoria(client):
    """T59 (RF-53): erróneo con real 50 → compensatoria +50; original intacto."""
    corte_id, mov_uuid = _revision_por_exceso(client, "barbero_t59b")
    admin = "barbero_t59b_adm"
    r = _resolver(
        client, admin, corte_id, mov_uuid,
        {"veredicto": "erroneo", "motivo": "duplicado con otro cobro", "importe_real": "50.00"},
    )
    assert r.status_code == 200
    assert r.json()["tipo"] == "compensacion"
    assert r.json()["importe"] == "50.00"
    assert r.json()["original_uuid"] == mov_uuid
    saldos = _saldos(client, _token_para(client, "barbero_t59b"), corte_id).json()
    assert saldos["cliente"]["abonado"] == "50.00"
    assert saldos["cliente"]["restante"] == "50.00"


def test_resolver_exige_motivo_y_admin(client):
    """T59: sin motivo → 400; barbero → 403; ya resuelta → 409."""
    corte_id, mov_uuid = _revision_por_exceso(client, "barbero_t59c")
    admin = "barbero_t59c_adm"
    assert _resolver(
        client, admin, corte_id, mov_uuid, {"veredicto": "real", "motivo": ""}
    ).status_code == 400
    assert _resolver(
        client, "barbero_t59c", corte_id, mov_uuid, {"veredicto": "real", "motivo": "x"}
    ).status_code == 403
    assert _resolver(
        client, admin, corte_id, mov_uuid, {"veredicto": "real", "motivo": "ok"}
    ).status_code == 200
    assert _resolver(
        client, admin, corte_id, mov_uuid, {"veredicto": "real", "motivo": "otra vez"}
    ).status_code == 409


def _compensar(client, admin_login, corte_id, body):
    return client.post(
        f"/api/cortes/{corte_id}/compensaciones",
        json=body,
        headers={"Authorization": f"Bearer {_token_para(client, admin_login)}"},
    )


def test_compensacion_corrige_sin_borrar_original(client):
    """T60 (RF-43): compensatoria −30 con motivo y referencia; original intacto."""
    from app.models.finanzas_corte import MovimientoCorte as MovimientoT60

    corte_id = _corte_para_abonos(client, "barbero_t60")
    token = _token_para(client, "barbero_t60")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t60", Rol.ADMIN)
    db.close()
    original_uuid = _abonar(client, token, corte_id, "cliente", 100).json()["uuid"]
    r = _compensar(client, "admin_t60", corte_id, {
        "concepto": "cliente",
        "importe": "-30.00",
        "motivo": "cobro duplicado parcial",
        "original_uuid": original_uuid,
    })
    assert r.status_code == 201
    assert r.json()["tipo"] == "compensacion"
    assert r.json()["original_uuid"] == original_uuid
    db = TestingSessionLocal()
    original = db.query(MovimientoT60).filter(MovimientoT60.uuid == original_uuid).first()
    assert original.importe == Decimal("100.00")
    db.close()
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "70.00"
    assert saldos["cliente"]["restante"] == "30.00"


def test_compensacion_exige_motivo_original_y_admin(client):
    """T60: sin motivo → 400; original inexistente → 404; barbero → 403; cero → 400."""
    corte_id = _corte_para_abonos(client, "barbero_t60b")
    token = _token_para(client, "barbero_t60b")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t60b", Rol.ADMIN)
    db.close()
    base = {"concepto": "cliente", "importe": "-10.00", "original_uuid": "inexistente"}
    assert _compensar(client, "admin_t60b", corte_id, {**base, "motivo": ""}).status_code == 400
    assert _compensar(
        client, "admin_t60b", corte_id, {**base, "motivo": "m"}
    ).status_code == 404
    assert _compensar(
        client, "barbero_t60b", corte_id, {**base, "motivo": "m"}
    ).status_code == 403
    original_uuid = _abonar(client, token, corte_id, "cliente", 50).json()["uuid"]
    assert _compensar(client, "admin_t60b", corte_id, {
        "concepto": "cliente", "importe": "0.00",
        "motivo": "cero", "original_uuid": original_uuid,
    }).status_code == 400


def _devolver(client, admin_login, corte_id, body):
    return client.post(
        f"/api/cortes/{corte_id}/devoluciones",
        json=body,
        headers={"Authorization": f"Bearer {_token_para(client, admin_login)}"},
    )


def test_devolucion_limite_y_capacidad(client):
    """T61 (RF-41): dentro de capacidad → 201 y reduce neto; exceso → 400."""
    corte_id = _corte_para_abonos(client, "barbero_t61")
    token = _token_para(client, "barbero_t61")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t61", Rol.ADMIN)
    db.close()
    assert _abonar(client, token, corte_id, "cliente", 100).status_code == 201
    r = _devolver(client, "admin_t61", corte_id, {
        "concepto": "cliente", "importe": "30.00", "motivo": "cobro de más",
    })
    assert r.status_code == 201
    assert r.json()["tipo"] == "devolucion"
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "70.00"
    assert _devolver(client, "admin_t61", corte_id, {
        "concepto": "cliente", "importe": "80.00", "motivo": "exceso",
    }).status_code == 400


def test_devolucion_concurrente_solo_una_consume(client):
    """T61: dos devoluciones de 30 sobre capacidad 40 → una 201 y otra 400."""
    import concurrent.futures

    corte_id = _corte_para_abonos(client, "barbero_t61b")
    token = _token_para(client, "barbero_t61b")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t61b", Rol.ADMIN)
    db.close()
    assert _abonar(client, token, corte_id, "cliente", 100).status_code == 201
    assert _devolver(client, "admin_t61b", corte_id, {
        "concepto": "cliente", "importe": "60.00", "motivo": "primera",
    }).status_code == 201
    cuerpo = {"concepto": "cliente", "importe": "30.00", "motivo": "carrera"}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        estados = sorted(
            pool.map(lambda _: _devolver(client, "admin_t61b", corte_id, cuerpo).status_code, range(2))
        )
    assert estados == [201, 400]


def test_devolucion_reintento_y_permisos(client):
    """T61: misma UUID no duplica; sin motivo → 400; barbero → 403."""
    import uuid as uuid_lib
    from app.models.finanzas_corte import MovimientoCorte as MovimientoT61

    corte_id = _corte_para_abonos(client, "barbero_t61c")
    token = _token_para(client, "barbero_t61c")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t61c", Rol.ADMIN)
    db.close()
    assert _abonar(client, token, corte_id, "cliente", 100).status_code == 201
    uuid_val = str(uuid_lib.uuid4())
    cuerpo = {
        "concepto": "cliente", "importe": "10.00", "motivo": "ajuste",
        "operacion_uuid": uuid_val,
    }
    assert _devolver(client, "admin_t61c", corte_id, cuerpo).status_code == 201
    assert _devolver(client, "admin_t61c", corte_id, cuerpo).status_code == 201
    db = TestingSessionLocal()
    assert db.query(MovimientoT61).filter(MovimientoT61.uuid == uuid_val).count() == 1
    db.close()
    assert _devolver(client, "admin_t61c", corte_id, {
        "concepto": "cliente", "importe": "5.00", "motivo": "",
    }).status_code == 400
    assert _devolver(client, "barbero_t61c", corte_id, {
        "concepto": "cliente", "importe": "5.00", "motivo": "m",
    }).status_code == 403


def _anular_como_admin(client, admin_login, corte_id, motivo="anulacion T62"):
    return _anular_corte(client, _token_para(client, admin_login), corte_id, motivo)


def test_correctivos_admin_al_anulado_201(client):
    """T62 (RF-46): ordinario al anulado → 409; compensación/devolución admin → 201."""
    corte_id = _corte_para_abonos(client, "barbero_t62")
    token = _token_para(client, "barbero_t62")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t62", Rol.ADMIN)
    db.close()
    assert _abonar(client, token, corte_id, "cliente", 30).status_code == 201
    original_uuid = _abonar(client, token, corte_id, "comision", 10).json()["uuid"]
    assert _anular_como_admin(client, "admin_t62", corte_id).status_code == 200
    assert _abonar(client, token, corte_id, "cliente", 10).status_code == 409
    assert _compensar(client, "admin_t62", corte_id, {
        "concepto": "cliente", "importe": "-5.00",
        "motivo": "ajuste anulado", "original_uuid": original_uuid,
    }).status_code == 201
    assert _devolver(client, "admin_t62", corte_id, {
        "concepto": "cliente", "importe": "5.00", "motivo": "excedente anulado",
    }).status_code == 201


def test_anular_cancela_obligaciones_y_neto_a_excedente(client):
    """T62 (RF-27/46): al anular con 30/100, restante 0 y excedente 30."""
    from app.models.auditoria_corte import AuditoriaCorte as AuditoriaT62

    corte_id = _corte_para_abonos(client, "barbero_t62b")
    token = _token_para(client, "barbero_t62b")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t62b", Rol.ADMIN)
    db.close()
    assert _abonar(client, token, corte_id, "cliente", 30).status_code == 201
    assert _anular_como_admin(client, "admin_t62b", corte_id).status_code == 200
    saldos = _saldos(client, token, corte_id).json()
    assert saldos["cliente"]["abonado"] == "30.00"
    assert saldos["cliente"]["restante"] == "0.00"
    assert saldos["cliente"]["excedente"] == "30.00"
    db = TestingSessionLocal()
    fila = db.query(AuditoriaT62).filter(AuditoriaT62.corte_id == corte_id).all()
    assert any(
        (r.despues or {}).get("obligaciones_canceladas") is True for r in fila
    )
    db.close()


def _movimientos_de(client, token, corte_id):
    return client.get(
        f"/api/cortes/{corte_id}/movimientos",
        headers={"Authorization": f"Bearer {token}"},
    )


def test_barbero_ve_motivos_en_lo_propio(client):
    """T63: motivos de correctivos propios visibles; sin datos del negocio."""
    corte_id = _corte_para_abonos(client, "barbero_t63")
    token = _token_para(client, "barbero_t63")
    db = TestingSessionLocal()
    _crear_usuario(db, "admin_t63", Rol.ADMIN)
    db.close()
    original_uuid = _abonar(client, token, corte_id, "cliente", 100).json()["uuid"]
    assert _compensar(client, "admin_t63", corte_id, {
        "concepto": "cliente", "importe": "-20.00",
        "motivo": "cobro duplicado", "original_uuid": original_uuid,
    }).status_code == 201
    r = _movimientos_de(client, token, corte_id)
    assert r.status_code == 200
    motivos = [m["motivo"] for m in r.json()]
    assert "cobro duplicado" in motivos
    assert _sin_campos_prohibidos(r.json()) == []


def test_movimientos_ajeno_404_y_detector_extendido(client):
    """T63 (RF-14/RNF-5): ajeno → 404 idéntico; detector limpio en saldos y correctivos."""
    from app.models.usuario import Rol as RolT63

    corte_id = _corte_para_abonos(client, "barbero_t63b")
    token = _token_para(client, "barbero_t63b")
    db = TestingSessionLocal()
    _crear_usuario(db, "barbero_t63c", RolT63.BARBERO)
    _crear_usuario(db, "admin_t63b", RolT63.ADMIN)
    db.close()
    assert _movimientos_de(client, _token_para(client, "barbero_t63c"), corte_id).status_code == 404
    assert _movimientos_de(client, _token_para(client, "admin_t63b"), corte_id).status_code == 200
    assert _sin_campos_prohibidos(_saldos(client, token, corte_id).json()) == []
    assert _abonar(client, token, corte_id, "cliente", 100).status_code == 201
    r = _devolver(client, "admin_t63b", corte_id, {
        "concepto": "cliente", "importe": "10.00", "motivo": "devolución menor",
    })
    assert r.status_code == 201
    assert _sin_campos_prohibidos(r.json()) == []
