"""Jornadas de negocio (paquete 11, RF-45 parcial).

Tablas y endpoints nuevos al lado del cierre legacy (`cierre_caja`,
snapshot aportado): ese flujo no se toca ni se reinterpreta.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin
from app.models.jornada_caja import EstadoJornada, JornadaCaja
from app.models.usuario import Usuario
from app.services.jornada_service import (
    JornadaExistente,
    JornadaInexistente,
    abrir_jornada,
    cerrar_jornada,
)

router = APIRouter(prefix="/api/jornadas", tags=["Jornadas"])


class JornadaAbrir(BaseModel):
    fecha: date


class JornadaResponse(BaseModel):
    id: int
    fecha_negocio: date
    estado: EstadoJornada

    class Config:
        from_attributes = True


@router.post("/abrir", response_model=JornadaResponse, status_code=201)
def abrir(
    datos: JornadaAbrir,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Apertura explícita de la jornada (solo admin, nunca automática)."""
    try:
        fila = abrir_jornada(db, admin=admin, fecha=datos.fecha)
    except JornadaExistente as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    db.refresh(fila)
    return fila


@router.post("/cerrar", response_model=JornadaResponse)
def cerrar(
    datos: JornadaAbrir,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Cierre inmutable de la jornada (solo admin, sin reapertura)."""
    try:
        fila = cerrar_jornada(db, admin=admin, fecha=datos.fecha)
    except (JornadaExistente, JornadaInexistente) as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    db.refresh(fila)
    return fila


@router.get("", response_model=list[JornadaResponse])
def listar(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Jornadas registradas (solo admin)."""
    return db.query(JornadaCaja).order_by(JornadaCaja.fecha_negocio).all()
