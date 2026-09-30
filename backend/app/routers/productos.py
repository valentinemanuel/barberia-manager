from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.schemas.producto import ProductoCrear, ProductoActualizar, ProductoResponse

router = APIRouter(prefix="/api/productos", tags=["Productos"])


@router.get("/", response_model=list[ProductoResponse])
def listar_productos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Lista todos los productos activos."""
    return db.query(Producto).filter(Producto.activo == True).all()


@router.get("/stock-bajo", response_model=list[ProductoResponse])
def productos_stock_bajo(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Lista productos con stock bajo (solo admin)."""
    return db.query(Producto).filter(
        Producto.activo == True,
        Producto.stock <= Producto.stock_minimo
    ).all()


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene un producto por ID."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Crea un nuevo producto (solo admin)."""
    nuevo = Producto(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Actualiza un producto (solo admin)."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(producto, campo, valor)

    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Elimina un producto (solo admin)."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.activo = False
    db.commit()
    return None
