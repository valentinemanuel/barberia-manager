"""Servicio de invariantes de administración (RF-4, RF-4b, RF-4c, RF-5, RF-6)."""
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.usuario import Usuario, Rol

# Acciones soportadas por validar_cambio_admin
ACCION_PROMOVER = "promover_admin"
ACCION_DEGRADAR = "degradar_admin"
ACCION_DESACTIVAR = "desactivar"

ACCIONES_QUE_QUITAN_ADMIN = {ACCION_DEGRADAR, ACCION_DESACTIVAR}


def contar_admins_activos(db: Session) -> int:
    """Cuenta usuarios con rol admin y estado activo."""
    return (
        db.query(Usuario)
        .filter(Usuario.rol == Rol.ADMIN, Usuario.activo.is_(True))
        .count()
    )


def es_ultimo_admin(db: Session, usuario: Usuario) -> bool:
    """True si `usuario` es admin activo y es el único admin activo."""
    if usuario.rol != Rol.ADMIN or not usuario.activo:
        return False
    return contar_admins_activos(db) == 1


def validar_cambio_admin(
    db: Session,
    usuario_afectado: Usuario,
    accion: str,
    actor: Usuario,
) -> Optional[dict]:
    """
    Valida un cambio sobre el rol/estado de un admin.

    Devuelve None si el cambio es permitido, o un dict
    {"status_code": 409, "detail": ...} si viola el invariante
    (degradación/desactivación del último admin activo).

    - RF-6: promover a admin siempre se permite.
    - RF-4/RF-5: degradar/desactivar se permite mientras quede al menos
      otro admin activo (incluido que el actor se degrade/desactive a sí
      mismo cuando hay otro admin activo — RF-4b).
    - RF-4: si el cambio dejaría al sistema sin admin activo, 409.
    """
    if accion == ACCION_PROMOVER:
        return None

    if accion in ACCIONES_QUE_QUITAN_ADMIN:
        if es_ultimo_admin(db, usuario_afectado):
            return {
                "status_code": 409,
                "detail": (
                    "No se puede degradar ni desactivar al último "
                    "administrador activo"
                ),
            }
        return None

    # Acción desconocida: no afecta al invariante
    return None


def validar_y_aplicar_cambio_admin(
    db: Session,
    usuario_afectado: Usuario,
    accion: str,
    actor: Usuario,
    cambios: dict,
) -> Optional[dict]:
    """
    T6 — RF-4c: valida el invariante y aplica los cambios de forma ATÓMICA,
    con transacción bloqueante (SQLite: BEGIN IMMEDIATE).

    Devuelve None si todo salió bien, o un dict {"status_code", "detail"} con
    409 si el invariante se viola o hay conflicto de concurrencia.
    """
    try:
        db.execute(text("BEGIN IMMEDIATE"))
    except OperationalError:
        db.rollback()
        return {
            "status_code": 409,
            "detail": "Conflicto de concurrencia: la base está bloqueada, reintente",
        }

    try:
        # Releer estado vigente bajo el bloqueo
        db.refresh(usuario_afectado)

        error = validar_cambio_admin(db, usuario_afectado, accion, actor)
        if error is not None:
            db.rollback()
            return error

        for campo, valor in cambios.items():
            setattr(usuario_afectado, campo, valor)

        db.commit()
        return None
    except OperationalError:
        db.rollback()
        return {
            "status_code": 409,
            "detail": "Conflicto de concurrencia: reintente la operación",
        }
    except Exception:
        db.rollback()
        raise
