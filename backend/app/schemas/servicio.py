from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class ServicioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: Decimal = Field(..., gt=0)
    duracion_minutos: int = Field(default=30, gt=0)


class ServicioCrear(ServicioBase):
    pass


class ServicioActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: Optional[Decimal] = Field(None, gt=0)
    duracion_minutos: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = None


class ServicioResponse(ServicioBase):
    id: int
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True
