from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.models.usuario import Rol


class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    usuario: str = Field(..., min_length=3, max_length=50)
    rol: Rol = Rol.BARBERO
    porcentaje_ganancia: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class UsuarioCrear(UsuarioBase):
    password: str = Field(..., min_length=6, max_length=100)


class UsuarioActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    usuario: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    rol: Optional[Rol] = None
    porcentaje_ganancia: Optional[Decimal] = Field(None, ge=0, le=100)
    activo: Optional[bool] = None


class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    usuario: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    usuario_id: Optional[int] = None
    rol: Optional[Rol] = None
