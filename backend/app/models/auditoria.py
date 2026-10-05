from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, JSON
import enum

from app.database import Base


class AccionAuditoria(str, enum.Enum):
    CREAR_USUARIO = "crear_usuario"
    CAMBIAR_ROL = "cambiar_rol"
    CAMBIAR_PORCENTAJE = "cambiar_porcentaje"
    CAMBIAR_ACTIVO = "cambiar_activo"


class Auditoria(Base):
    __tablename__ = "auditorias"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    accion = Column(Enum(AccionAuditoria), nullable=False)
    usuario_afectado_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    valor_anterior = Column(JSON, nullable=True)
    valor_nuevo = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
