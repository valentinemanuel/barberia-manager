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


class AccionAuditoriaCorte(str, enum.Enum):
    """Acción registrada en el journal (paquete 7, RF-26).

    El paquete de auditoría podrá agregar acciones correctivas.
    """

    EDICION = "edicion"
    ANULACION = "anulacion"
    # Correctivos monetarios (paquete 9, RF-43/RF-53 parcial).
    RESOLUCION = "resolucion"
    COMPENSACION = "compensacion"
    DEVOLUCION = "devolucion"


class AuditoriaCorte(Base):
    """Journal append-only de ediciones y anulaciones (RF-26).

    Conserva autor, momento, motivo y valores anteriores/posteriores
    como snapshots explícitos. Sin edición ni borrado.
    """

    __tablename__ = "auditoria_corte"

    id = Column(Integer, primary_key=True, index=True)
    corte_id = Column(Integer, ForeignKey("cortes.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    accion = Column(Enum(AccionAuditoriaCorte), nullable=False)
    antes = Column(JSON, nullable=False)
    despues = Column(JSON, nullable=False)
    motivo = Column(String(255), nullable=True)
    momento_utc = Column(DateTime, default=datetime.utcnow, nullable=False)
