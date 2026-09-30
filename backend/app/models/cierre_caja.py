from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class CierreCaja(Base):
    __tablename__ = "cierres_caja"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False)
    total_cortes = Column(Numeric(10, 2), nullable=False)
    total_productos = Column(Numeric(10, 2), nullable=False)
    total_consumibles = Column(Numeric(10, 2), nullable=False)
    total_ingresos = Column(Numeric(10, 2), nullable=False)
    total_gastos = Column(Numeric(10, 2), nullable=False)
    total_en_caja = Column(Numeric(10, 2), nullable=False)
    monto_retirado = Column(Numeric(10, 2), nullable=False)
    diferencia = Column(Numeric(10, 2), nullable=False)
    realizado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    realizado_por = relationship("Usuario", backref="cierres_caja")
