from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

from app.models.corte import MetodoPago


class CorteBase(BaseModel):
    servicio_id: int
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO


class CorteCrear(CorteBase):
    pass


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
