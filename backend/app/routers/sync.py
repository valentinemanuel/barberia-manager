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
    "crear_corte_v2": {Rol.ADMIN, Rol.BARBERO},
    "registrar_abono_v2": {Rol.ADMIN, Rol.BARBERO},
    "editar_corte_v2": {Rol.ADMIN, Rol.BARBERO},
    "anular_corte_v2": {Rol.ADMIN, Rol.BARBERO},
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
    # Camino v2 (paquete 8, T51): estado + mapping + snapshot definitivo.
    # Aditivos opcionales; el camino legacy los omite (compat RNF-3).
    estado: Optional[str] = None
    corte_id: Optional[int] = None
    snapshot: Optional[dict[str, Any]] = None
    # LWW (paquete 10, T68): unidades aplicadas/omitidas por la edición.
    unidades: Optional[dict[str, str]] = None


class SyncResponse(BaseModel):
    aceptadas: int
    rechazadas: int
    resultados: list[ResultadoOperacion]


def accion_permitida(rol: Rol, accion: str) -> bool:
    permitidos = ACCIONES_PERMITIDAS.get(accion)
    if permitidos is None:
        return False
    return rol in permitidos


def _sincronizar_corte_v2(
    db: Session, usuario: Usuario, op: OperacionSync
) -> ResultadoOperacion:
    """Camino v2 (paquete 8, T51): UUID obligatoria, idempotente, con acuse.

    Sin UUID o con UUID malformada → rechazada 400 (el camino legacy
    `crear_corte` sin UUID sigue intacto). Misma UUID con distinto
    contenido → 409 conflicto de identidad, sin efecto.
    """
    import uuid as uuid_lib

    from app.services.operacion_corte_service import ConflictoIdentidad

    uuid_val = op.datos.get("operacion_uuid")
    if not uuid_val:
        return ResultadoOperacion(
            id=op.id,
            accion=op.accion,
            aceptada=False,
            status_code=400,
            motivo="falta_uuid",
            notificacion="La operación v2 exige operacion_uuid.",
        )
    try:
        uuid_lib.UUID(str(uuid_val))
    except (ValueError, AttributeError, TypeError):
        return ResultadoOperacion(
            id=op.id,
            accion=op.accion,
            aceptada=False,
            status_code=400,
            motivo="uuid_invalida",
            notificacion="La operacion_uuid no es una UUID válida.",
        )
    try:
        metodo = MetodoPago(op.datos["metodo_pago"])
    except (ValueError, KeyError):
        metodo = MetodoPago.EFECTIVO
    modo = str(op.datos.get("modo_captura") or "offline")
    if modo not in ("online", "offline"):
        return ResultadoOperacion(
            id=op.id,
            accion=op.accion,
            aceptada=False,
            status_code=400,
            motivo="modo_invalido",
            notificacion="El modo_captura debe ser online u offline.",
        )
    momento = None
    momento_raw = op.datos.get("momento_real")
    if momento_raw:
        from datetime import datetime as datetime_sync
        from datetime import timezone as timezone_sync

        try:
            momento = datetime_sync.fromisoformat(str(momento_raw))
            if momento.tzinfo is not None:
                momento = momento.astimezone(timezone_sync.utc).replace(tzinfo=None)
        except ValueError as e:
            return ResultadoOperacion(
                id=op.id, accion=op.accion, aceptada=False, status_code=400,
                motivo=f"momento_invalido: {e}",
                notificacion="El momento_real no es una fecha válida.",
            )
    try:
        servicio_id = int(op.datos["servicio_id"])
    except (KeyError, TypeError, ValueError) as e:
        return ResultadoOperacion(
            id=op.id,
            accion=op.accion,
            aceptada=False,
            status_code=400,
            motivo=f"datos_invalidos: {e}",
            notificacion="La operación trae datos inválidos.",
        )
    from app.models.servicio import Servicio as ServicioSync

    if db.query(ServicioSync).filter(ServicioSync.id == servicio_id).first() is None:
        # RF-56: sin valores recuperables se conserva para revisión
        # administrativa, sin inventar valores ni identidad.
        return ResultadoOperacion(
            id=op.id,
            accion=op.accion,
            aceptada=False,
            status_code=202,
            motivo="servicio_inexistente",
            notificacion="El servicio ya no existe; la operación quedó en revisión.",
            estado="revision",
            snapshot=None,
        )

    def _efecto_v2():
        creado = crear_corte(
            db, usuario, servicio_id, metodo, aceptar_inactivo=True,
            momento_real=momento,
        )
        return {
            "corte_id": creado.id,
            "estado": "aceptada",
            "snapshot": {
                "precio": str(creado.precio),
                "porcentaje_barbero": str(creado.porcentaje_barbero),
                "parte_barbero": str(creado.parte_barbero),
                "metodo_pago": str(creado.metodo_pago),
            },
        }

    try:
        acuse = ejecutar_operacion(
            db,
            actor_id=usuario.id,
            namespace="sync",
            operacion_id=str(uuid_val),
            accion="crear_corte",
            payload={
                "servicio_id": str(servicio_id),
                "metodo_pago": str(metodo),
                "modo_captura": modo,
                "momento_real": momento.isoformat() if momento else "",
            },
            modo="offline",
            ejecutar=_efecto_v2,
        )
    except ConflictoIdentidad as e:
        db.rollback()
        return ResultadoOperacion(
            id=op.id,
            accion=op.accion,
            aceptada=False,
            status_code=409,
            motivo=str(e),
            notificacion="La operación ya existe con otro contenido.",
        )
    db.commit()
    return ResultadoOperacion(
        id=op.id,
        accion=op.accion,
        aceptada=True,
        status_code=201,
        estado=str(acuse.get("estado", "aceptada")),
        corte_id=acuse.get("corte_id"),
        snapshot=acuse.get("snapshot"),
    )


