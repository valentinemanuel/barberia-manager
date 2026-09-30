from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: Decimal = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    stock_minimo: int = Field(default=5, ge=0)


class ProductoCrear(ProductoBase):
    pass


class ProductoActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    activo: Optional[bool] = None


class ProductoResponse(ProductoBase):
    id: int
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True
