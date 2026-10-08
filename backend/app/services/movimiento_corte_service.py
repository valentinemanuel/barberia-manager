"""Abonos ordinarios por concepto (paquete 6, RF-16/RF-17/RF-41).

Sin commit: la unidad de trabajo la posee el llamador.
"""
import threading
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.corte import MetodoPago
from app.models.finanzas_corte import (
    ConceptoMovimiento,
    EstadoMovimiento,
    MovimientoCorte,
    TipoMovimiento,
)
from app.models.usuario import Usuario
from app.models.corte import Corte
from app.services.dinero_cortes import validar_importe_abono


# Serialización mínima de devoluciones (paquete 9, T61, RF-41 parcial):
# el check de capacidad + inserción + commit ocurren bajo este candado
# (el endpoint lo mantiene durante toda la UoW). Solo protege un proceso;
# multi-worker/PostgreSQL exigirá locks de fila (protocolo del plan §3).
_candado_devolucion = threading.Lock()


def registrar_abono(
    db: Session,
    *,
    autor: Usuario,
    corte: Corte,
    concepto: ConceptoMovimiento,
    importe: Decimal,
    metodo: MetodoPago,
    momento_real: datetime | None = None,
    uuid: str | None = None,
    origen: str = "online",
) -> MovimientoCorte:
    """Crea un abono ordinario con importe canónico (sin normalizar).

    En origen online el abono no puede superar el saldo restante (RF-41).
    En origen offline (paquete 8, T52, RF-38/RF-51) el exceso sobre el
    saldo definitivo y el reloj adelantado más de cinco minutos conservan
    el movimiento con su importe real en revisión, sin mover saldos.
    """
    try:
        importe_ok = validar_importe_abono(importe)
    except (TypeError, ValueError) as error:
        raise ValueError(str(error)) from error
    if uuid is not None:
        existente = (
            db.query(MovimientoCorte).filter(MovimientoCorte.uuid == uuid).first()
        )
        if existente is not None:
            return existente
    causa_revision: str | None = None
    if origen == "online":
        clave = "cliente" if concepto == ConceptoMovimiento.CLIENTE else "comision"
        restante = saldos_corte(db, corte)[clave]["restante"]
        if importe_ok > restante:
            raise ValueError("El abono supera el saldo restante del concepto")
    else:
        clave = "cliente" if concepto == ConceptoMovimiento.CLIENTE else "comision"
        restante = saldos_corte(db, corte)[clave]["restante"]
        if importe_ok > restante:
            # RF-38: se conserva íntegro para decisión admin, sin recortar.
            causa_revision = "exceso"
        if momento_real is not None:
            desvio = (momento_real - datetime.utcnow()).total_seconds()
            if desvio > 300:
                # RF-51: solo reloj adelantado >5min; el atraso de sync no invalida.
                causa_revision = "reloj" if causa_revision is None else causa_revision + "+reloj"
    movimiento = MovimientoCorte(
        uuid=uuid or str(uuid4()),
        corte_id=corte.id,
        concepto=concepto,
        tipo=TipoMovimiento.ABONO,
        importe=importe_ok,
        autor_id=autor.id,
        metodo_pago=metodo,
        momento_real=momento_real,
        estado=EstadoMovimiento.REVISION if causa_revision else EstadoMovimiento.ACEPTADO,
        motivo_revision=causa_revision,
        # Titular del dinero (paquete 10, T66): la comisión pertenece al
        # titular del corte, no al autor del registro; la deuda es del corte.
        profesional_id=corte.barbero_id if concepto == ConceptoMovimiento.COMISION else None,
    )
    db.add(movimiento)
    db.flush()
    return movimiento


def calcular_saldo(obligacion: Decimal, neto_reconocido: Decimal) -> dict:
    """Saldo de un concepto: obligación − neto, con excedente visible.

    Paquete 9 (RF-21 parcial): `abonado` es el neto reconocido
    (abonos + compensaciones con signo − devoluciones, solo aceptados);
    `restante` nunca es negativo y el sobrante va a `excedente`.
    Revisión/rechazados no entran al neto (RF-38/RF-53).
    """
    restante = obligacion - neto_reconocido
    excedente = neto_reconocido - obligacion
    if restante <= Decimal("0"):
        estado = "pagado"
    elif neto_reconocido > Decimal("0"):
        estado = "parcial"
    else:
        estado = "pendiente"
    centavo = Decimal("0.01")
    return {
        "obligacion": obligacion.quantize(centavo),
        "abonado": neto_reconocido.quantize(centavo),
        "restante": max(restante, Decimal("0")).quantize(centavo),
        "excedente": max(excedente, Decimal("0")).quantize(centavo),
        "estado": estado,
    }


