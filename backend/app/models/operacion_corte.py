from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
import enum

from app.database import Base


class EstadoOperacion(str, enum.Enum):
    """Estados terminales del paquete 5 (RF-32/RF-57 parcial).

    Revisión y dependencias corresponden a paquetes posteriores.
    """

    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"


class ModoCaptura(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class OperacionCorte(Base):
    """Journal idempotente mínimo (paquete 5).

    Clave única (actor, namespace, operación): el reintento con la misma
    clave y el mismo hash devuelve el acuse guardado sin reejecutar.
    """

    __tablename__ = "operaciones_corte"
    __table_args__ = (
        UniqueConstraint(
            "actor_id", "namespace_cliente", "operacion_id", name="uq_operacion_clave"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    namespace_cliente = Column(String(32), nullable=False)
    operacion_id = Column(String(36), nullable=False)
    accion = Column(String(32), nullable=False)
    hash_operacion = Column(String(64), nullable=False)
    modo_captura = Column(Enum(ModoCaptura), nullable=False)
    estado = Column(Enum(EstadoOperacion), nullable=False)
    resultado = Column(JSON, nullable=False)
    recibida_en = Column(DateTime, default=datetime.utcnow, nullable=False)
