from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.schemas.servicio import ServicioCrear, ServicioActualizar, ServicioResponse

router = APIRouter(prefix="/api/servicios", tags=["Servicios"])


@router.get("/", response_model=list[ServicioResponse])
def listar_servicios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Lista todos los servicios activos."""
    return db.query(Servicio).filter(Servicio.activo == True).all()


@router.get("/{servicio_id}", response_model=ServicioResponse)
def obtener_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene un servicio por ID."""
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return servicio


@router.post("/", response_model=ServicioResponse, status_code=status.HTTP_201_CREATED)
def crear_servicio(
    datos: ServicioCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Crea un nuevo servicio (solo admin)."""
    nuevo = Servicio(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/{servicio_id}", response_model=ServicioResponse)
def actualizar_servicio(
    servicio_id: int,
    datos: ServicioActualizar,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Actualiza un servicio (solo admin)."""
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(servicio, campo, valor)

    db.commit()
    db.refresh(servicio)
    return servicio


@router.delete("/{servicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Elimina un servicio (solo admin)."""
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    servicio.activo = False
    db.commit()
    return None
