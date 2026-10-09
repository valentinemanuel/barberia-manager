"""Movimientos de corte por concepto (paquete 6, RF-16–RF-21 parcial)."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import obtener_usuario_actual
from app.models.auditoria_corte import AccionAuditoriaCorte
from app.models.corte import Corte, MetodoPago
from app.models.finanzas_corte import ConceptoMovimiento, MovimientoCorte
from app.models.usuario import Rol, Usuario
from app.services.edicion_corte_service import auditar_cambio
from app.services.movimiento_corte_service import (
    OriginalAusente,
    RevisionResuelta,
    _candado_abono,
    _candado_devolucion,
    registrar_abono,
    registrar_compensacion,
    registrar_devolucion,
    resolucion_previa,
    resolver_revision,
    saldos_corte,
)
from app.services.operacion_corte_service import ConflictoIdentidad

router = APIRouter(prefix="/api/cortes", tags=["Movimientos"])


class MovimientoCrear(BaseModel):
    concepto: ConceptoMovimiento
    importe: Decimal
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO
    momento_real: Optional[datetime] = None
    uuid: Optional[UUID] = None


class MovimientoResponse(BaseModel):
    id: int
    uuid: str
    concepto: ConceptoMovimiento
    importe: Decimal
    metodo_pago: MetodoPago
    momento_real: Optional[datetime] = None
    registrado_en: datetime
    # Revisión offline (paquete 8, T52): aditivos opcionales.
    estado: Optional[str] = None
    motivo_revision: Optional[str] = None
    # Correctivos (paquete 9, T59): aditivos opcionales.
    tipo: Optional[str] = None
    motivo: Optional[str] = None
    original_uuid: Optional[str] = None
    evidencia: Optional[str] = None
    # Imputación (paquete 11, T75): aditivo opcional.
    imputacion: Optional[str] = None

    class Config:
        from_attributes = True


class SaldoConcepto(BaseModel):
    obligacion: Decimal
    abonado: Decimal
    restante: Decimal
    excedente: Decimal = Decimal("0.00")
    estado: str
    # Históricos (paquete 10, RF-44): False = sin información suficiente.
    conocido: bool = True


class SaldosResponse(BaseModel):
    cliente: SaldoConcepto
    comision: SaldoConcepto


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
    if corte.anulado_en is not None:
        raise HTTPException(
            status_code=409, detail="Corte anulado: no admite abonos ordinarios"
        )
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
        with _candado_abono:
            movimiento = registrar_abono(
                db,
                autor=actor,
                corte=corte,
                concepto=datos.concepto,
                importe=datos.importe,
                metodo=datos.metodo_pago,
                momento_real=momento,
                uuid=str(datos.uuid) if datos.uuid is not None else None,
            )
            db.commit()
    except ConflictoIdentidad as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(movimiento)
    return _respuesta_movimiento(db, movimiento)


def _respuesta_movimiento(
    db: Session, movimiento: MovimientoCorte
) -> MovimientoResponse:
    """Serializa un movimiento con los campos correctivos aditivos."""
    from app.models.imputacion_corte import ImputacionMovimiento

    respuesta = MovimientoResponse.model_validate(movimiento)
    respuesta.estado = movimiento.estado.value if movimiento.estado else "aceptado"
    respuesta.motivo_revision = movimiento.motivo_revision
    respuesta.tipo = movimiento.tipo.value if movimiento.tipo else None
    respuesta.motivo = movimiento.motivo
    respuesta.original_uuid = movimiento.original_uuid
    respuesta.evidencia = movimiento.evidencia
    fila = (
        db.query(ImputacionMovimiento)
        .filter(ImputacionMovimiento.movimiento_uuid == movimiento.uuid)
        .first()
    )
    respuesta.imputacion = fila.estado.value if fila else None
    return respuesta


@router.get("/{corte_id}/saldos", response_model=SaldosResponse)
def obtener_saldos(
    corte_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Saldos de cliente y comisión del corte (DTO personal, RF-21 parcial)."""
    corte = _corte_propio_o_gestion(db, corte_id, actor)
    return saldos_corte(db, corte)


