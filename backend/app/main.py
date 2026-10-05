from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app import models  # noqa: F401  # asegura que todos los modelos (incl. Auditoria) estén registrados
from app.routers import (
    auth,
    usuarios,
    servicios,
    cortes,
    productos,
    consumibles,
    gastos,
    cierre_caja,
    ventas,
    reportes,
    auditoria,
    sync,
)

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Gestión para Barbería",
    description="API REST para gestión de barbería con roles de admin y barbero",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(servicios.router)
app.include_router(cortes.router)
app.include_router(productos.router)
app.include_router(consumibles.router)
app.include_router(gastos.router)
app.include_router(cierre_caja.router)
app.include_router(ventas.router)
app.include_router(reportes.router)
app.include_router(auditoria.router)
app.include_router(sync.router)


@app.get("/")
def raiz():
    return {"mensaje": "Sistema de Gestión para Barbería", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
