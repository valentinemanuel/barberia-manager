from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class CierreCajaBase(BaseModel):
    fecha: datetime
    total_cortes: Decimal = Field(..., ge=0)
    total_productos: Decimal = Field(..., ge=0)
    total_consumibles: Decimal = Field(..., ge=0)
    total_ingresos: Decimal = Field(..., ge=0)
    total_gastos: Decimal = Field(..., ge=0)
    total_en_caja: Decimal = Field(..., ge=0)
    monto_retirado: Decimal = Field(..., ge=0)


class CierreCajaCrear(CierreCajaBase):
    pass


class CierreCajaResponse(CierreCajaBase):
    id: int
    diferencia: Decimal
    realizado_por_id: int
    creado_en: datetime

    class Config:
        from_attributes = True
