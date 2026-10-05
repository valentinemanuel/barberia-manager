from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from app.models.auditoria import AccionAuditoria


class AuditoriaResponse(BaseModel):
    id: int
    actor_id: int
    accion: AccionAuditoria
    usuario_afectado_id: int
    valor_anterior: Optional[dict] = None
    valor_nuevo: dict
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditoriaListResponse(BaseModel):
    items: List[AuditoriaResponse]
    total: int
    skip: int
    limit: int
