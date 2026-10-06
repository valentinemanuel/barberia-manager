from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.corte import Corte
from app.models.usuario import Usuario, Rol
from app.schemas.corte import CorteCrear, CorteResponse, CortePersonal
from app.services.corte_service import crear_corte
from app.services.operacion_corte_service import (
    ConflictoIdentidad,
    ReintentosAgotados,
    ejecutar_operacion,
)

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


@router.get("/mi/historial", response_model=list[CortePersonal])
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


@router.get("/{corte_id}", response_model=CortePersonal)
def obtener_corte(
    corte_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene un corte por ID."""
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    # Barberos solo pueden ver sus propios cortes; se devuelve 404
    # para no revelar la existencia de cortes ajenos
    if usuario.rol == Rol.BARBERO and corte.barbero_id != usuario.id:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    return corte


@router.post("/", response_model=CortePersonal, status_code=status.HTTP_201_CREATED)
def registrar_corte(
    datos: CorteCrear,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual)
):
    """Registra un nuevo corte (propio; el admin puede indicar destinatario)."""
    try:
        destino = actor
        if datos.barbero_id is not None:
            if actor.rol != Rol.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo un admin puede registrar cortes para otro barbero",
                )
            destino = db.query(Usuario).filter(Usuario.id == datos.barbero_id).first()
            if not destino:
                raise HTTPException(status_code=404, detail="Barbero no encontrado")
            # Decisión RF-2: el destino de un tercero debe ser barbero; el
            # propio siempre está permitido (registro propio del admin).
            if destino.id != actor.id and destino.rol != Rol.BARBERO:
                raise HTTPException(
                    status_code=400, detail="El destinatario debe ser un barbero"
                )
        momento = datos.momento_real
        if momento is not None:
            if actor.rol != Rol.ADMIN:
                raise HTTPException(
                    status_code=400,
                    detail="Solo un admin puede indicar el momento real",
                )
            if momento.tzinfo is not None:
                momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
            if momento > datetime.utcnow():
                raise HTTPException(
                    status_code=400, detail="El momento real no puede ser futuro"
                )

        creado_id: int | None = None

        def _efecto() -> dict:
            nonlocal creado_id
            creado = crear_corte(
                db, actor, datos.servicio_id, datos.metodo_pago, destino, momento
            )
            creado_id = creado.id
            return {"corte_id": creado.id, "estado": "aceptada"}

        if datos.operacion_uuid is None:
            _efecto()
            corte = db.query(Corte).filter(Corte.id == creado_id).first()
            db.commit()
        else:
            # Contención: el commit puede perder contra otro escritor con la
            # misma clave; rollback + reintento converge al acuse del ganador.
            for _intento in range(3):
                try:
                    acuse = ejecutar_operacion(
                        db,
                        actor_id=actor.id,
                        namespace="web",
                        operacion_id=str(datos.operacion_uuid),
                        accion="crear_corte",
                        payload={
                            "servicio_id": str(datos.servicio_id),
                            "metodo_pago": str(datos.metodo_pago),
                            "barbero_id": (
                                "" if datos.barbero_id is None else str(datos.barbero_id)
                            ),
                            "momento_real": (
                                "" if datos.momento_real is None else datos.momento_real.isoformat()
                            ),
                        },
                        modo="online",
                        ejecutar=_efecto,
                    )
                    corte = db.query(Corte).filter(Corte.id == acuse["corte_id"]).first()
                    db.commit()
                    break
                except (IntegrityError, OperationalError):
                    db.rollback()
                    continue
            else:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo registrar por contención; reintente",
                )
        db.refresh(corte)
        return corte
    except ReintentosAgotados as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ConflictoIdentidad as e:
        raise HTTPException(status_code=409, detail=str(e))
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
