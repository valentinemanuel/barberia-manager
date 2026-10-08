from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
)
import enum

from app.database import Base


class EstadoIntervencion(str, enum.Enum):
    """Estado de la intervención (paquete 10, RF-40 parcial).

    Revisión manual: el admin la aplica o descarta con motivo; el sistema
    nunca la auto-aplica.
    """

    PENDIENTE = "pendiente"
    APLICADA = "aplicada"
    DESCARTADA = "descartada"


class IntervencionCorte(Base):
    """Edición/anulación offline que llegó tras un bloqueo (RF-40).

    Se conserva con su causa sin aplicarse; la resolución es manual del
    admin. Idempotente por UUID (replay no duplica).
    """

    __tablename__ = "intervenciones_corte"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), nullable=False, unique=True)
    corte_id = Column(Integer, ForeignKey("cortes.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    accion = Column(String(16), nullable=False)
    cambios = Column(JSON, nullable=False)
    causa = Column(String(64), nullable=False)
    estado = Column(Enum(EstadoIntervencion), nullable=False)
    motivo_resolucion = Column(String(255), nullable=True)
    creada_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    resuelta_en = Column(DateTime, nullable=True)
    resuelta_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
