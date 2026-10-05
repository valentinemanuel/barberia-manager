import json
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.models.auditoria import Auditoria, AccionAuditoria


def _serializar_valor(valor) -> Optional[Any]:
    """Convierte un valor a estructura JSON-serializable (dict)."""
    if valor is None:
        return None
    return json.loads(json.dumps(valor, default=str, ensure_ascii=False))


def registrar_auditoria(
    db: Session,
    actor_id: int,
    accion: AccionAuditoria,
    usuario_afectado_id: int,
    valor_anterior,
    valor_nuevo,
) -> Auditoria:
    """
    Registra un evento de auditoría.

    Los valores se serializan a JSON. En `crear_usuario`, valor_anterior debe
    ser None (null). El timestamp se guarda en UTC.
    """
    registro = Auditoria(
        actor_id=actor_id,
        accion=accion,
        usuario_afectado_id=usuario_afectado_id,
        valor_anterior=_serializar_valor(valor_anterior),
        valor_nuevo=_serializar_valor(valor_nuevo),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro
