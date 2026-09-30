from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

from app.models.venta import TipoVenta


class VentaBase(BaseModel):
    tipo: TipoVenta
    producto_id: Optional[int] = None
    consumible_id: Optional[int] = None
    cantidad: int = Field(default=1, gt=0)
    precio_unitario: Decimal = Field(..., gt=0)
    corte_id: Optional[int] = None


class VentaCrear(VentaBase):
    pass


class VentaResponse(BaseModel):
    id: int
    tipo: TipoVenta
    producto_id: Optional[int]
    consumible_id: Optional[int]
    cantidad: int
    precio_unitario: Decimal
    total: Decimal
    corte_id: Optional[int]
    barbero_id: int
    fecha: datetime
    sincronizado: bool

    class Config:
        from_attributes = True
