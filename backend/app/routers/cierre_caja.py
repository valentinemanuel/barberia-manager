from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin
from app.models.cierre_caja import CierreCaja
from app.models.corte import Corte
from app.models.gasto import Gasto
from app.models.venta import Venta
from app.models.usuario import Usuario
from app.schemas.cierre_caja import CierreCajaCrear, CierreCajaResponse

router = APIRouter(prefix="/api/cierre-caja", tags=["Cierre de Caja"])


@router.get("/", response_model=list[CierreCajaResponse])
def listar_cierres(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
    skip: int = 0,
    limit: int = 30
):
    """Lista los cierres de caja (solo admin)."""
    return db.query(CierreCaja).order_by(CierreCaja.fecha.desc()).offset(skip).limit(limit).all()


@router.get("/{cierre_id}", response_model=CierreCajaResponse)
def obtener_cierre(
    cierre_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Obtiene un cierre de caja por ID (solo admin)."""
    cierre = db.query(CierreCaja).filter(CierreCaja.id == cierre_id).first()
    if not cierre:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return cierre


@router.post("/", response_model=CierreCajaResponse, status_code=status.HTTP_201_CREATED)
def crear_cierre(
    datos: CierreCajaCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Crea un cierre de caja (solo admin)."""
    # Calcular diferencia
    diferencia = (datos.total_en_caja - datos.monto_retirado - datos.total_ingresos).quantize(Decimal("0.01"))

    nuevo = CierreCaja(
        **datos.model_dump(),
        diferencia=diferencia,
        realizado_por_id=admin.id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/resumen/dia")
def resumen_dia(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Resumen del día para cierre de caja (solo admin)."""
    hoy = datetime.utcnow().date()
    inicio = datetime(hoy.year, hoy.month, hoy.day)

    # Total cortes
    cortes = db.query(Corte).filter(Corte.fecha >= inicio).all()
    total_cortes = sum(c.precio for c in cortes)

    # Total productos y consumibles
    ventas = db.query(Venta).filter(Venta.fecha >= inicio).all()
    total_productos = sum(v.total for v in ventas if v.tipo.value == "producto")
    total_consumibles = sum(v.total for v in ventas if v.tipo.value == "consumible")

    # Total gastos
    gastos = db.query(Gasto).filter(Gasto.fecha >= inicio).all()
    total_gastos = sum(g.monto for g in gastos)

    total_ingresos = total_cortes + total_productos + total_consumibles

    return {
        "fecha": hoy,
        "total_cortes": total_cortes,
        "total_productos": total_productos,
        "total_consumibles": total_consumibles,
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "ganancia_neta": total_ingresos - total_gastos,
        "cantidad_cortes": len(cortes),
    }
