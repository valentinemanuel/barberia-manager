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
