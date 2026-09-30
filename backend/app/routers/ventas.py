from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.producto import Producto
from app.models.consumible import Consumible
from app.models.venta import Venta, TipoVenta
from app.models.usuario import Usuario
from app.schemas.venta import VentaCrear, VentaResponse

router = APIRouter(prefix="/api/ventas", tags=["Ventas"])


@router.get("/", response_model=list[VentaResponse])
def listar_ventas(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin),
    skip: int = 0,
    limit: int = 100
):
    """Lista todas las ventas (solo admin)."""
    return db.query(Venta).order_by(Venta.fecha.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=VentaResponse, status_code=status.HTTP_201_CREATED)
def crear_venta(
    datos: VentaCrear,
    db: Session = Depends(get_db),
    barbero: Usuario = Depends(obtener_usuario_actual)
):
    """Crea una venta de producto o consumible."""
    total = (datos.precio_unitario * datos.cantidad).quantize(Decimal("0.01"))

    # Actualizar stock
    if datos.tipo == TipoVenta.PRODUCTO and datos.producto_id:
        producto = db.query(Producto).filter(Producto.id == datos.producto_id).first()
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if producto.stock < datos.cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
        producto.stock -= datos.cantidad
    elif datos.tipo == TipoVenta.CONSUMIBLE and datos.consumible_id:
        consumible = db.query(Consumible).filter(Consumible.id == datos.consumible_id).first()
        if not consumible:
            raise HTTPException(status_code=404, detail="Consumible no encontrado")
        if consumible.stock < datos.cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
        consumible.stock -= datos.cantidad

    nueva = Venta(
        **datos.model_dump(),
        total=total,
        barbero_id=barbero.id,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva
