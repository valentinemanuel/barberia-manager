from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from typing import Optional


def _precio_canonico(valor: Optional[Decimal]) -> Optional[Decimal]:
    """RF-41: precio finito con hasta dos decimales, sin normalizar.

    La positividad la exige Field(gt=0); aquí solo finitud y precisión,
    porque el ORM redondea silenciosamente al leer Numeric.
    """
    if valor is None:
        return None
    if not isinstance(valor, Decimal):
        raise ValueError("El precio debe ser Decimal")
    if not valor.is_finite():
        raise ValueError("El precio debe ser finito")
    if valor.as_tuple().exponent < -2:
        raise ValueError("El precio debe tener como máximo dos decimales")
    return valor


class ServicioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: Decimal = Field(..., gt=0)
    duracion_minutos: int = Field(default=30, gt=0)


class ServicioCrear(ServicioBase):
    @field_validator("precio")
    @classmethod
    def _validar_precio(cls, valor: Decimal) -> Decimal:
        return _precio_canonico(valor)


class ServicioActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    precio: Optional[Decimal] = Field(None, gt=0)
    duracion_minutos: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = None

    @field_validator("precio")
    @classmethod
    def _validar_precio(cls, valor: Optional[Decimal]) -> Optional[Decimal]:
        return _precio_canonico(valor)


class ServicioResponse(ServicioBase):
    # Solo expone precio_venta (precio) al usuario autenticado.
    # No se incluyen costos ni márgenes.
    id: int
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True
