from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import requerir_admin
from app.models.corte import Corte
from app.models.venta import Venta, TipoVenta
from app.models.gasto import Gasto
from app.models.usuario import Usuario, Rol
from app.schemas.reporte import ReporteDia, ReporteBarbero, DashboardAdmin

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


@router.get("/dashboard", response_model=DashboardAdmin)
def dashboard_admin(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Dashboard principal del administrador."""
    hoy = datetime.utcnow().date()
    inicio_dia = datetime(hoy.year, hoy.month, hoy.day)
    inicio_semana = inicio_dia - timedelta(days=hoy.weekday())
    inicio_mes = datetime(hoy.year, hoy.month, 1)

    # Ganancias por período
    ganancias_dia = _calcular_ganancias(db, inicio_dia)
    ganancias_semana = _calcular_ganancias(db, inicio_semana)
    ganancias_mes = _calcular_ganancias(db, inicio_mes)

    # Cortes por período
    cortes_dia = db.query(Corte).filter(Corte.fecha >= inicio_dia).count()
    cortes_semana = db.query(Corte).filter(Corte.fecha >= inicio_semana).count()
    cortes_mes = db.query(Corte).filter(Corte.fecha >= inicio_mes).count()

    # Top barberos
    top_barberos = (
        db.query(
            Usuario.id,
            Usuario.nombre,
            Usuario.apellido,
            func.count(Corte.id).label("cantidad_cortes"),
            func.sum(Corte.precio).label("total_bruto"),
            func.sum(Corte.parte_barbero).label("parte_barbero"),
            func.sum(Corte.parte_barberia).label("parte_barberia"),
        )
        .join(Corte, Usuario.id == Corte.barbero_id)
        .filter(Usuario.rol == Rol.BARBERO, Corte.fecha >= inicio_mes)
        .group_by(Usuario.id)
        .order_by(func.count(Corte.id).desc())
        .limit(5)
        .all()
    )

    # Productos más vendidos
    productos_top = (
        db.query(
            Venta.producto_id,
            func.sum(Venta.cantidad).label("total_vendido"),
        )
        .filter(Venta.tipo == TipoVenta.PRODUCTO, Venta.fecha >= inicio_mes)
        .group_by(Venta.producto_id)
        .order_by(func.sum(Venta.cantidad).desc())
        .limit(5)
        .all()
    )

    return DashboardAdmin(
        ganancias_hoy=ganancias_dia,
        ganancias_semana=ganancias_semana,
        ganancias_mes=ganancias_mes,
        cortes_hoy=cortes_dia,
        cortes_semana=cortes_semana,
        cortes_mes=cortes_mes,
        top_barberos=[
            ReporteBarbero(
                barbero_id=b.id,
                nombre_barbero=f"{b.nombre} {b.apellido}",
                cantidad_cortes=b.cantidad_cortes,
                total_bruto=b.total_bruto or Decimal("0"),
                parte_barbero=b.parte_barbero or Decimal("0"),
                parte_barberia=b.parte_barberia or Decimal("0"),
            )
            for b in top_barberos
        ],
        productos_mas_vendidos=[
            {"producto_id": p.producto_id, "total_vendido": p.total_vendido}
            for p in productos_top
        ],
    )


@router.get("/dia/{fecha}", response_model=ReporteDia)
def reporte_dia(
    fecha: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Reporte de un día específico."""
    from datetime import datetime as dt
    fecha_obj = dt.strptime(fecha, "%Y-%m-%d").date()
    inicio = datetime(fecha_obj.year, fecha_obj.month, fecha_obj.day)
    fin = inicio + timedelta(days=1)

    cortes = db.query(Corte).filter(Corte.fecha >= inicio, Corte.fecha < fin).all()
    ventas = db.query(Venta).filter(Venta.fecha >= inicio, Venta.fecha < fin).all()
    gastos = db.query(Gasto).filter(Gasto.fecha >= inicio, Gasto.fecha < fin).all()

    total_cortes = sum((c.precio for c in cortes), Decimal("0"))
    total_productos = sum((v.total for v in ventas if v.tipo == TipoVenta.PRODUCTO), Decimal("0"))
    total_consumibles = sum((v.total for v in ventas if v.tipo == TipoVenta.CONSUMIBLE), Decimal("0"))
    total_gastos = sum((g.monto for g in gastos), Decimal("0"))
    total_ingresos = total_cortes + total_productos + total_consumibles

    return ReporteDia(
        fecha=fecha_obj,
        total_cortes=total_cortes,
        total_productos=total_productos,
        total_consumibles=total_consumibles,
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        ganancia_neta=total_ingresos - total_gastos,
        cantidad_cortes=len(cortes),
    )


def _calcular_ganancias(db: Session, inicio: datetime) -> Decimal:
    """Calcula ganancias totales desde una fecha."""
    cortes = db.query(Corte).filter(Corte.fecha >= inicio).all()
    ventas = db.query(Venta).filter(Venta.fecha >= inicio).all()
    gastos = db.query(Gasto).filter(Gasto.fecha >= inicio).all()

    total_ingresos = (
        sum((c.precio for c in cortes), Decimal("0"))
        + sum((v.total for v in ventas), Decimal("0"))
    )
    total_gastos = sum((g.monto for g in gastos), Decimal("0"))

    return (total_ingresos - total_gastos).quantize(Decimal("0.01"))