def saldos_corte(db: Session, corte: Corte) -> dict:
    """Saldos de ambos conceptos desde movimientos aceptados.

    Revisión y nulos legacy: los nulos legacy cuentan como aceptados
    (compat); las revisiones no mueven saldos (RF-38/RF-53).
    Compensaciones suman con su signo, devoluciones restan (RF-41/43).
    Anulado (RF-27/46, T62): obligaciones canceladas al anular → el neto
    ya abonado queda como excedente a regularizar, sin devolución
    automática ni nuevos abonos ordinarios.
    """
    from sqlalchemy import or_

    movimientos = (
        db.query(MovimientoCorte)
        .filter(
            MovimientoCorte.corte_id == corte.id,
            or_(
                MovimientoCorte.estado == EstadoMovimiento.ACEPTADO,
                MovimientoCorte.estado.is_(None),
            ),
        )
        .all()
    )
    neto = {ConceptoMovimiento.CLIENTE: Decimal("0"), ConceptoMovimiento.COMISION: Decimal("0")}
    for movimiento in movimientos:
        if movimiento.concepto == ConceptoMovimiento.COMISION:
            # La comisión pertenece a su profesional (paquete 10, RF-47):
            # filas de un titular previo no se trasladan ficticiamente al
            # nuevo; la deuda del cliente pertenece al corte y no cambia.
            if movimiento.profesional_id != corte.barbero_id:
                continue
        if movimiento.tipo == TipoMovimiento.DEVOLUCION:
            neto[movimiento.concepto] -= movimiento.importe
        else:
            # Abono suma; compensación suma con su signo (puede restar).
            neto[movimiento.concepto] += movimiento.importe
    if corte.anulado_en is not None:
        obligacion_cliente = Decimal("0")
        obligacion_comision = Decimal("0")
    else:
        obligacion_cliente = corte.precio
        obligacion_comision = corte.parte_barbero
    return {
        "cliente": calcular_saldo(obligacion_cliente, neto[ConceptoMovimiento.CLIENTE]),
        "comision": calcular_saldo(
            obligacion_comision, neto[ConceptoMovimiento.COMISION]
        ),
    }


def corte_bloqueado(db: Session, corte: Corte) -> bool:
    """Bloqueo calculado (RF-23/25 base): verdadero desde el primer pago.

    La pertenencia a cierre corresponde al paquete de jornadas; la edición
    aún no existe (paquete 7), esto solo expone el estado.
    """
    return (
        db.query(MovimientoCorte)
        .filter(MovimientoCorte.corte_id == corte.id)
        .first()
        is not None
    )


class RevisionResuelta(ValueError):
    """La revisión ya salió de ese estado: conflicto, sin efecto (HTTP 409)."""


class OriginalAusente(ValueError):
    """El movimiento original no existe: sin referencia no hay correctivo (404)."""


def _validar_importe_real(importe: Decimal) -> Decimal:
    """Dinero real reconocido: Decimal finito, no negativo, ≤2 decimales."""
    from decimal import Decimal as DecimalT59

    if not isinstance(importe, DecimalT59):
        raise ValueError("El importe real debe ser Decimal")
    if not importe.is_finite():
        raise ValueError("El importe real debe ser finito")
    if importe.as_tuple().exponent < -2:
        raise ValueError("El importe real debe tener como máximo dos decimales")
    if importe < DecimalT59("0"):
        raise ValueError("El importe real no puede ser negativo")
    return importe


def resolver_revision(
    db: Session,
    *,
    admin: Usuario,
    movimiento: MovimientoCorte,
    veredicto: str,
    motivo: str,
    importe_real: Decimal | None = None,
    operacion_uuid: str | None = None,
) -> MovimientoCorte:
    """Resuelve una revisión administrativa (paquete 9, RF-38/RF-53 parcial).

    `real`: el dinero registrado era íntegro → el original pasa a aceptado
    con su importe intacto (el sobrante sobre la obligación queda como
    excedente en saldos, sin devolución automática).
    `erroneo`: el registro era erróneo → el original queda en revisión y,
    si hubo dinero real, se crea una compensatoria aceptada por ese importe
    con referencia al original. Sin commit: la UoW la posee el llamador.
    """
    if movimiento.estado != EstadoMovimiento.REVISION:
        raise RevisionResuelta("La revisión ya fue resuelta")
    if not motivo or not motivo.strip():
        raise ValueError("La resolución exige motivo")
    if veredicto == "real":
        movimiento.estado = EstadoMovimiento.ACEPTADO
        movimiento.motivo = motivo.strip()
        db.flush()
        return movimiento
    if veredicto != "erroneo":
        raise ValueError("El veredicto debe ser real o erroneo")
    real = _validar_importe_real(Decimal("0") if importe_real is None else importe_real)
    if operacion_uuid is not None:
        existente = (
            db.query(MovimientoCorte).filter(MovimientoCorte.uuid == operacion_uuid).first()
        )
        if existente is not None:
            return existente
    movimiento.motivo = motivo.strip()
    if real <= Decimal("0"):
        # Sin dinero real: solo queda la traza del motivo en el original.
        db.flush()
        return movimiento
    compensatoria = MovimientoCorte(
        uuid=operacion_uuid or str(uuid4()),
        corte_id=movimiento.corte_id,
        concepto=movimiento.concepto,
        tipo=TipoMovimiento.COMPENSACION,
        importe=real,
        autor_id=admin.id,
        metodo_pago=movimiento.metodo_pago,
        momento_real=movimiento.momento_real,
        estado=EstadoMovimiento.ACEPTADO,
        original_uuid=movimiento.uuid,
        motivo=motivo.strip(),
        profesional_id=movimiento.profesional_id,
    )
    db.add(compensatoria)
    db.flush()
    return compensatoria


