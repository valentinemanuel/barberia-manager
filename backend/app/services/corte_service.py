from datetime import datetime

from sqlalchemy.orm import Session

from app.models.corte import Corte
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.services.dinero_cortes import calcular_partes


def crear_corte(
    db: Session,
    barbero: Usuario,
    servicio_id: int,
    metodo_pago: str,
    destinatario: Usuario | None = None,
    momento_real: datetime | None = None,
    aceptar_inactivo: bool = False,
) -> Corte:
    """Crea un registro de corte con cálculo automático de porcentajes.

    El reparto usa precio actual del servicio y porcentaje actual del
    destinatario (actor por defecto, otro barbero si lo indica un admin).
    `aceptar_inactivo` solo lo usa la sincronización (RF-31): un servicio
    desactivado después del registro offline no invalida el corte; el
    registro online nuevo sigue exigiendo servicios activos (RF-56).
    """
    destino = destinatario or barbero
    consulta = db.query(Servicio).filter(Servicio.id == servicio_id)
    if not aceptar_inactivo:
        consulta = consulta.filter(Servicio.activo == True)
    servicio = consulta.first()
    if not servicio:
        raise ValueError("Servicio no encontrado o inactivo")

    try:
        parte_barbero, parte_barberia = calcular_partes(servicio.precio, destino.porcentaje_ganancia)
    except (TypeError, ValueError) as error:
        # Toda entrada monetaria inválida (incluido un no-Decimal llegado
        # desde almacenamiento) se rechaza con 400 en el router, nunca 500.
        raise ValueError(str(error)) from error

    corte = Corte(
        barbero_id=destino.id,
        servicio_id=servicio.id,
        precio=servicio.precio,
        porcentaje_barbero=destino.porcentaje_ganancia,
        parte_barbero=parte_barbero,
        parte_barberia=parte_barberia,
        metodo_pago=metodo_pago,
        fecha=momento_real or datetime.utcnow(),
    )
    db.add(corte)
    # Sin commit: la unidad de trabajo la posee el llamador (router online o
    # sync), con un solo commit por operacion. Flush asigna el ID.
    db.flush()
    db.refresh(corte)
    # Pertenencia tardía (paquete 11, RF-49, T76): si su jornada ya cerró,
    # se vincula por ajuste sin tocar el cierre original.
    from app.services.jornada_service import vincular_corte

    vincular_corte(db, corte_id=corte.id, autor_id=barbero.id)
    return corte
