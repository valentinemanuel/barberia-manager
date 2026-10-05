from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin
from app.models.auditoria import Auditoria
from app.models.usuario import Usuario
from app.schemas.auditoria import AuditoriaListResponse

router = APIRouter(prefix="/api/auditoria", tags=["Auditoria"])


@router.get("", response_model=AuditoriaListResponse)
def listar_auditoria(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Lista registros de auditoría, solo admin, ordenados por timestamp desc."""
    query = db.query(Auditoria).order_by(Auditoria.timestamp.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return AuditoriaListResponse(items=items, total=total, skip=skip, limit=limit)
