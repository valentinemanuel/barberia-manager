"""Movimientos de corte por concepto (paquete 6, RF-16–RF-21 parcial)."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import obtener_usuario_actual
from app.models.corte import Corte, MetodoPago
from app.models.finanzas_corte import ConceptoMovimiento
from app.models.usuario import Rol, Usuario
from app.services.movimiento_corte_service import registrar_abono

router = APIRouter(prefix="/api/cortes", tags=["Movimientos"])


class MovimientoCrear(BaseModel):
    concepto: ConceptoMovimiento
    importe: Decimal
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO
    momento_real: Optional[datetime] = None
    uuid: Optional[str] = None


class MovimientoResponse(BaseModel):
    id: int
    uuid: str
    concepto: ConceptoMovimiento
    importe: Decimal
    metodo_pago: MetodoPago
    momento_real: Optional[datetime] = None
    registrado_en: datetime

    class Config:
        from_attributes = True


def _corte_propio_o_gestion(
    db: Session, corte_id: int, actor: Usuario
) -> Corte:
    """Corte visible para el actor; ajeno/inexistente → 404 idéntico (RF-14)."""
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    if actor.rol != Rol.ADMIN and corte.barbero_id != actor.id:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    return corte


@router.post(
    "/{corte_id}/movimientos",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_movimiento(
    corte_id: int,
    datos: MovimientoCrear,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Registra un abono ordinario en un concepto del corte."""
    corte = _corte_propio_o_gestion(db, corte_id, actor)
    momento = datos.momento_real
    if momento is not None:
        if actor.rol != Rol.ADMIN:
            raise HTTPException(
                status_code=400, detail="Solo un admin puede indicar el momento real"
            )
        if momento.tzinfo is not None:
            momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
        if momento > datetime.utcnow():
            raise HTTPException(
                status_code=400, detail="El momento real no puede ser futuro"
            )
    try:
        movimiento = registrar_abono(
            db,
            autor=actor,
            corte=corte,
            concepto=datos.concepto,
            importe=datos.importe,
            metodo=datos.metodo_pago,
            momento_real=momento,
            uuid=datos.uuid,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.commit()
    db.refresh(movimiento)
    return movimiento