def _sincronizar_abono_v2(
    db: Session, usuario: Usuario, op: OperacionSync
) -> ResultadoOperacion:
    """Abono offline idempotente (paquete 8, T52, RF-38/RF-51 parcial).

    UUID obligatoria; exceso sobre el saldo y reloj >5min conservan el
    movimiento en revisión (202) sin mover saldos. Ajeno/inexistente → 404
    idéntico (RF-14). Anulado → 409. El POST directo sigue siendo online.
    """
    import uuid as uuid_lib
    from datetime import datetime, timezone
    from decimal import Decimal, InvalidOperation

    from app.models.corte import Corte
    from app.models.finanzas_corte import ConceptoMovimiento, EstadoMovimiento
    from app.services.movimiento_corte_service import registrar_abono

    uuid_val = op.datos.get("operacion_uuid")
    if not uuid_val:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo="falta_uuid",
            notificacion="La operación v2 exige operacion_uuid.",
        )
    try:
        uuid_lib.UUID(str(uuid_val))
    except (ValueError, AttributeError, TypeError):
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo="uuid_invalida",
            notificacion="La operacion_uuid no es una UUID válida.",
        )
    try:
        corte_id = int(op.datos["corte_id"])
        concepto = ConceptoMovimiento(op.datos["concepto"])
        importe = Decimal(str(op.datos["importe"]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as e:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo=f"datos_invalidos: {e}",
            notificacion="La operación trae datos inválidos.",
        )
    momento = None
    momento_raw = op.datos.get("momento_real")
    if momento_raw:
        try:
            momento = datetime.fromisoformat(str(momento_raw))
            if momento.tzinfo is not None:
                momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError as e:
            return ResultadoOperacion(
                id=op.id, accion=op.accion, aceptada=False, status_code=400,
                motivo=f"momento_invalido: {e}",
                notificacion="El momento_real no es una fecha válida.",
            )
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=404,
            motivo="Corte no encontrado",
            notificacion="Corte no encontrado.",
        )
    if usuario.rol != Rol.ADMIN and corte.barbero_id != usuario.id:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=404,
            motivo="Corte no encontrado",
            notificacion="Corte no encontrado.",
        )
    if corte.anulado_en is not None:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=409,
            motivo="Corte anulado: no admite abonos ordinarios",
            notificacion="Corte anulado: no admite abonos ordinarios.",
        )
    try:
        from app.models.corte import MetodoPago as MetodoAbono

        try:
            metodo = MetodoAbono(op.datos.get("metodo_pago") or "efectivo")
        except ValueError:
            metodo = MetodoAbono.EFECTIVO
        movimiento = registrar_abono(
            db, autor=usuario, corte=corte, concepto=concepto,
            importe=importe, metodo=metodo, momento_real=momento,
            uuid=str(uuid_val), origen="offline",
        )
    except ValueError as e:
        db.rollback()
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo=str(e), notificacion=f"Abono rechazado: {e}",
        )
    db.commit()
    estado = movimiento.estado.value if movimiento.estado else "aceptado"
    if estado == "revision":
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=202,
            motivo=movimiento.motivo_revision,
            notificacion="Abono en revisión administrativa.",
            estado="revision",
            corte_id=corte.id,
            snapshot={"importe": str(movimiento.importe)},
        )
    return ResultadoOperacion(
        id=op.id, accion=op.accion, aceptada=True, status_code=201,
        estado="aceptada", corte_id=corte.id,
        snapshot={"importe": str(movimiento.importe)},
    )


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
            if op.accion == "crear_corte_v2":
                resultados.append(_sincronizar_corte_v2(db, usuario, op))
                continue
            if op.accion == "registrar_abono_v2":
                resultados.append(_sincronizar_abono_v2(db, usuario, op))
                continue
            if op.accion in ("editar_corte_v2", "anular_corte_v2"):
                resultados.append(_sincronizar_edicion_v2(db, usuario, op))
                continue
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


