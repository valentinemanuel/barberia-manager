from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.usuario import Usuario, Rol
from app.schemas.usuario import UsuarioCrear, UsuarioActualizar, UsuarioResponse

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Lista todos los usuarios (solo admin)."""
    return db.query(Usuario).all()


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Obtiene un usuario por ID (solo admin)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCrear,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Crea un nuevo usuario (solo admin)."""
    # Verificar email único
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    # Verificar nombre de usuario único
    if db.query(Usuario).filter(Usuario.usuario == datos.usuario).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    nuevo = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        usuario=datos.usuario,
        hashed_password=hash_password(datos.password),
        rol=datos.rol,
        porcentaje_ganancia=datos.porcentaje_ganancia,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizar,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Actualiza un usuario (solo admin)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if datos.email and datos.email != usuario.email:
        if db.query(Usuario).filter(Usuario.email == datos.email).first():
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        usuario.email = datos.email

    if datos.usuario and datos.usuario != usuario.usuario:
        if db.query(Usuario).filter(Usuario.usuario == datos.usuario).first():
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        usuario.usuario = datos.usuario

    if datos.password:
        usuario.hashed_password = hash_password(datos.password)
    if datos.nombre is not None:
        usuario.nombre = datos.nombre
    if datos.apellido is not None:
        usuario.apellido = datos.apellido
    if datos.rol is not None:
        usuario.rol = datos.rol
    if datos.porcentaje_ganancia is not None:
        usuario.porcentaje_ganancia = datos.porcentaje_ganancia
    if datos.activo is not None:
        usuario.activo = datos.activo

    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_admin)
):
    """Elimina un usuario (solo admin)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(usuario)
    db.commit()
    return None


@router.get("/me/perfil", response_model=UsuarioResponse)
def obtener_perfil(
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene el perfil del usuario actual."""
    return usuario
