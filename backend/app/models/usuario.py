from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, Enum
import enum

from app.database import Base


class Rol(str, enum.Enum):
    ADMIN = "admin"
    BARBERO = "barbero"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    usuario = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(Enum(Rol), default=Rol.BARBERO, nullable=False)
    porcentaje_ganancia = Column(Numeric(5, 2), default=0, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