@router.get("/{corte_id}/movimientos", response_model=list[MovimientoResponse])
def listar_movimientos(
    corte_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Movimientos del corte con motivos propios visibles (T63, RF-43 parcial).

    Propio o gestión; ajeno/inexistente → 404 idéntico (RF-14). Incluye
    revisiones con causa e importe y correctivos con motivo, sin datos
    de otros profesionales (RNF-5).
    """
    corte = _corte_propio_o_gestion(db, corte_id, actor)
    filas = (
        db.query(MovimientoCorte)
        .filter(MovimientoCorte.corte_id == corte.id)
        .order_by(MovimientoCorte.id)
        .all()
    )
    return [_respuesta_movimiento(db, fila) for fila in filas]


class ResolucionCrear(BaseModel):
    """Resolución admin de una revisión (paquete 9, RF-53 parcial)."""

    veredicto: Literal["real", "erroneo"]
    motivo: str
    importe_real: Optional[Decimal] = None
    operacion_uuid: Optional[UUID] = None
    # Evidencia obligatoria si lo erróneo reconoce dinero (T86, RF-41).
    evidencia: Optional[str] = None


@router.post(
    "/{corte_id}/revisiones/{movimiento_uuid}/resolver",
    response_model=MovimientoResponse,
)
def resolver_revision_endpoint(
    corte_id: int,
    movimiento_uuid: str,
    datos: ResolucionCrear,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Resuelve una revisión: dinero real íntegro o corrección compensatoria.

    Solo admin (403 en otro caso). No edita importes registrados: acepta
    el original o crea una compensatoria referenciada, con journal.
    """
    if actor.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Solo un admin resuelve revisiones")
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    movimiento = (
        db.query(MovimientoCorte)
        .filter(
            MovimientoCorte.corte_id == corte.id,
            MovimientoCorte.uuid == movimiento_uuid,
        )
        .first()
    )
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    estado_antes = movimiento.estado.value if movimiento.estado else "aceptado"
    es_replay = resolucion_previa(db, movimiento)
    try:
        resultado = resolver_revision(
            db,
            admin=actor,
            movimiento=movimiento,
            veredicto=datos.veredicto,
            motivo=datos.motivo,
            importe_real=datos.importe_real,
            operacion_uuid=str(datos.operacion_uuid) if datos.operacion_uuid else None,
            evidencia=datos.evidencia,
        )
    except RevisionResuelta as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not es_replay:
        auditar_cambio(
            db,
            corte_id=corte.id,
            actor_id=actor.id,
            accion=AccionAuditoriaCorte.RESOLUCION,
            antes={"movimiento_uuid": movimiento.uuid, "estado": estado_antes},
            despues={
                "movimiento_uuid": movimiento.uuid,
                "estado": movimiento.estado.value if movimiento.estado else None,
                "resuelto_uuid": resultado.uuid,
            },
            motivo=datos.motivo,
        )
    db.commit()
    db.refresh(resultado)
    return _respuesta_movimiento(db, resultado)


class CompensacionCrear(BaseModel):
    """Compensación admin de un movimiento erróneo (paquete 9, RF-43)."""

    concepto: ConceptoMovimiento
    importe: Decimal
    motivo: str
    original_uuid: str
    evidencia: Optional[str] = None
    operacion_uuid: Optional[UUID] = None


@router.post(
    "/{corte_id}/compensaciones",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_compensacion(
    corte_id: int,
    datos: CompensacionCrear,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Registra una compensación sin borrar el original (solo admin).

    Vale también sobre anulados (ajuste administrativo trazable, RF-46);
    el abono ordinario sigue prohibido allí.
    """
    if actor.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Solo un admin compensa movimientos")
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    try:
        fila = registrar_compensacion(
            db,
            admin=actor,
            corte=corte,
            concepto=datos.concepto,
            importe=datos.importe,
            motivo=datos.motivo,
            original_uuid=datos.original_uuid,
            evidencia=datos.evidencia,
            operacion_uuid=str(datos.operacion_uuid) if datos.operacion_uuid else None,
        )
    except OriginalAusente as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictoIdentidad as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    auditar_cambio(
        db,
        corte_id=corte.id,
        actor_id=actor.id,
        accion=AccionAuditoriaCorte.COMPENSACION,
        antes={"movimiento_original": datos.original_uuid},
        despues={"compensacion_uuid": fila.uuid, "importe": str(fila.importe)},
        motivo=datos.motivo,
    )
    db.commit()
    db.refresh(fila)
    return _respuesta_movimiento(db, fila)


class DevolucionCrear(BaseModel):
    """Devolución admin de dinero real (paquete 9, RF-41/RF-43)."""

    concepto: ConceptoMovimiento
    importe: Decimal
    motivo: str
    operacion_uuid: Optional[UUID] = None


@router.post(
    "/{corte_id}/devoluciones",
    response_model=MovimientoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_devolucion(
    corte_id: int,
    datos: DevolucionCrear,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Devuelve dinero reconocido del concepto (solo admin).

    Limitada a la capacidad (reconocido no devuelto); el check + inserción
    + commit ocurren bajo candado de proceso. Vale sobre anulados (RF-46).
    """
    if actor.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Solo un admin devuelve dinero")
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    try:
        with _candado_devolucion:
            from app.services.movimiento_corte_service import capacidad_devolucion

            capacidad_antes = capacidad_devolucion(db, corte, datos.concepto)
            fila = registrar_devolucion(
                db,
                admin=actor,
                corte=corte,
                concepto=datos.concepto,
                importe=datos.importe,
                motivo=datos.motivo,
                operacion_uuid=str(datos.operacion_uuid) if datos.operacion_uuid else None,
            )
            auditar_cambio(
                db,
                corte_id=corte.id,
                actor_id=actor.id,
                accion=AccionAuditoriaCorte.DEVOLUCION,
                antes={"capacidad": str(capacidad_antes)},
                despues={"devolucion_uuid": fila.uuid, "importe": str(fila.importe)},
                motivo=datos.motivo,
            )
            db.commit()
    except ConflictoIdentidad as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(fila)
    return _respuesta_movimiento(db, fila)
