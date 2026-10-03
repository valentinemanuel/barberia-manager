from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import config
from app.database import get_db
from app.models.usuario import Usuario, Rol
from app.schemas.usuario import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def crear_token(data: dict) -> str:
    """Crea un token JWT."""
    to_encode = data.copy()
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


def verificar_token(token: str) -> TokenData:
    """Verifica y decodifica un token JWT."""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        sub = payload.get("sub")
        rol: str = payload.get("rol")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            usuario_id = int(sub)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(usuario_id=usuario_id, rol=rol)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    """Obtiene el usuario actual desde el token JWT."""
    token_data = verificar_token(token)
    usuario = db.query(Usuario).filter(Usuario.id == token_data.usuario_id).first()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )
    return usuario


def requerir_admin(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
    """Verifica que el usuario sea administrador."""
    if usuario.rol != Rol.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return usuario


def requerir_barbero(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
    """Verifica que el usuario sea barbero o admin."""
    if usuario.rol not in [Rol.BARBERO, Rol.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado",
        )
    return usuario
