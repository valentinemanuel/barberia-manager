from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
import enum

from app.database import Base
from app.models.corte import MetodoPago


class ConceptoMovimiento(str, enum.Enum):
    """Concepto independiente del movimiento (RF-13/RF-16)."""

    CLIENTE = "cliente"
    COMISION = "comision"


class TipoMovimiento(str, enum.Enum):
    """Tipo de movimiento (paquete 9, RF-41/RF-43 parcial).

    ABONO: abono ordinario positivo. COMPENSACION: corrección
    administrativa con motivo y referencia al original (puede restar).
    DEVOLUCION: devolución explícita de dinero real (resta del neto).
    """

    ABONO = "abono"
    COMPENSACION = "compensacion"
    DEVOLUCION = "devolucion"


class EstadoMovimiento(str, enum.Enum):
    """Aceptación del movimiento (paquete 8, T52, RF-38/RF-51 parcial).

    `REVISION` conserva el importe real pendiente de decisión admin,
    sin mover saldos aceptados. Nulos legacy se leen como aceptados.
    """

    ACEPTADO = "aceptado"
    REVISION = "revision"


class MovimientoCorte(Base):
    """Abono a un corte por concepto (paquete 6, RF-16/RF-17).

    Append-only: sin edición ni borrado. El importe es canónico
    (validado en frontera, nunca normalizado).
    """

    __tablename__ = "movimientos_corte"
    __table_args__ = (
        UniqueConstraint("uuid", name="uq_movimiento_uuid"),
    )

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), nullable=False)
    corte_id = Column(Integer, ForeignKey("cortes.id"), nullable=False)
    concepto = Column(Enum(ConceptoMovimiento), nullable=False)
    tipo = Column(Enum(TipoMovimiento), default=TipoMovimiento.ABONO, nullable=False)
    importe = Column(Numeric(10, 2), nullable=False)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    metodo_pago = Column(Enum(MetodoPago), nullable=False)
    momento_real = Column(DateTime, nullable=True)
    registrado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Revisión offline (paquete 8, T52): nulos legacy = aceptados.
    estado = Column(Enum(EstadoMovimiento), nullable=True)
    motivo_revision = Column(String(64), nullable=True)
    # Correctivos (paquete 9, T58): referencia al original, motivo y
    # evidencia. Solo en filas COMPENSACION/DEVOLUCION; nulos = abono común.
    original_uuid = Column(String(36), nullable=True)
    motivo = Column(String(255), nullable=True)
    evidencia = Column(String(255), nullable=True)
    # Titular del dinero (paquete 10, T66): profesional al que pertenece una
    # comisión. Nulo en cliente (la deuda es del corte) y en legacy, que se
    # rellena en la migración 008 con el titular vigente entonces.
    profesional_id = Column(Integer, nullable=True)
