import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.usuario import Usuario, Rol
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def crear_admin():
    """Crea el usuario administrador inicial."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Verificar si ya existe un admin
    admin_existente = db.query(Usuario).filter(Usuario.rol == Rol.ADMIN).first()
    if admin_existente:
        print("Ya existe un usuario administrador.")
        db.close()
        return

    # Crear admin por defecto
    admin = Usuario(
        nombre="Admin",
        apellido="Principal",
        email="admin@barberia.com",
        usuario="admin",
        hashed_password=pwd_context.hash("admin123"),
        rol=Rol.ADMIN,
        porcentaje_ganancia=0,
        activo=True,
    )
    db.add(admin)
    db.commit()
    db.close()
    print("Usuario administrador creado exitosamente!")
    print("Usuario: admin")
    print("Contraseña: admin123")
    print("¡Cambia la contraseña después del primer inicio de sesión!")


if __name__ == "__main__":
    crear_admin()
