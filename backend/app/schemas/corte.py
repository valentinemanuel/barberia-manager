from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional
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

    class Config:
        from_attributes = True
