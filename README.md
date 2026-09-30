# Sistema de Gestión para Barbería

Sistema completo de gestión para barberías con PWA instalable, funcionamiento offline y sincronización automática.

## Características

- **Gestión de barberos**: Registro de cortes, porcentajes de ganancia, historial
- **Catálogo de servicios**: Cortes, barbas, tintes con precios configurables
- **Productos y consumibles**: Control de stock, ventas rápidas
- **Cierre de caja**: Resumen diario, diferencias, retiros
- **Reportes**: Ganancias por período, cortes por barbero, productos más vendidos
- **PWA**: Instalable en celular, funciona offline, sincronización automática

## Capturas de Pantalla

![Dashboard Admin](docs/screenshots/dashboard-admin.png)
![Registro de Cortes](docs/screenshots/registro-cortes.png)
![Dashboard Barbero](docs/screenshots/dashboard-barbero.png)
![Reportes](docs/screenshots/reportes.png)

## Requisitos Previos

- Python 3.11+
- Node.js 18+
- npm o pnpm

## Instalación

### 1. Clonar el repositorio
```bash
git clone <repo-url>
cd barberia
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend
```bash
cd frontend
npm install
```

## Configuración Inicial

### Crear usuario administrador
```bash
cd backend
python -m app.scripts.create_admin
```

### Variables de entorno (backend/.env)
```env
DATABASE_URL=sqlite:///./barberia.db
SECRET_KEY=tu-clave-secreta-muy-segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

## Uso del Sistema

### Desarrollo
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Producción
```bash
# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build
npm run preview
```

## Roles y Permisos

### Administrador
- Ver ganancias (diarias, semanales, mensuales)
- Gestionar barberos y porcentajes
- Configurar servicios y precios
- Gestionar productos y stock
- Registrar gastos
- Realizar cierre de caja
- Ver reportes y exportar datos

### Barbero
- Registrar sus propios cortes
- Ver su plata acumulada (su parte correspondiente)
- Ver su porcentaje asignado
- NO ve información de otros barberos
- NO ve ganancias globales

## Scripts Disponibles

### Backend
| Script | Descripción |
|--------|-------------|
| `uvicorn app.main:app --reload` | Servidor desarrollo |
| `pytest tests/ -v` | Ejecutar tests |
| `python -m app.scripts.create_admin` | Crear admin inicial |

### Frontend
| Script | Descripción |
|--------|-------------|
| `npm run dev` | Servidor desarrollo |
| `npm run build` | Build producción |
| `npm run preview` | Preview producción |

## API Documentation

Una vez ejecutando el backend, visita:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.
