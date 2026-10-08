"""Edición y anulación de cortes (paquete 7, RF-22–27/RF-42 parcial).

Sin commit: la unidad de trabajo la posee el llamador.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.auditoria_corte import AccionAuditoriaCorte, AuditoriaCorte
from app.models.corte import Corte, MetodoPago
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.services.dinero_cortes import calcular_partes


class NoEncontrado(ValueError):
    """Recurso inexistente: el router lo vuelve 404 (sin revelar titularidad)."""


def anular_corte(
    db: Session,
    *,
    corte: Corte,
    actor: Usuario,
    motivo: str | None = None,
) -> Corte:
    """Anulación terminal (RF-27): conserva fila y movimientos, sin borrado.

    No reactiva ni permite edición posterior (verificación en router T45).
    """
    corte.anulado_en = datetime.utcnow()
    corte.anulado_motivo = motivo
    corte.anulado_por = actor.id
    db.flush()
    return corte


def snapshot_corte(corte: Corte) -> dict:
    """Snapshot explícito para el journal (Decimal como strings exactos)."""
    return {
        "servicio_id": corte.servicio_id,
        "metodo_pago": corte.metodo_pago.value
        if isinstance(corte.metodo_pago, MetodoPago)
        else str(corte.metodo_pago),
        "precio": str(corte.precio),
        "porcentaje_barbero": str(corte.porcentaje_barbero),
        "parte_barbero": str(corte.parte_barbero),
        "parte_barberia": str(corte.parte_barberia),
        "anulado_en": corte.anulado_en.isoformat() if corte.anulado_en else None,
        "anulado_motivo": corte.anulado_motivo,
    }


def auditar_cambio(
    db: Session,
    *,
    corte_id: int,
    actor_id: int,
    accion: AccionAuditoriaCorte,
    antes: dict,
    despues: dict,
    motivo: str | None = None,
) -> AuditoriaCorte:
    """Agrega una fila append-only al journal (misma UoW, sin commit)."""
    fila = AuditoriaCorte(
        corte_id=corte_id,
        actor_id=actor_id,
        accion=accion,
        antes=antes,
        despues=despues,
        motivo=motivo,
    )
    db.add(fila)
    db.flush()
    return fila


def editar_corte(
    db: Session,
    *,
    corte: Corte,
    servicio_id: int | None = None,
    metodo: MetodoPago | None = None,
    instante: datetime | None = None,
) -> tuple[Corte, dict]:
    """Edita servicio y/o método de un corte no bloqueado ni anulado.

    LWW por unidades (paquete 10, RF-36 parcial): método y finanzas
    (servicio/precio/porcentaje/reparto como grupo atómico) compiten cada
    una con su reloj; gana el instante mayor o igual, la perdedora se
    omite con causa (nunca silenciosa). El bloqueo/anulación se verifican
    en el router (T44/T45); aquí solo titularidad resuelta afuera,
    recálculo RF-42 y validación canónica.
    """
    from datetime import datetime as datetime_lww

    if servicio_id is None and metodo is None:
        raise ValueError("Sin cambios para aplicar")
    ahora = instante or datetime_lww.utcnow()
    unidades: dict[str, str] = {}
    if servicio_id is not None and servicio_id != corte.servicio_id:
        if corte.unidad_finanzas_ts is None or ahora >= corte.unidad_finanzas_ts:
            servicio = (
                db.query(Servicio).filter(Servicio.id == servicio_id).first()
            )
            if servicio is None:
                raise NoEncontrado("Servicio no encontrado")
            if not servicio.activo:
                raise ValueError("Servicio inactivo")
            titular = db.query(Usuario).filter(Usuario.id == corte.barbero_id).first()
            if titular is None:
                raise NoEncontrado("Barbero no encontrado")
            try:
                parte_barbero, parte_barberia = calcular_partes(
                    servicio.precio, titular.porcentaje_ganancia
                )
            except (TypeError, ValueError) as error:
                raise ValueError(str(error)) from error
            corte.servicio_id = servicio.id
            corte.precio = servicio.precio
            corte.porcentaje_barbero = titular.porcentaje_ganancia
            corte.parte_barbero = parte_barbero
            corte.parte_barberia = parte_barberia
            corte.unidad_finanzas_ts = ahora
            unidades["finanzas"] = "aplicada"
        else:
            unidades["finanzas"] = "omitida"
    if metodo is not None:
        if corte.unidad_metodo_ts is None or ahora >= corte.unidad_metodo_ts:
            corte.metodo_pago = metodo
            corte.unidad_metodo_ts = ahora
            unidades["metodo"] = "aplicada"
        else:
            unidades["metodo"] = "omitida"
    if any(v == "aplicada" for v in unidades.values()):
        corte.version = (corte.version or 0) + 1
    db.flush()
    return corte, unidades
