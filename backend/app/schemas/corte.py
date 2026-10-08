from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID
import enum

from app.models.corte import MetodoPago


class CorteBase(BaseModel):
    servicio_id: int
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO


class CobroInicial(str, enum.Enum):
    """Elección de cobro del cliente al registrar (RF-37, sin default)."""

    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    COMPLETO = "completo"


class CorteCrear(CorteBase):
    # Solo admin: barbero destinatario. Si lo envía un barbero → 403.
    barbero_id: Optional[int] = None
    # Solo admin: momento real retroactivo (nunca futuro). Barbero → 400.
    momento_real: Optional[datetime] = None
    # Idempotencia opcional (paquete 5): sin UUID → camino legacy intacto.
    operacion_uuid: Optional[UUID] = None
    # Cobro inicial del cliente (paquete 6, RF-37): sin elección → pendiente.
    cobro_inicial: Optional[CobroInicial] = None
    importe_cobro: Optional[Decimal] = None


class CorteEditar(BaseModel):
    """Edición parcial (paquete 7, RF-22/RF-42): servicio y/o método."""

    servicio_id: Optional[int] = None
    metodo_pago: Optional[MetodoPago] = None
    # Motivo obligatorio para admin sobre bloqueado (RF-26); se exige pero
    # su journal completo corresponde al paquete de auditoría.
    motivo: Optional[str] = None
    # Concurrencia LWW (paquete 10, RF-36): instante de la edición y bases
    # vistas por el cliente (informativas; la resolución es por instante).
    instante_cambio: Optional[datetime] = None
    bases: Optional[dict] = None
    operacion_uuid: Optional[str] = None
    # Reasignación y fecha (paquete 10, RF-42/RF-47): solo admin con motivo.
    barbero_id: Optional[int] = None
    momento_real: Optional[datetime] = None


class CorteAnular(BaseModel):
    """Anulación (paquete 7, RF-27): motivo obligatorio para admin en bloqueado."""

    motivo: Optional[str] = None


class IntervencionResolver(BaseModel):
    """Resolución manual de una intervención RF-40 (paquete 10)."""

    decision: Literal["aplicar", "descartar"]
    motivo: str


class IntervencionResponse(BaseModel):
    uuid: str
    corte_id: int
    accion: str
    estado: str
    causa: str

    class Config:
        from_attributes = True


class JustificanteResponse(BaseModel):
    """Justificante propio post-reasignación (paquete 10, RF-48).

    Sin titular del corte ni datos de otros profesionales.
    """

    corte_id: int
    uuid: str
    concepto: str
    tipo: Optional[str] = None
    importe: Decimal
    motivo: Optional[str] = None
    momento_real: Optional[datetime] = None
    registrado_en: datetime

    class Config:
        from_attributes = True


class CorteResponse(BaseModel):
    id: int
    barbero_id: int
    servicio_id: int
    precio: Decimal
    porcentaje_barbero: Decimal
    parte_barbero: Decimal
    parte_barberia: Decimal
    metodo_pago: MetodoPago
    fecha: datetime
    sincronizado: bool
    anulado_en: Optional[datetime] = None
    anulado_motivo: Optional[str] = None

    class Config:
        from_attributes = True


class CortePersonal(BaseModel):
    """Contrato personal (barbero): igual que CorteResponse pero SIN la
    parte de la barbería (gate §11.2). El listado global de admin y los
    reportes conservan el contrato completo."""

    id: int
    barbero_id: int
    servicio_id: int
    precio: Decimal
    porcentaje_barbero: Decimal
    parte_barbero: Decimal
    metodo_pago: MetodoPago
    fecha: datetime
    sincronizado: bool
    anulado_en: Optional[datetime] = None
    anulado_motivo: Optional[str] = None

    class Config:
        from_attributes = True


class CorteEdicionResponse(CortePersonal):
    """Respuesta de edición (paquete 10, RF-36): resultado por unidad.

    Aditiva sobre el contrato personal: cada unidad pedida informa
    `aplicada` u `omitida` (omitida nunca es silenciosa).
    """

    unidades: dict = {}
