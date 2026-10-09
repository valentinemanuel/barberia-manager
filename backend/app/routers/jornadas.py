"""Jornadas de negocio (paquete 11, RF-45 parcial).

Tablas y endpoints nuevos al lado del cierre legacy (`cierre_caja`,
snapshot aportado): ese flujo no se toca ni se reinterpreta.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin
from app.models.jornada_caja import EstadoJornada, JornadaCaja
from app.models.usuario import Usuario
from app.services.jornada_service import (
    JornadaExistente,
    JornadaInexistente,
    abrir_jornada,
    cerrar_jornada,
)

router = APIRouter(prefix="/api/jornadas", tags=["Jornadas"])


class JornadaAbrir(BaseModel):
    fecha: date


class JornadaResponse(BaseModel):
    id: int
    fecha_negocio: date
    estado: EstadoJornada

    class Config:
        from_attributes = True


@router.post("/abrir", response_model=JornadaResponse, status_code=201)
def abrir(
    datos: JornadaAbrir,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Apertura explícita de la jornada (solo admin, nunca automática)."""
    try:
        fila = abrir_jornada(db, admin=admin, fecha=datos.fecha)
    except JornadaExistente as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    db.refresh(fila)
    return fila


@router.post("/cerrar", response_model=JornadaResponse)
def cerrar(
    datos: JornadaAbrir,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Cierre inmutable de la jornada (solo admin, sin reapertura)."""
    try:
        fila = cerrar_jornada(db, admin=admin, fecha=datos.fecha)
    except (JornadaExistente, JornadaInexistente) as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    db.refresh(fila)
    return fila


@router.get("", response_model=list[JornadaResponse])
def listar(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Jornadas registradas (solo admin)."""
    return db.query(JornadaCaja).order_by(JornadaCaja.fecha_negocio).all()


class ResumenCaja(BaseModel):
    fecha: date
    estado: EstadoJornada
    devengado: dict
    cobros: dict
    pagos: dict
    ajustes: int
    desconocidos: int
    pendientes: int


@router.get("/resumen", response_model=ResumenCaja)
def resumen(
    fecha: date,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Caja de la jornada (paquete 11, RF-45 parcial, T77).

    Servicios realizados (devengado) separados del dinero cobrado/pagado
    por método; ajustes y desconocidos aparte. El cierre legacy no se
    toca: este resumen vive en endpoints nuevos.
    """
    from decimal import Decimal

    from app.models.corte import Corte
    from app.models.finanzas_corte import (
        ConceptoMovimiento,
        EstadoMovimiento,
        MovimientoCorte,
        TipoMovimiento,
    )
    from app.models.imputacion_corte import EstadoImputacion, ImputacionMovimiento
    from app.models.jornada_caja import AjusteCierre, PertenenciaCierre
    from app.services.jornada_service import rango_utc

    jornada = db.query(JornadaCaja).filter(JornadaCaja.fecha_negocio == fecha).first()
    if jornada is None:
        raise HTTPException(status_code=404, detail="Jornada no registrada")
    centavo = Decimal("0.01")
    if jornada.estado == EstadoJornada.CERRADA:
        filas = (
            db.query(PertenenciaCierre)
            .filter(PertenenciaCierre.jornada_id == jornada.id)
            .all()
        )
        n_cortes = len(filas)
        total_dev = sum((f.precio for f in filas), Decimal("0"))
    else:
        inicio, fin = rango_utc(fecha)
        cortes = (
            db.query(Corte)
            .filter(Corte.fecha >= inicio, Corte.fecha < fin, Corte.anulado_en.is_(None))
            .all()
        )
        n_cortes = len(cortes)
        total_dev = sum((c.precio for c in cortes), Decimal("0"))
    movs = (
        db.query(MovimientoCorte, ImputacionMovimiento)
        .join(ImputacionMovimiento, ImputacionMovimiento.movimiento_uuid == MovimientoCorte.uuid)
        .filter(
            ImputacionMovimiento.jornada_destino_id == jornada.id,
            MovimientoCorte.estado == EstadoMovimiento.ACEPTADO,
        )
        .all()
    )
    cobros = Decimal("0")
    pagos = Decimal("0")
    por_metodo: dict[str, Decimal] = {}
    for mov, _imp in movs:
        signo = Decimal("-1") if mov.tipo == TipoMovimiento.DEVOLUCION else Decimal("1")
        neto = mov.importe * signo
        if mov.concepto == ConceptoMovimiento.CLIENTE:
            cobros += neto
        else:
            pagos += neto
        if mov.tipo == TipoMovimiento.ABONO:
            metodo = mov.metodo_pago.value if hasattr(mov.metodo_pago, "value") else str(mov.metodo_pago)
            por_metodo[metodo] = por_metodo.get(metodo, Decimal("0")) + mov.importe
    ajustes = (
        db.query(AjusteCierre)
        .filter(
            (AjusteCierre.jornada_origen_id == jornada.id)
            | (AjusteCierre.jornada_destino_id == jornada.id)
        )
        .count()
    )
    inicio, fin = rango_utc(fecha)
    desconocidos = (
        db.query(Corte)
        .filter(Corte.fecha >= inicio, Corte.fecha < fin)
        .filter(
            (Corte.deuda_conocida.is_(False)) | (Corte.comision_conocida.is_(False))
        )
        .count()
    )
    pendientes = (
        db.query(ImputacionMovimiento)
        .filter(
            ImputacionMovimiento.jornada_real == fecha,
            ImputacionMovimiento.estado == EstadoImputacion.PENDIENTE,
        )
        .count()
    )
    return ResumenCaja(
        fecha=fecha,
        estado=jornada.estado,
        devengado={"cortes": n_cortes, "total": str(total_dev.quantize(centavo))},
        cobros={
            "total": str(cobros.quantize(centavo)),
            "por_metodo": {k: str(v.quantize(centavo)) for k, v in por_metodo.items()},
        },
        pagos={"total": str(pagos.quantize(centavo))},
        ajustes=ajustes,
        desconocidos=desconocidos,
        pendientes=pendientes,
    )


class AcumuladosResponse(BaseModel):
    periodo: str
    desde: date
    hasta: date
    comisiones: dict
    cobros: dict
    revision: dict
    excedentes: str


@router.get("/acumulados", response_model=AcumuladosResponse)
def acumulados(
    periodo: str,
    fecha: date,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
):
    """Acumulados en jornada de negocio (paquete 11, RF-52/RF-12 parcial, T78).

    Endpoints nuevos: día, semana Lun–Dom, mes calendario y total acotado.
    Comisiones por momento del servicio; dinero por saldos; revisión,
    excedentes y desconocidos siempre aparte de confirmados. Los resúmenes
    viejos quedan intactos.
    """
    import calendar
    from datetime import timedelta
    from decimal import Decimal

    from app.models.corte import Corte
    from app.models.finanzas_corte import EstadoMovimiento, MovimientoCorte
    from app.services.jornada_service import rango_utc
    from app.services.movimiento_corte_service import saldos_corte

    if periodo == "dia":
        desde = hasta = fecha
    elif periodo == "semana":
        desde = fecha - timedelta(days=fecha.weekday())
        hasta = desde + timedelta(days=6)
    elif periodo == "mes":
        desde = fecha.replace(day=1)
        hasta = fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])
    elif periodo == "total":
        primera = db.query(JornadaCaja).order_by(JornadaCaja.fecha_negocio).first()
        desde = primera.fecha_negocio if primera else fecha
        hasta = fecha
    else:
        raise HTTPException(status_code=400, detail="periodo debe ser dia, semana, mes o total")
    if desde > hasta:
        raise HTTPException(status_code=400, detail="rango inválido")
    inicio, _fin = rango_utc(desde)
    _inicio_fin, fin = rango_utc(hasta)
    centavo = Decimal("0.01")
    cortes = (
        db.query(Corte)
        .filter(Corte.fecha >= inicio, Corte.fecha < fin, Corte.anulado_en.is_(None))
        .all()
    )
    devengada = Decimal("0")
    pagada = Decimal("0")
    pendiente = Decimal("0")
    desconocida = Decimal("0")
    cobros_neto = Decimal("0")
    excedentes = Decimal("0")
    revision_cantidad = 0
    revision_total = Decimal("0")
    for corte in cortes:
        saldos = saldos_corte(db, corte)
        if corte.comision_conocida is False:
            desconocida += corte.parte_barbero
        else:
            devengada += corte.parte_barbero
            pagada += saldos["comision"]["abonado"]
            pendiente += saldos["comision"]["restante"]
        if corte.deuda_conocida is False:
            continue
        cobros_neto += saldos["cliente"]["abonado"]
        excedentes += saldos["cliente"]["excedente"] + saldos["comision"]["excedente"]
    revs = (
        db.query(MovimientoCorte)
        .join(Corte, Corte.id == MovimientoCorte.corte_id)
        .filter(
            MovimientoCorte.estado == EstadoMovimiento.REVISION,
            Corte.fecha >= inicio,
            Corte.fecha < fin,
            Corte.anulado_en.is_(None),
        )
        .all()
    )
    for mov in revs:
        revision_cantidad += 1
        revision_total += mov.importe
    return AcumuladosResponse(
        periodo=periodo,
        desde=desde,
        hasta=hasta,
        comisiones={
            "devengada": str(devengada.quantize(centavo)),
            "pagada": str(pagada.quantize(centavo)),
            "pendiente": str(pendiente.quantize(centavo)),
            "desconocida": str(desconocida.quantize(centavo)),
        },
        cobros={"neto": str(cobros_neto.quantize(centavo))},
        revision={"cantidad": revision_cantidad, "total": str(revision_total.quantize(centavo))},
        excedentes=str(excedentes.quantize(centavo)),
    )
