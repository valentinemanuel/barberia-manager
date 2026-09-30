from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import Token, UsuarioLogin
from app.services.auth_service import autenticar_usuario, crear_access_token

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Inicia sesión y retorna token JWT."""
    usuario = autenticar_usuario(db, form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    access_token = crear_access_token(usuario.id, usuario.rol.value)
    return Token(access_token=access_token)


@router.post("/login/json", response_model=Token)
def login_json(
    datos: UsuarioLogin,
    db: Session = Depends(get_db)
):
    """Inicia sesión con JSON y retorna token JWT."""
    usuario = autenticar_usuario(db, datos.usuario, datos.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    access_token = crear_access_token(usuario.id, usuario.rol.value)
    return Token(access_token=access_token)
