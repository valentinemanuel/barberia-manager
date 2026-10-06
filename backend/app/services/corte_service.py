from sqlalchemy.orm import Session

from app.models.corte import Corte
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.services.dinero_cortes import calcular_partes


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
