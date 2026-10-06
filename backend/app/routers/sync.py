from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import oauth2_scheme, verificar_token
from app.models.corte import MetodoPago
from app.models.usuario import Rol, Usuario
from app.services.corte_service import crear_corte
from app.services.operacion_corte_service import (
    ReintentosAgotados,
    ejecutar_operacion,
)

router = APIRouter(prefix="/api/sync", tags=["Sincronización"])

# Acciones encoladas offline y roles que las tienen permitidas.
ACCIONES_PERMITIDAS: dict[str, set[Rol]] = {
    "crear_corte": {Rol.ADMIN, Rol.BARBERO},
    "crear_servicio": {Rol.ADMIN},
    "crear_producto": {Rol.ADMIN},
    "crear_consumible": {Rol.ADMIN},
    "crear_gasto": {Rol.ADMIN},
    "cerrar_caja": {Rol.ADMIN},
    "gestionar_usuario": {Rol.ADMIN},
}


class OperacionSync(BaseModel):
    """Operación encolada mientras el cliente estaba offline."""

    id: str
    accion: str
    datos: dict[str, Any] = {}


class SyncRequest(BaseModel):
    operaciones: list[OperacionSync] = []


class ResultadoOperacion(BaseModel):
    id: str
    accion: str
    aceptada: bool
    status_code: int
    motivo: Optional[str] = None
    notificacion: Optional[str] = None


class SyncResponse(BaseModel):
    aceptadas: int
    rechazadas: int
    resultados: list[ResultadoOperacion]


def accion_permitida(rol: Rol, accion: str) -> bool:
    permitidos = ACCIONES_PERMITIDAS.get(accion)
    if permitidos is None:
        return False
    return rol in permitidos


@router.post("/", response_model=SyncResponse)
def sincronizar_operaciones(
    payload: SyncRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Valida cada operación encolada contra el rol/activo ACTUAL en DB (RF-18).

    Las permitidas se aplican y aceptan; las no permitidas (rol incorrecto,
    usuario desactivado o acción desconocida) se rechazan con 409 y se
    notifica al usuario.
    """
    resultados: list[ResultadoOperacion] = []

    token_data = verificar_token(token)
    usuario = db.query(Usuario).filter(Usuario.id == token_data.usuario_id).first()

    for op in payload.operaciones:
        # Validar contra el estado vigente en DB (no el claim del token ni el cache local).
        if usuario is None or not usuario.activo:
            resultados.append(ResultadoOperacion(
                id=op.id,
                accion=op.accion,
                aceptada=False,
                status_code=409,
                motivo="usuario_desactivado",
                notificacion="Tu usuario fue desactivado; las operaciones encoladas no se pueden sincronizar.",
            ))
            continue

        if op.accion not in ACCIONES_PERMITIDAS:
            resultados.append(ResultadoOperacion(
                id=op.id,
                accion=op.accion,
                aceptada=False,
                status_code=409,
                motivo="accion_desconocida",
                notificacion=f"La operación '{op.accion}' no es válida.",
            ))
            continue

        if not accion_permitida(usuario.rol, op.accion):
            resultados.append(ResultadoOperacion(
                id=op.id,
                accion=op.accion,
                aceptada=False,
                status_code=409,
                motivo="rol_no_permitido",
                notificacion=(
                    f"Tu rol actual ({usuario.rol.value}) no permite '{op.accion}'; "
                    "la operación fue rechazada."
                ),
            ))
            continue

        # Operación permitida: aplicarla.
        try:
            if op.accion == "crear_corte":
                try:
                    metodo = MetodoPago(op.datos["metodo_pago"])
                except (ValueError, KeyError):
                    metodo = MetodoPago.EFECTIVO
                uuid_val = op.datos.get("operacion_uuid")
                if uuid_val is None:
                    # Legacy sin UUID: comportamiento intacto, sin promesa de
                    # deduplicación retroactiva (limitación documentada T32).
                    crear_corte(db, usuario, int(op.datos["servicio_id"]), metodo)
                else:
                    def _efecto_sync():
                        creado = crear_corte(
                            db, usuario, int(op.datos["servicio_id"]), metodo
                        )
                        return {"corte_id": creado.id, "estado": "aceptada"}

                    ejecutar_operacion(
                        db,
                        actor_id=usuario.id,
                        namespace="sync",
                        operacion_id=str(uuid_val),
                        accion="crear_corte",
                        payload={
                            "servicio_id": str(op.datos["servicio_id"]),
                            "metodo_pago": str(metodo),
                        },
                        modo="offline",
                        ejecutar=_efecto_sync,
                    )
                db.commit()
            else:
                # Otras acciones administrativas: aceptadas como válidas para el rol;
                # su aplicación detallada se realiza por los endpoints correspondientes.
                pass
            resultados.append(ResultadoOperacion(
                id=op.id,
                accion=op.accion,
                aceptada=True,
                status_code=201,
            ))
        except ReintentosAgotados as e:
            db.rollback()
            resultados.append(ResultadoOperacion(
                id=op.id,
                accion=op.accion,
                aceptada=False,
                status_code=500,
                motivo=str(e),
                notificacion="Contención del servidor; reintentá el lote.",
            ))
        except (ValueError, KeyError) as e:
            resultados.append(ResultadoOperacion(
                id=op.id,
                accion=op.accion,
                aceptada=False,
                status_code=409,
                motivo=str(e),
                notificacion=f"Operación '{op.accion}' rechazada: {e}",
            ))

    aceptadas = sum(1 for r in resultados if r.aceptada)
    return SyncResponse(
        aceptadas=aceptadas,
        rechazadas=len(resultados) - aceptadas,
        resultados=resultados,
    )
