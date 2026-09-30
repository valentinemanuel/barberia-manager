from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CategoriaGasto(str, enum.Enum):
    ALQUILER = "alquiler"
    SERVICIOS = "servicios"
    INSUMOS = "insumos"
    OTROS = "otros"


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String(255), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    categoria = Column(Enum(CategoriaGasto), default=CategoriaGasto.OTROS, nullable=False)
    registrado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)

    registrado_por = relationship("Usuario", backref="gastos")
