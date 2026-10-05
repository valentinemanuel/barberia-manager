from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import requerir_admin, obtener_usuario_actual
from app.models.usuario import Usuario, Rol
from app.models.auditoria import AccionAuditoria
from app.schemas.usuario import UsuarioCrear, UsuarioActualizar, UsuarioResponse
from app.services import admin_service, auditoria_service

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

    # RF-13: registrar auditoría de creación
    auditoria_service.registrar_auditoria(
        db,
        actor_id=admin.id,
        accion=AccionAuditoria.CREAR_USUARIO,
        usuario_afectado_id=nuevo.id,
        valor_anterior=None,
        valor_nuevo={
            "nombre": nuevo.nombre,
            "apellido": nuevo.apellido,
            "email": nuevo.email,
            "usuario": nuevo.usuario,
            "rol": nuevo.rol.value,
            "porcentaje_ganancia": float(nuevo.porcentaje_ganancia),
        },
    )
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

    # Capturar valores anteriores para auditoría
    rol_anterior = usuario.rol
    porcentaje_anterior = usuario.porcentaje_ganancia
    activo_anterior = usuario.activo

    # RF-4/4b/4c/5/6: validar invariante del último admin ANTES de aplicar
    cambios_rol_activo: dict = {}
    accion_admin = None

    if datos.rol is not None and datos.rol != usuario.rol:
        cambios_rol_activo["rol"] = datos.rol
        if datos.rol == Rol.ADMIN:
            accion_admin = admin_service.ACCION_PROMOVER
        elif usuario.rol == Rol.ADMIN:
            accion_admin = admin_service.ACCION_DEGRADAR

    if datos.activo is not None and datos.activo != usuario.activo:
        cambios_rol_activo["activo"] = datos.activo
        if datos.activo is False:
            # Desactivar es la acción más restrictiva en el invariante
            accion_admin = admin_service.ACCION_DESACTIVAR

    if accion_admin is not None or cambios_rol_activo:
        if accion_admin is None:
            # Reactivación u otro cambio que no remueve admin activo
            for campo, valor in cambios_rol_activo.items():
                setattr(usuario, campo, valor)
            db.commit()
        else:
            error = admin_service.validar_y_aplicar_cambio_admin(
                db, usuario, accion_admin, actor=admin, cambios=cambios_rol_activo
            )
            if error is not None:
                # 409: no aplicar cambio ni registrar auditoría
                raise HTTPException(
                    status_code=error["status_code"], detail=error["detail"]
                )
        db.refresh(usuario)

    cambio_porcentaje = False
    if datos.porcentaje_ganancia is not None and datos.porcentaje_ganancia != porcentaje_anterior:
        usuario.porcentaje_ganancia = datos.porcentaje_ganancia
        cambio_porcentaje = True

    db.commit()
    db.refresh(usuario)

    # RF-13: registrar auditoría solo de los cambios efectivamente aplicados
    if datos.rol is not None and datos.rol != rol_anterior:
        auditoria_service.registrar_auditoria(
            db,
            actor_id=admin.id,
            accion=AccionAuditoria.CAMBIAR_ROL,
            usuario_afectado_id=usuario.id,
            valor_anterior={"rol": rol_anterior.value},
            valor_nuevo={"rol": datos.rol.value},
        )
    if cambio_porcentaje:
        auditoria_service.registrar_auditoria(
            db,
            actor_id=admin.id,
            accion=AccionAuditoria.CAMBIAR_PORCENTAJE,
            usuario_afectado_id=usuario.id,
            valor_anterior={"porcentaje_ganancia": float(porcentaje_anterior)},
            valor_nuevo={"porcentaje_ganancia": float(datos.porcentaje_ganancia)},
        )
    if datos.activo is not None and datos.activo != activo_anterior:
        auditoria_service.registrar_auditoria(
            db,
            actor_id=admin.id,
            accion=AccionAuditoria.CAMBIAR_ACTIVO,
            usuario_afectado_id=usuario.id,
            valor_anterior={"activo": activo_anterior},
            valor_nuevo={"activo": datos.activo},
        )
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
