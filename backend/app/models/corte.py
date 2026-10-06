from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Enum, Boolean, String
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class MetodoPago(str, enum.Enum):
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"


class Corte(Base):
    __tablename__ = "cortes"

    id = Column(Integer, primary_key=True, index=True)
    barbero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    porcentaje_barbero = Column(Numeric(5, 2), nullable=False)
    parte_barbero = Column(Numeric(10, 2), nullable=False)
    parte_barberia = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(Enum(MetodoPago), default=MetodoPago.EFECTIVO, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    sincronizado = Column(Boolean, default=True, nullable=False)
    # Anulación terminal (paquete 7, RF-27/46 parcial): sin borrado ni
    # reactivación. La pertenencia a cierre corresponde a jornadas.
    anulado_en = Column(DateTime, nullable=True)
    anulado_motivo = Column(String(255), nullable=True)
    anulado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    barbero = relationship("Usuario", backref="cortes")
    servicio = relationship("Servicio", backref="cortes")
