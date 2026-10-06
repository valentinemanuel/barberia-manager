"""Edición y anullación de cortes (paquete 7, RF-22–27/RF-42 parcial).

Sin commit: la unidad de trabajo la posee el llamador.
"""
from sqlalchemy.orm import Session

from app.models.corte import Corte, MetodoPago
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.services.dinero_cortes import calcular_partes


class NoEncontrado(ValueError):
    """Recurso inexistente: el router lo vuelve 404 (sin revelar titularidad)."""


def editar_corte(
    db: Session,
    *,
    corte: Corte,
    servicio_id: int | None = None,
    metodo: MetodoPago | None = None,
) -> Corte:
    """Edita servicio y/o método de un corte no bloqueado ni anulado.

    El bloqueo/anulación se verifican en el router (T44/T45); aquí solo
    titularidad resuelta afuera, recálculo RF-42 y validación canónica.
    """
    if servicio_id is None and metodo is None:
        raise ValueError("Sin cambios para aplicar")
    if servicio_id is not None and servicio_id != corte.servicio_id:
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
    if metodo is not None:
        corte.metodo_pago = metodo
    db.flush()
    return corte
