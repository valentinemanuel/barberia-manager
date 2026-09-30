from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.corte import Corte
from app.models.servicio import Servicio
from app.models.usuario import Usuario


def calcular_partes(precio: Decimal, porcentaje_barbero: Decimal) -> tuple[Decimal, Decimal]:
    """
    Calcula la parte del barbero y la barbero.
    El porcentaje se aplica SOLO al servicio (corte).
    """
    parte_barbero = (precio * porcentaje_barbero / Decimal("100")).quantize(Decimal("0.01"))
    parte_barberia = (precio - parte_barbero).quantize(Decimal("0.01"))
    return parte_barbero, parte_barberia


def crear_corte(
    db: Session,
    barbero: Usuario,
    servicio_id: int,
    metodo_pago: str
) -> Corte:
    """Crea un registro de corte con cálculo automático de porcentajes."""
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id, Servicio.activo == True).first()
    if not servicio:
        raise ValueError("Servicio no encontrado o inactivo")

    parte_barbero, parte_barberia = calcular_partes(servicio.precio, barbero.porcentaje_ganancia)

    corte = Corte(
        barbero_id=barbero.id,
        servicio_id=servicio.id,
        precio=servicio.precio,
        porcentaje_barbero=barbero.porcentaje_ganancia,
        parte_barbero=parte_barbero,
        parte_barberia=parte_barberia,
        metodo_pago=metodo_pago,
    )
    db.add(corte)
    db.commit()
    db.refresh(corte)
    return corte
