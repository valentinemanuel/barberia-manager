"""Abonos ordinarios por concepto (paquete 6, RF-16/RF-17/RF-41).

Sin commit: la unidad de trabajo la posee el llamador.
"""
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
    )
    db.add(movimiento)
    db.flush()
    return movimiento


def calcular_saldo(obligacion: Decimal, abonado: Decimal) -> dict:
    """Saldo de un concepto: obligación − neto, con estado.

    Sin excedentes ni unknown en este paquete (RF-21 parcial): el exceso
    online se rechaza antes de llegar aquí (T39) y lo offline queda para sync.
    """
    restante = obligacion - abonado
    if restante <= Decimal("0"):
        estado = "pagado"
    elif abonado > Decimal("0"):
        estado = "parcial"
    else:
        estado = "pendiente"
    centavo = Decimal("0.01")
    return {
        "obligacion": obligacion.quantize(centavo),
        "abonado": abonado.quantize(centavo),
        "restante": max(restante, Decimal("0")).quantize(centavo),
        "estado": estado,
    }


def saldos_corte(db: Session, corte: Corte) -> dict:
    """Saldos de ambos conceptos desde movimientos aceptados.

    Revisión y nulos legacy: los nulos legacy cuentan como aceptados
    (compat); las revisiones no mueven saldos (RF-38/RF-53).
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
        neto[movimiento.concepto] += movimiento.importe
    return {
        "cliente": calcular_saldo(corte.precio, neto[ConceptoMovimiento.CLIENTE]),
        "comision": calcular_saldo(
            corte.parte_barbero, neto[ConceptoMovimiento.COMISION]
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