def _validar_importe_compensacion(importe: Decimal) -> Decimal:
    """Ajuste con signo: Decimal finito, no nulo, ≤2 decimales."""
    from decimal import Decimal as DecimalT60

    if not isinstance(importe, DecimalT60):
        raise ValueError("El importe de la compensación debe ser Decimal")
    if not importe.is_finite():
        raise ValueError("El importe de la compensación debe ser finito")
    if importe.as_tuple().exponent < -2:
        raise ValueError("El importe de la compensación debe tener como máximo dos decimales")
    if importe == DecimalT60("0"):
        raise ValueError("El importe de la compensación no puede ser cero")
    return importe


def registrar_compensacion(
    db: Session,
    *,
    admin: Usuario,
    corte: Corte,
    concepto: ConceptoMovimiento,
    importe: Decimal,
    motivo: str,
    original_uuid: str,
    evidencia: str | None = None,
    operacion_uuid: str | None = None,
) -> MovimientoCorte:
    """Corrección administrativa sin borrar el original (paquete 9, RF-43).

    Append-only con motivo y referencia inmutable al original. El signo
    corrige el neto (resta si el original sobrestimó); no representa una
    salida física de dinero. Sin commit: la UoW la posee el llamador.
    """
    if not motivo or not motivo.strip():
        raise ValueError("La compensación exige motivo")
    importe_ok = _validar_importe_compensacion(importe)
    original = (
        db.query(MovimientoCorte)
        .filter(
            MovimientoCorte.corte_id == corte.id,
            MovimientoCorte.uuid == original_uuid,
        )
        .first()
    )
    if original is None:
        raise OriginalAusente("Movimiento original no encontrado")
    if operacion_uuid is not None:
        existente = (
            db.query(MovimientoCorte).filter(MovimientoCorte.uuid == operacion_uuid).first()
        )
        if existente is not None:
            return existente
    fila = MovimientoCorte(
        uuid=operacion_uuid or str(uuid4()),
        corte_id=corte.id,
        concepto=concepto,
        tipo=TipoMovimiento.COMPENSACION,
        importe=importe_ok,
        autor_id=admin.id,
        metodo_pago=original.metodo_pago,
        momento_real=original.momento_real,
        estado=EstadoMovimiento.ACEPTADO,
        original_uuid=original.uuid,
        motivo=motivo.strip(),
        evidencia=evidencia,
        profesional_id=corte.barbero_id if concepto == ConceptoMovimiento.COMISION else None,
    )
    db.add(fila)
    db.flush()
    return fila


def capacidad_devolucion(
    db: Session, corte: Corte, concepto: ConceptoMovimiento
) -> Decimal:
    """Dinero reconocido no devuelto del concepto (paquete 9, T61, RF-41).

    Capacidad por concepto (decisión del paquete): neto aceptado
    (abonos + compensaciones con signo − devoluciones), nunca negativo.
    """
    clave = "cliente" if concepto == ConceptoMovimiento.CLIENTE else "comision"
    neto = saldos_corte(db, corte)[clave]["abonado"]
    return max(neto, Decimal("0"))


def registrar_devolucion(
    db: Session,
    *,
    admin: Usuario,
    corte: Corte,
    concepto: ConceptoMovimiento,
    importe: Decimal,
    motivo: str,
    operacion_uuid: str | None = None,
) -> MovimientoCorte:
    """Devolución explícita de dinero real (paquete 9, RF-41/RF-43 parcial).

    Limitada a la capacidad del concepto; consume esa capacidad al
    aceptarse. No genera devolución automática nada: siempre explícita
    con motivo. Sin commit: la UoW (con candado) la posee el llamador.
    """
    if not motivo or not motivo.strip():
        raise ValueError("La devolución exige motivo")
    try:
        importe_ok = validar_importe_abono(importe)
    except (TypeError, ValueError) as error:
        raise ValueError(str(error)) from error
    if operacion_uuid is not None:
        existente = (
            db.query(MovimientoCorte).filter(MovimientoCorte.uuid == operacion_uuid).first()
        )
        if existente is not None:
            return existente
    if importe_ok > capacidad_devolucion(db, corte, concepto):
        raise ValueError("La devolución supera el dinero reconocido no devuelto")
    fila = MovimientoCorte(
        uuid=operacion_uuid or str(uuid4()),
        corte_id=corte.id,
        concepto=concepto,
        tipo=TipoMovimiento.DEVOLUCION,
        importe=importe_ok,
        autor_id=admin.id,
        metodo_pago=MetodoPago.EFECTIVO,
        estado=EstadoMovimiento.ACEPTADO,
        motivo=motivo.strip(),
        profesional_id=corte.barbero_id if concepto == ConceptoMovimiento.COMISION else None,
    )
    db.add(fila)
    db.flush()
    return fila
