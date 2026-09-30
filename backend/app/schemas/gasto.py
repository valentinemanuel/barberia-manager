from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

from app.models.gasto import CategoriaGasto


class GastoBase(BaseModel):
    concepto: str = Field(..., min_length=1, max_length=255)
    monto: Decimal = Field(..., gt=0)
    categoria: CategoriaGasto = CategoriaGasto.OTROS


class GastoCrear(GastoBase):
    pass


class GastoResponse(GastoBase):
    id: int
    registrado_por_id: int
    fecha: datetime

    class Config:
        from_attributes = True
