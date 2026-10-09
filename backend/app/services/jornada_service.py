"""Jornada de negocio y regla de imputación (paquete 11, RF-45/RF-50).

Puro + UoW sin commit: la unidad de trabajo la posee el llamador.
Sin zona en config: `America/Argentina/Buenos_Aires` es contractual (DA-8).
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.jornada_caja import EstadoJornada, JornadaCaja
from app.models.usuario import Usuario

ZONA_NEGOCIO = ZoneInfo("America/Argentina/Buenos_Aires")


def fecha_negocio(instante_utc: datetime) -> date:
    """Fecha de negocio del instante UTC (día 00:00–24:00 en zona)."""
    if instante_utc.tzinfo is None:
        instante_utc = instante_utc.replace(tzinfo=ZoneInfo("UTC"))
    return instante_utc.astimezone(ZONA_NEGOCIO).date()


class JornadaExistente(ValueError):
    """La jornada ya está abierta o cerrada: conflicto, sin efecto (HTTP 409)."""


class JornadaInexistente(ValueError):
    """Sin jornada para esa fecha: nada que cerrar (HTTP 409)."""


def abrir_jornada(db: Session, *, admin: Usuario, fecha: date) -> JornadaCaja:
    """Apertura explícita admin. Nunca automática (plan §3)."""
    existente = (
        db.query(JornadaCaja).filter(JornadaCaja.fecha_negocio == fecha).first()
    )
    if existente is not None:
        raise JornadaExistente("La jornada ya existe")
    otra = (
        db.query(JornadaCaja).filter(JornadaCaja.estado == EstadoJornada.ABIERTA).first()
    )
    if otra is not None:
        raise JornadaExistente("Ya hay una jornada abierta")
    fila = JornadaCaja(
        fecha_negocio=fecha,
        estado=EstadoJornada.ABIERTA,
        abierta_por=admin.id,
    )
    db.add(fila)
    db.flush()
    return fila


def cerrar_jornada(db: Session, *, admin: Usuario, fecha: date) -> JornadaCaja:
    """Cierre inmutable: abierta → cerrada, sin reapertura."""
    fila = (
        db.query(JornadaCaja).filter(JornadaCaja.fecha_negocio == fecha).first()
    )
    if fila is None:
        raise JornadaInexistente("La jornada no existe")
    if fila.estado != EstadoJornada.ABIERTA:
        raise JornadaExistente("La jornada ya está cerrada")
    fila.estado = EstadoJornada.CERRADA
    fila.cerrada_por = admin.id
    fila.cerrada_en = datetime.utcnow()
    db.flush()
    return fila


def jornada_abierta(db: Session, *, fecha: date) -> JornadaCaja | None:
    """Jornada abierta para esa fecha, o None si no hay destino."""
    fila = (
        db.query(JornadaCaja).filter(JornadaCaja.fecha_negocio == fecha).first()
    )
    if fila is None or fila.estado != EstadoJornada.ABIERTA:
        return None
    return fila


def jornada_abierta_actual(db: Session) -> JornadaCaja | None:
    """La jornada abierta actual (a lo sumo una), o None."""
    return (
        db.query(JornadaCaja)
        .filter(JornadaCaja.estado == EstadoJornada.ABIERTA)
        .order_by(JornadaCaja.fecha_negocio.desc())
        .first()
    )


def imputar_movimiento(
    db: Session, *, movimiento_uuid: str, momento: datetime
) -> "ImputacionMovimiento":
    """Destino contable de un movimiento aceptado (paquete 11, RF-45/50).

    Real abierta → imputa allí; real cerrada/inexistente + abierta actual
    → ajuste a la actual con referencia; sin abierta → pendiente (mantiene
    saldo, pide apertura). Idempotente por UUID. Sin commit.
    """
    from app.models.imputacion_corte import EstadoImputacion, ImputacionMovimiento

    existente = (
        db.query(ImputacionMovimiento)
        .filter(ImputacionMovimiento.movimiento_uuid == movimiento_uuid)
        .first()
    )
    if existente is not None:
        return existente
    real = fecha_negocio(momento)
    destino = jornada_abierta(db, fecha=real)
    if destino is None:
        destino = jornada_abierta_actual(db)
    if destino is None:
        fila = ImputacionMovimiento(
            movimiento_uuid=movimiento_uuid,
            jornada_real=real,
            jornada_destino_id=None,
            estado=EstadoImputacion.PENDIENTE,
        )
    else:
        fila = ImputacionMovimiento(
            movimiento_uuid=movimiento_uuid,
            jornada_real=real,
            jornada_destino_id=destino.id,
            estado=EstadoImputacion.IMPUTADO,
        )
    db.add(fila)
    db.flush()
    return fila
