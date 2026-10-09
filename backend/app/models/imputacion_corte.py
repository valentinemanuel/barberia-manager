from datetime import date, datetime
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
import enum

from app.database import Base


class EstadoImputacion(str, enum.Enum):
    """Estado contable del movimiento (paquete 11, RF-45/RF-50 parcial).

    `PENDIENTE` requiere jornada abierta y mantiene el saldo financiero;
    no reabre cierres ni equivale a revisión.
    """

    IMPUTADO = "imputado"
    PENDIENTE = "pendiente"


class ImputacionMovimiento(Base):
    """Destino contable de un movimiento aceptado (una por movimiento).

    `jornada_real` deriva del momento real; `jornada_destino` es donde se
    imputa (la real si abierta, si no la abierta actual como ajuste).
    """

    __tablename__ = "imputaciones_movimiento"

    id = Column(Integer, primary_key=True, index=True)
    movimiento_uuid = Column(String(36), nullable=False, unique=True)
    jornada_real = Column(Date, nullable=False)
    jornada_destino_id = Column(Integer, ForeignKey("jornadas_caja.id"), nullable=True)
    estado = Column(Enum(EstadoImputacion), nullable=False)
    creada_en = Column(DateTime, default=datetime.utcnow, nullable=False)
