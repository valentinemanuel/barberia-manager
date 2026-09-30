from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.corte import Corte
from app.models.usuario import Usuario, Rol
from app.schemas.corte import CorteCrear, CorteResponse
from app.services.corte_service import crear_corte

router = APIRouter(prefix="/api/cortes", tags=["Cortes"])


@router.get("/", response_model=list[CorteResponse])
def listar_cortes(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
    skip: int = 0,
    limit: int = 100
):
    """Lista todos los cortes (solo admin)."""
    return db.query(Corte).order_by(Corte.fecha.desc()).offset(skip).limit(limit).all()


@router.get("/mi/historial", response_model=list[CorteResponse])
def mis_cortes(
    db: Session = Depends(get_db),
    barbero: Usuario = Depends(obtener_usuario_actual),
    skip: int = 0,
    limit: int = 100
):
    """Lista los cortes del barbero actual."""
    return (
        db.query(Corte)
        .filter(Corte.barbero_id == barbero.id)
        .order_by(Corte.fecha.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{corte_id}", response_model=CorteResponse)
def obtener_corte(
    corte_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene un corte por ID."""
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    # Barberos solo pueden ver sus propios cortes
    if usuario.rol == Rol.BARBERO and corte.barbero_id != usuario.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return corte


@router.post("/", response_model=CorteResponse, status_code=status.HTTP_201_CREATED)
def registrar_corte(
    datos: CorteCrear,
    db: Session = Depends(get_db),
    barbero: Usuario = Depends(obtener_usuario_actual)
):
    """Registra un nuevo corte."""
    try:
        corte = crear_corte(db, barbero, datos.servicio_id, datos.metodo_pago)
        return corte
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mi/resumen/dia")
def resumen_dia(
    db: Session = Depends(get_db),
    barbero: Usuario = Depends(obtener_usuario_actual)
):
    """Resumen del día para el barbero actual."""
    hoy = datetime.utcnow().date()
    inicio = datetime(hoy.year, hoy.month, hoy.day)

    cortes = (
        db.query(Corte)
        .filter(
            Corte.barbero_id == barbero.id,
            Corte.fecha >= inicio
        )
        .all()
    )

    total_cortes = len(cortes)
    acumulado = sum(c.parte_barbero for c in cortes)

    return {
        "fecha": hoy,
        "total_cortes": total_cortes,
        "acumulado": acumulado,
        "porcentaje_asignado": barbero.porcentaje_ganancia,
    }


@router.get("/mi/resumen/semana")
def resumen_semana(
    db: Session = Depends(get_db),
    barbero: Usuario = Depends(obtener_usuario_actual)
):
    """Resumen de la semana para el barbero actual."""
    hoy = datetime.utcnow().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio = datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day)

    cortes = (
        db.query(Corte)
        .filter(
            Corte.barbero_id == barbero.id,
            Corte.fecha >= inicio
        )
        .all()
    )

    total_cortes = len(cortes)
    acumulado = sum(c.parte_barbero for c in cortes)

    return {
        "semana_inicio": inicio_semana,
        "total_cortes": total_cortes,
        "acumulado": acumulado,
        "porcentaje_asignado": barbero.porcentaje_ganancia,
    }


@router.get("/mi/resumen/mes")
def resumen_mes(
    db: Session = Depends(get_db),
    barbero: Usuario = Depends(obtener_usuario_actual)
):
    """Resumen del mes para el barbero actual."""
    hoy = datetime.utcnow().date()
    inicio = datetime(hoy.year, hoy.month, 1)

    cortes = (
        db.query(Corte)
        .filter(
            Corte.barbero_id == barbero.id,
            Corte.fecha >= inicio
        )
        .all()
    )

    total_cortes = len(cortes)
    acumulado = sum(c.parte_barbero for c in cortes)

    return {
        "mes": hoy.month,
        "anio": hoy.year,
        "total_cortes": total_cortes,
        "acumulado": acumulado,
        "porcentaje_asignado": barbero.porcentaje_ganancia,
    }
