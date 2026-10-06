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
) -> MovimientoCorte:
    """Crea un abono ordinario con importe canónico (sin normalizar)."""
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
    movimiento = MovimientoCorte(
        uuid=uuid or str(uuid4()),
        corte_id=corte.id,
        concepto=concepto,
        tipo=TipoMovimiento.ABONO,
        importe=importe_ok,
        autor_id=autor.id,
        metodo_pago=metodo,
        momento_real=momento_real,
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
    """Saldos de ambos conceptos desde movimientos aceptados."""
    movimientos = (
        db.query(MovimientoCorte)
        .filter(MovimientoCorte.corte_id == corte.id)
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
