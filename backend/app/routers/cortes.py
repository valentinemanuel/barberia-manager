from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.corte import Corte, MetodoPago
from app.models.usuario import Usuario, Rol
from app.schemas.corte import (
    CobroInicial,
    CorteAnular,
    CorteCrear,
    CorteEditar,
    CorteEdicionResponse,
    CorteResponse,
    CortePersonal,
    IntervencionResolver,
    IntervencionResponse,
    JustificanteResponse,
)
from app.services.corte_service import crear_corte
from app.services.edicion_corte_service import (
    NoEncontrado,
    anular_corte as aplicar_anulacion,
    auditar_cambio,
    editar_corte as aplicar_edicion,
    snapshot_corte,
)
from app.models.auditoria_corte import AccionAuditoriaCorte
from app.services.movimiento_corte_service import corte_bloqueado
from app.services.movimiento_corte_service import registrar_abono, saldos_corte
from app.models.finanzas_corte import ConceptoMovimiento, MovimientoCorte
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


@router.get("/mi/justificantes", response_model=list[JustificanteResponse])
def mis_justificantes(
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Justificantes monetarios propios (paquete 10, RF-48 parcial).

    Tras una reasignación, el profesional anterior conserva únicamente
    sus filas comisionadas (sin datos del nuevo titular); el aislamiento
    es por `profesional_id`, nunca filtrado en pantalla.
    """
    filas = (
        db.query(MovimientoCorte)
        .filter(
            MovimientoCorte.profesional_id == actor.id,
            MovimientoCorte.concepto == ConceptoMovimiento.COMISION,
        )
        .order_by(MovimientoCorte.id)
        .all()
    )
    return [
        JustificanteResponse(
            corte_id=fila.corte_id,
            uuid=fila.uuid,
            concepto=fila.concepto,
            tipo=fila.tipo.value if fila.tipo else None,
            importe=fila.importe,
            motivo=fila.motivo,
            momento_real=fila.momento_real,
            registrado_en=fila.registrado_en,
        )
        for fila in filas
    ]


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
            # Cobro inicial en la misma UoW (RF-37); nunca marca comisión.
            if datos.cobro_inicial == CobroInicial.PARCIAL:
                if datos.importe_cobro is None:
                    raise ValueError("El cobro parcial requiere importe")
                registrar_abono(
                    db,
                    autor=actor,
                    corte=creado,
                    concepto=ConceptoMovimiento.CLIENTE,
                    importe=datos.importe_cobro,
                    metodo=datos.metodo_pago,
                )
            elif datos.cobro_inicial == CobroInicial.COMPLETO:
                registrar_abono(
                    db,
                    autor=actor,
                    corte=creado,
                    concepto=ConceptoMovimiento.CLIENTE,
                    importe=creado.precio,
                    metodo=datos.metodo_pago,
                )
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
                            "cobro_inicial": (
                                "" if datos.cobro_inicial is None else str(datos.cobro_inicial)
                            ),
                            "importe_cobro": (
                                "" if datos.importe_cobro is None else str(datos.importe_cobro)
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


@router.patch("/{corte_id}", response_model=CorteEdicionResponse)
def editar_corte_endpoint(
    corte_id: int,
    datos: CorteEditar,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Edita servicio y/o método de un corte propio no bloqueado (RF-22/42).

    LWW por unidades (paquete 10, RF-36): el instante decide por unidad;
    la anulación terminal prevalece siempre (409). El bloqueo y la
    anulación se verifican en T44/T45; aquí titularidad y recálculo.
    El admin opera sobre cualquier corte (gestión).
    """
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    if actor.rol != Rol.ADMIN and corte.barbero_id != actor.id:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    if corte.anulado_en is not None:
        raise HTTPException(status_code=409, detail="Corte anulado: no admite edición")
    if actor.rol != Rol.ADMIN and corte_bloqueado(db, corte):
        raise HTTPException(
            status_code=409, detail="Corte bloqueado: tiene pagos registrados"
        )
    if (
        actor.rol == Rol.ADMIN
        and corte_bloqueado(db, corte)
        and not datos.motivo
    ):
        raise HTTPException(
            status_code=400,
            detail="Corregir un corte bloqueado exige motivo",
        )
    if datos.barbero_id is not None and actor.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Solo un admin reasigna cortes")
    if datos.barbero_id is not None and not datos.motivo:
        raise HTTPException(
            status_code=400, detail="Reasignar un corte exige motivo"
        )
    if datos.momento_real is not None and actor.rol != Rol.ADMIN:
        raise HTTPException(status_code=400, detail="Solo un admin corrige el momento real")
    momento = datos.momento_real
    if momento is not None:
        if momento.tzinfo is not None:
            momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
        if momento > datetime.utcnow():
            raise HTTPException(
                status_code=400, detail="El momento real no puede ser futuro"
            )
        if not datos.motivo:
            raise HTTPException(
                status_code=400, detail="Corregir el momento real exige motivo"
            )
    try:
        antes = snapshot_corte(corte)
        instante = datos.instante_cambio
        if instante is not None and instante.tzinfo is not None:
            instante = instante.astimezone(timezone.utc).replace(tzinfo=None)
        corte, unidades = aplicar_edicion(
            db,
            corte=corte,
            servicio_id=datos.servicio_id,
            metodo=datos.metodo_pago,
            instante=instante,
            nuevo_barbero_id=datos.barbero_id,
            momento_real=momento,
        )
        despues = snapshot_corte(corte)
        despues["unidades"] = unidades
        if datos.operacion_uuid:
            despues["operacion_uuid"] = datos.operacion_uuid
        if datos.bases:
            despues["bases_vistas"] = datos.bases
        auditar_cambio(
            db,
            corte_id=corte.id,
            actor_id=actor.id,
            accion=AccionAuditoriaCorte.EDICION,
            antes=antes,
            despues=despues,
            motivo=datos.motivo,
        )
    except NoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.commit()
    db.refresh(corte)
    respuesta = CorteEdicionResponse.model_validate(corte)
    respuesta.unidades = unidades
    return respuesta


@router.post("/intervenciones/{uuid}/resolver", response_model=IntervencionResponse)
def resolver_intervencion_endpoint(
    uuid: str,
    datos: IntervencionResolver,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Resuelve manualmente una intervención RF-40 (solo admin).

    `aplicar` ejecuta la edición/anulación con las reglas vigentes y
    motivo obligatorio; `descartar` la cierra sin efecto. Nada se
    auto-aplica: ambas ramas exigen motivo y dejan journal.
    """
    from app.models.intervencion_corte import EstadoIntervencion, IntervencionCorte

    if actor.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Solo un admin resuelve intervenciones")
    intervencion = (
        db.query(IntervencionCorte).filter(IntervencionCorte.uuid == uuid).first()
    )
    if not intervencion:
        raise HTTPException(status_code=404, detail="Intervención no encontrada")
    if intervencion.estado != EstadoIntervencion.PENDIENTE:
        raise HTTPException(status_code=409, detail="La intervención ya fue resuelta")
    if not datos.motivo or not datos.motivo.strip():
        raise HTTPException(status_code=400, detail="La resolución exige motivo")
    if datos.decision == "descartar":
        intervencion.estado = EstadoIntervencion.DESCARTADA
        intervencion.motivo_resolucion = datos.motivo.strip()
        intervencion.resuelta_en = datetime.utcnow()
        intervencion.resuelta_por = actor.id
        db.commit()
        db.refresh(intervencion)
        return intervencion
    corte = db.query(Corte).filter(Corte.id == intervencion.corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    if corte.anulado_en is not None:
        raise HTTPException(status_code=409, detail="Corte anulado: no admite edición")
    try:
        antes = snapshot_corte(corte)
        cambios = intervencion.cambios.get("cambios", {}) if isinstance(intervencion.cambios, dict) else {}
        if intervencion.accion == "anular":
            corte = aplicar_anulacion(db, corte=corte, actor=actor, motivo=datos.motivo)
            accion = AccionAuditoriaCorte.ANULACION
            despues = snapshot_corte(corte)
        else:
            metodo = None
            if cambios.get("metodo_pago") is not None:
                metodo = MetodoPago(cambios["metodo_pago"])
            servicio_id = cambios.get("servicio_id")
            corte, unidades = aplicar_edicion(
                db,
                corte=corte,
                servicio_id=int(servicio_id) if servicio_id is not None else None,
                metodo=metodo,
                instante=datetime.utcnow(),
            )
            accion = AccionAuditoriaCorte.EDICION
            despues = {**snapshot_corte(corte), "unidades": unidades,
                       "intervencion_uuid": intervencion.uuid}
        auditar_cambio(
            db,
            corte_id=corte.id,
            actor_id=actor.id,
            accion=accion,
            antes=antes,
            despues=despues,
            motivo=datos.motivo,
        )
    except NoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    intervencion.estado = EstadoIntervencion.APLICADA
    intervencion.motivo_resolucion = datos.motivo.strip()
    intervencion.resuelta_en = datetime.utcnow()
    intervencion.resuelta_por = actor.id
    db.commit()
    db.refresh(intervencion)
    return intervencion


@router.post("/{corte_id}/anular", response_model=CortePersonal)
def anular_corte_endpoint(
    corte_id: int,
    datos: CorteAnular,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(obtener_usuario_actual),
):
    """Anula un corte conservando fila y movimientos (RF-27, terminal).

    El barbero solo anula propios no bloqueados; el admin anula bloqueados
    con motivo obligatorio (RF-26). Nunca reactiva ni admite edición posterior.
    """
    corte = db.query(Corte).filter(Corte.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    if actor.rol != Rol.ADMIN and corte.barbero_id != actor.id:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    if corte.anulado_en is not None:
        raise HTTPException(status_code=409, detail="Corte anulado: ya está anulado")
    bloqueado = corte_bloqueado(db, corte)
    if actor.rol != Rol.ADMIN and bloqueado:
        raise HTTPException(
            status_code=409, detail="Corte bloqueado: tiene pagos registrados"
        )
    if actor.rol == Rol.ADMIN and bloqueado and not datos.motivo:
        raise HTTPException(
            status_code=400,
            detail="Anular un corte bloqueado exige motivo",
        )
    antes_anulacion = snapshot_corte(corte)
    corte = aplicar_anulacion(db, corte=corte, actor=actor, motivo=datos.motivo)
    # Efecto al anular (RF-27/46, T62): obligaciones canceladas y neto
    # existente como excedente; queda trazado en esta fila de journal.
    saldos_efecto = saldos_corte(db, corte)
    despues_anulacion = snapshot_corte(corte)
    despues_anulacion["obligaciones_canceladas"] = True
    despues_anulacion["neto_cliente"] = str(saldos_efecto["cliente"]["abonado"])
    despues_anulacion["excedente_cliente"] = str(saldos_efecto["cliente"]["excedente"])
    despues_anulacion["neto_comision"] = str(saldos_efecto["comision"]["abonado"])
    despues_anulacion["excedente_comision"] = str(saldos_efecto["comision"]["excedente"])
    auditar_cambio(
        db,
        corte_id=corte.id,
        actor_id=actor.id,
        accion=AccionAuditoriaCorte.ANULACION,
        antes=antes_anulacion,
        despues=despues_anulacion,
        motivo=datos.motivo,
    )
    db.commit()
    db.refresh(corte)
    return corte


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
            Corte.fecha >= inicio,
            Corte.anulado_en.is_(None)
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
            Corte.fecha >= inicio,
            Corte.anulado_en.is_(None)
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
            Corte.fecha >= inicio,
            Corte.anulado_en.is_(None)
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
