from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import config
from app.models.usuario import Usuario
from app.dependencies import crear_token


def autenticar_usuario(db: Session, usuario: str, password: str) -> Usuario | None:
    """Autentica un usuario por nombre de usuario y contraseña."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = db.query(Usuario).filter(Usuario.usuario == usuario).first()
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user


def crear_access_token(usuario_id: int, rol: str) -> str:
    """Crea un token de acceso JWT."""
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {
        "sub": str(usuario_id),
        "rol": rol,
        "exp": expire,
    }
    return crear_token(data)
