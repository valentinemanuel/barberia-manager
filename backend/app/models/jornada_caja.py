from datetime import datetime
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
import enum

from app.database import Base


class EstadoJornada(str, enum.Enum):
    """Estado de la jornada de negocio (paquete 11, RF-45 parcial).

    Solo transiciones abierta → cerrada, por admin explícito. Sin
    reapertura ni apertura automática.
    """

    ABIERTA = "abierta"
    CERRADA = "cerrada"


class JornadaCaja(Base):
    """Jornada de negocio en `America/Argentina/Buenos_Aires`.

    Día calendario [00:00, 00:00 siguiente). No es el cierre legacy
    (`cierre_caja`, snapshot aportado): tablas y endpoints separados.
    """

    __tablename__ = "jornadas_caja"

    id = Column(Integer, primary_key=True, index=True)
    fecha_negocio = Column(Date, nullable=False, unique=True)
    estado = Column(Enum(EstadoJornada), nullable=False)
    abierta_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    abierta_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    cerrada_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    cerrada_en = Column(DateTime, nullable=True)


class PertenenciaCierre(Base):
    """Cortes incorporados a una jornada (paquete 11, RF-49 parcial).

    Inmutable: el snapshot se congela al incorporar; los tardíos se
    vinculan por ajuste sin tocar el snapshot original.
    """

    __tablename__ = "pertenencias_cierre"
    __table_args__ = (
        UniqueConstraint("jornada_id", "corte_id", name="uq_pertenencia"),
    )

    id = Column(Integer, primary_key=True, index=True)
    jornada_id = Column(Integer, ForeignKey("jornadas_caja.id"), nullable=False)
    corte_id = Column(Integer, ForeignKey("cortes.id"), nullable=False)
    servicio_id = Column(Integer, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    porcentaje_barbero = Column(Numeric(5, 2), nullable=False)
    parte_barbero = Column(Numeric(10, 2), nullable=False)
    version_corte = Column(Integer, nullable=False)
