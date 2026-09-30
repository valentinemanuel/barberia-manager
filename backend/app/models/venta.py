from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class TipoVenta(str, enum.Enum):
    PRODUCTO = "producto"
    CONSUMIBLE = "consumible"


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(TipoVenta), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    consumible_id = Column(Integer, ForeignKey("consumibles.id"), nullable=True)
    cantidad = Column(Integer, default=1, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    corte_id = Column(Integer, ForeignKey("cortes.id"), nullable=True)
    barbero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    sincronizado = Column(Boolean, default=True, nullable=False)

    barbero = relationship("Usuario", backref="ventas")
    corte = relationship("Corte", backref="ventas")
