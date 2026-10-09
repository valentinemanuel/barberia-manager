"""Jornada de negocio y regla de imputación (paquete 11, RF-45/RF-50).

Puro + UoW sin commit: la unidad de trabajo la posee el llamador.
Sin zona en config: `America/Argentina/Buenos_Aires` es contractual (DA-8).
"""
from datetime import date, datetime, timedelta
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
    # Incorporación con snapshot congelado (RF-49, T76): lo que no estaba
    # aceptado aún llegará como tardío por ajuste, sin mutar el cierre.
    incorporar_jornada(db, jornada=fila)
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


def rango_utc(fecha: date) -> tuple[datetime, datetime]:
    """Intervalo [00:00, 00:00 siguiente) de la jornada en UTC naive."""
    inicio = datetime(fecha.year, fecha.month, fecha.day, tzinfo=ZONA_NEGOCIO)
    fin = inicio + timedelta(days=1)
    utc = ZoneInfo("UTC")
    return (
        inicio.astimezone(utc).replace(tzinfo=None),
        fin.astimezone(utc).replace(tzinfo=None),
    )


def incorporar_jornada(db: Session, *, jornada: JornadaCaja) -> int:
    """Vincula los cortes de la jornada con snapshot congelado (RF-49).

    Solo no anulados sin pertenencia. Inmutable: nunca reescribe.
    Devuelve la cantidad incorporada. Sin commit.
    """
    from app.models.corte import Corte
    from app.models.jornada_caja import PertenenciaCierre

    inicio, fin = rango_utc(jornada.fecha_negocio)
    candidatos = (
        db.query(Corte)
        .filter(
            Corte.fecha >= inicio,
            Corte.fecha < fin,
            Corte.anulado_en.is_(None),
        )
        .all()
    )
    incorporados = 0
    for corte in candidatos:
        existe = (
            db.query(PertenenciaCierre)
            .filter(PertenenciaCierre.corte_id == corte.id)
            .first()
        )
        if existe is not None:
            continue
        db.add(PertenenciaCierre(
            jornada_id=jornada.id,
            corte_id=corte.id,
            servicio_id=corte.servicio_id,
            precio=corte.precio,
            porcentaje_barbero=corte.porcentaje_barbero,
            parte_barbero=corte.parte_barbero,
            version_corte=corte.version or 1,
            es_tardio=False,
        ))
        incorporados += 1
    db.flush()
    return incorporados


def corte_en_cierre(db: Session, *, corte_id: int) -> bool:
    """Pertenencia verificada (nunca inferida por fecha)."""
    from app.models.jornada_caja import PertenenciaCierre

    return (
        db.query(PertenenciaCierre)
        .filter(PertenenciaCierre.corte_id == corte_id)
        .first()
        is not None
    )


def vincular_corte(db: Session, *, corte_id: int, autor_id: int) -> None:
    """Vincula un corte recién aceptado a su jornada (RF-49, T76).

    Jornada inexistente o abierta: nada (el cierre incorporará).
    Jornada cerrada: pertenencia tardía + ajuste referenciado, sin tocar
    el snapshot del cierre original. Sin commit.
    """
    from app.models.corte import Corte
    from app.models.jornada_caja import (
        AjusteCierre,
        PertenenciaCierre,
        TipoAjuste,
    )

    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if corte is None or corte.anulado_en is not None:
        return
    if corte_en_cierre(db, corte_id=corte_id):
        return
    jornada = (
        db.query(JornadaCaja)
        .filter(JornadaCaja.fecha_negocio == fecha_negocio(corte.fecha))
        .first()
    )
    if jornada is None or jornada.estado != EstadoJornada.CERRADA:
        return
    db.add(PertenenciaCierre(
        jornada_id=jornada.id,
        corte_id=corte.id,
        servicio_id=corte.servicio_id,
        precio=corte.precio,
        porcentaje_barbero=corte.porcentaje_barbero,
        parte_barbero=corte.parte_barbero,
        version_corte=corte.version or 1,
        es_tardio=True,
    ))
    db.flush()
    db.add(AjusteCierre(
        tipo=TipoAjuste.TARDIO,
        corte_id=corte.id,
        jornada_origen_id=jornada.id,
        jornada_destino_id=None,
        detalle={"pertenencia": "tardia", "momento_real": corte.fecha.isoformat()},
        autor_id=autor_id,
        motivo="Corte tardío de jornada cerrada",
    ))
    db.flush()


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
