"""Ejecutor idempotente mínimo (paquete 5, RF-32/RF-57 parcial).

Una clave (actor, namespace, operación): el primer uso ejecuta el efecto y
guarda el acuse; el replay con el mismo hash devuelve el acuse sin reejecutar.
Misma clave con hash distinto → conflicto de identidad, sin efecto.
Sin commit: la unidad de trabajo la posee el llamador (T9).
"""
import hashlib
import json
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.operacion_corte import (
    EstadoOperacion,
    ModoCaptura,
    OperacionCorte,
)


def hash_canonico(payload: dict) -> str:
    """Hash estable del payload (claves ordenadas, sin espacios)."""
    texto = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class ConflictoIdentidad(ValueError):
    """Misma clave con distinto contenido: se rechaza sin efecto (HTTP 409)."""


def ejecutar_operacion(
    db: Session,
    *,
    actor_id: int,
    namespace: str,
    operacion_id: str,
    accion: str,
    payload: dict,
    modo: str,
    ejecutar: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Ejecuta una sola vez por clave; el replay devuelve el acuse guardado."""
    firma = hash_canonico(payload)
    existente = (
        db.query(OperacionCorte)
        .filter(
            OperacionCorte.actor_id == actor_id,
            OperacionCorte.namespace_cliente == namespace,
            OperacionCorte.operacion_id == operacion_id,
        )
        .first()
    )
    if existente is not None:
        if existente.hash_operacion != firma:
            raise ConflictoIdentidad(
                "Conflicto de identidad: la operación ya existe con otro contenido"
            )
        return dict(existente.resultado)

    resultado = ejecutar()
    db.add(
        OperacionCorte(
            actor_id=actor_id,
            namespace_cliente=namespace,
            operacion_id=operacion_id,
            accion=accion,
            hash_operacion=firma,
            modo_captura=ModoCaptura(modo),
            estado=EstadoOperacion.ACEPTADA,
            resultado=resultado,
        )
    )
    db.flush()
    return resultado