def _uuid_o_error(op: OperacionSync) -> tuple[str | None, ResultadoOperacion | None]:
    """UUID obligatoria del camino v2 (paquete 8, T51; reutilizada en T68)."""
    import uuid as uuid_lib

    uuid_val = op.datos.get("operacion_uuid")
    if not uuid_val:
        return None, ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo="falta_uuid",
            notificacion="La operación v2 exige operacion_uuid.",
        )
    try:
        uuid_lib.UUID(str(uuid_val))
    except (ValueError, AttributeError, TypeError):
        return None, ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo="uuid_invalida",
            notificacion="La operacion_uuid no es una UUID válida.",
        )
    return str(uuid_val), None


def _sincronizar_edicion_v2(
    db: Session, usuario: Usuario, op: OperacionSync
) -> ResultadoOperacion:
    """Edición/anulación offline con LWW (paquete 10, T68, RF-36/RF-40).

    Sin bloqueo: aplica con el instante de captura (misma regla que PATCH).
    Con bloqueo o anulación y origen barbero: conserva la operación
    pendiente de intervención manual (202), sin aplicarla ni terminalizar.
    Origen admin sobre bloqueado: aplica con motivo obligatorio.
    """
    from datetime import datetime, timezone

    from app.models.corte import Corte, MetodoPago as MetodoEdicion
    from app.models.intervencion_corte import EstadoIntervencion, IntervencionCorte
    from app.services.edicion_corte_service import (
        NoEncontrado as NoEncontradoEdicion,
    )
    from app.services.edicion_corte_service import (
        anular_corte as aplicar_anulacion_sync,
    )
    from app.services.edicion_corte_service import (
        auditar_cambio as auditar_edicion_sync,
    )
    from app.services.edicion_corte_service import (
        editar_corte as aplicar_edicion_sync,
    )
    from app.services.edicion_corte_service import (
        snapshot_corte as snapshot_sync,
    )
    from app.models.auditoria_corte import AccionAuditoriaCorte as AccionSync
    from app.services.movimiento_corte_service import corte_bloqueado

    uuid_val, error = _uuid_o_error(op)
    if error is not None:
        return error
    assert uuid_val is not None
    try:
        corte_id = int(op.datos["corte_id"])
    except (KeyError, TypeError, ValueError) as e:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo=f"datos_invalidos: {e}",
            notificacion="La operación trae datos inválidos.",
        )
    instante_raw = op.datos.get("instante_cambio")
    try:
        instante = (
            datetime.fromisoformat(str(instante_raw))
            if instante_raw
            else datetime.utcnow()
        )
        if instante.tzinfo is not None:
            instante = instante.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError as e:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo=f"instante_invalido: {e}",
            notificacion="El instante_cambio no es una fecha válida.",
        )
    es_anulacion = op.accion == "anular_corte_v2"
    cambios = dict(op.datos.get("cambios") or {})
    motivo = op.datos.get("motivo")

    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=404,
            motivo="Corte no encontrado", notificacion="Corte no encontrado.",
        )
    if usuario.rol != Rol.ADMIN and corte.barbero_id != usuario.id:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=404,
            motivo="Corte no encontrado", notificacion="Corte no encontrado.",
        )
    if corte.anulado_en is not None:
        # Terminal: ni la edición tardía ni el replay la eluden (RF-36).
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=409,
            motivo="Corte anulado: no admite edición",
            notificacion="El corte está anulado.",
        )
    bloqueado = corte_bloqueado(db, corte)
    if bloqueado and usuario.rol != Rol.ADMIN:
        existente = (
            db.query(IntervencionCorte).filter(IntervencionCorte.uuid == uuid_val).first()
        )
        if existente is None:
            causa = "corte_bloqueado" if not es_anulacion else "anulacion_bloqueada"
            db.add(IntervencionCorte(
                uuid=uuid_val,
                corte_id=corte.id,
                actor_id=usuario.id,
                accion="anular" if es_anulacion else "editar",
                cambios={"cambios": cambios, "instante_cambio": instante.isoformat(),
                         "motivo": motivo},
                causa=causa,
                estado=EstadoIntervencion.PENDIENTE,
            ))
            db.commit()
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=202,
            motivo="corte_bloqueado",
            notificacion="El corte se bloqueó antes de sincronizar; quedó pendiente de intervención.",
            estado="pendiente_intervencion", corte_id=corte.id,
        )
    if bloqueado and not motivo:
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo="Corregir un corte bloqueado exige motivo",
            notificacion="Corregir un corte bloqueado exige motivo.",
        )
    try:
        if es_anulacion:
            antes = snapshot_sync(corte)
            aplicar_anulacion_sync(db, corte=corte, actor=usuario, motivo=motivo)
            auditar_edicion_sync(
                db, corte_id=corte.id, actor_id=usuario.id,
                accion=AccionSync.ANULACION, antes=antes,
                despues=snapshot_sync(corte), motivo=motivo,
            )
            db.commit()
            return ResultadoOperacion(
                id=op.id, accion=op.accion, aceptada=True, status_code=200,
                estado="aceptada", corte_id=corte.id,
                snapshot={"anulado_en": corte.anulado_en.isoformat() if corte.anulado_en else None},
            )
        metodo = None
        if cambios.get("metodo_pago") is not None:
            try:
                metodo = MetodoEdicion(cambios["metodo_pago"])
            except ValueError:
                metodo = MetodoEdicion.EFECTIVO
        servicio_id = cambios.get("servicio_id")
        antes = snapshot_sync(corte)
        corte, unidades = aplicar_edicion_sync(
            db, corte=corte,
            servicio_id=int(servicio_id) if servicio_id is not None else None,
            metodo=metodo, instante=instante,
        )
        auditar_edicion_sync(
            db, corte_id=corte.id, actor_id=usuario.id,
            accion=AccionSync.EDICION, antes=antes,
            despues={**snapshot_sync(corte), "unidades": unidades,
                     "operacion_uuid": uuid_val},
            motivo=motivo,
        )
        db.commit()
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=True, status_code=200,
            estado="aceptada", corte_id=corte.id, unidades=unidades,
            snapshot={"metodo_pago": str(corte.metodo_pago), "precio": str(corte.precio)},
        )
    except NoEncontradoEdicion as e:
        db.rollback()
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=404,
            motivo=str(e), notificacion=str(e),
        )
    except (ValueError, KeyError) as e:
        db.rollback()
        return ResultadoOperacion(
            id=op.id, accion=op.accion, aceptada=False, status_code=400,
            motivo=str(e), notificacion=f"Edición rechazada: {e}",
        )
