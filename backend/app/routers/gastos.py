from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin
from app.models.gasto import Gasto
from app.models.usuario import Usuario
from app.schemas.gasto import GastoCrear, GastoResponse

router = APIRouter(prefix="/api/gastos", tags=["Gastos"])


@router.get("/", response_model=list[GastoResponse])
def listar_gastos(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
    skip: int = 0,
    limit: int = 100
):
    """Lista todos los gastos (solo admin)."""
    return db.query(Gasto).order_by(Gasto.fecha.desc()).offset(skip).limit(limit).all()


@router.get("/{gasto_id}", response_model=GastoResponse)
def obtener_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Obtiene un gasto por ID (solo admin)."""
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


@router.post("/", response_model=GastoResponse, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    datos: GastoCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Crea un nuevo gasto (solo admin)."""
    nuevo = Gasto(**datos.model_dump(), registrado_por_id=admin.id)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.delete("/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Elimina un gasto (solo admin)."""
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(gasto)
    db.commit()
    return None
