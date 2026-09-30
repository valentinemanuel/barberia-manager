from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.consumible import Consumible
from app.models.usuario import Usuario
from app.schemas.consumible import ConsumibleCrear, ConsumibleActualizar, ConsumibleResponse

router = APIRouter(prefix="/api/consumibles", tags=["Consumibles"])


@router.get("/", response_model=list[ConsumibleResponse])
def listar_consumibles(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Lista todos los consumibles activos."""
    return db.query(Consumible).filter(Consumible.activo == True).all()


@router.get("/{consumible_id}", response_model=ConsumibleResponse)
def obtener_consumible(
    consumible_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene un consumible por ID."""
    consumible = db.query(Consumible).filter(Consumible.id == consumible_id).first()
    if not consumible:
        raise HTTPException(status_code=404, detail="Consumible no encontrado")
    return consumible


@router.post("/", response_model=ConsumibleResponse, status_code=status.HTTP_201_CREATED)
def crear_consumible(
    datos: ConsumibleCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Crea un nuevo consumible (solo admin)."""
    nuevo = Consumible(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/{consumible_id}", response_model=ConsumibleResponse)
def actualizar_consumible(
    consumible_id: int,
    datos: ConsumibleActualizar,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Actualiza un consumible (solo admin)."""
    consumible = db.query(Consumible).filter(Consumible.id == consumible_id).first()
    if not consumible:
        raise HTTPException(status_code=404, detail="Consumible no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(consumible, campo, valor)

    db.commit()
    db.refresh(consumible)
    return consumible


@router.delete("/{consumible_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_consumible(
    consumible_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Elimina un consumible (solo admin)."""
    consumible = db.query(Consumible).filter(Consumible.id == consumible_id).first()
    if not consumible:
        raise HTTPException(status_code=404, detail="Consumible no encontrado")
    consumible.activo = False
    db.commit()
    return None
