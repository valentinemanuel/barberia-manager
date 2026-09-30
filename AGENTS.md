# AGENTS.md - Sistema de Gestión para Barbería

## Descripción del Proyecto
Sistema completo de gestión para barbería con backend FastAPI y frontend React PWA. Permite registrar cortes, gestionar barberos, productos, consumibles, gastos y generar reportes. La PWA funciona offline con sincronización al servidor.

## Stack Tecnológico
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, JWT (python-jose)
- **Frontend**: React 18, Vite, TypeScript, PWA (vite-plugin-pwa), Dexie (IndexedDB), Zustand
- **Base de datos**: SQLite (desarrollo), PostgreSQL (producción futura)
- **Autenticación**: JWT con refresh tokens

## Estructura de Carpetas
```
barberia/
├── backend/
│   ├── app/
│   │   ├── main.py              # Punto de entrada FastAPI
│   │   ├── database.py          # Configuración SQLAlchemy
│   │   ├── config.py            # Variables de entorno
│   │   ├── models/              # Modelos SQLAlchemy
│   │   ├── schemas/             # Esquemas Pydantic
│   │   ├── routers/             # Endpoints de la API
│   │   ├── services/            # Lógica de negocio
│   │   └── dependencies.py      # Dependencias (auth, db)
│   ├── tests/                   # Tests con pytest
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Componentes reutilizables
│   │   ├── pages/               # Páginas de la app
│   │   ├── hooks/               # Custom hooks
│   │   ├── services/            # API client y sync
│   │   ├── store/               # Estado global (Zustand)
│   │   └── pwa/                 # Service worker y sync
│   ├── public/                  # Recursos estáticos
│   └── vite.config.ts
└── docs/                        # Documentación adicional
```

## Convenciones de Código

### Python (Backend)
- **Idioma**: Código y comentarios en español
- **Nombres**: snake_case para variables/functions, PascalCase para clases
- **Tipos**: Usar type hints siempre
- **Validación**: Pydantic schemas para todas las entradas/salidas
- **Monedas**: Usar `Decimal` NUNCA `float`
- **Fechas**: Guardar en UTC, mostrar en hora local

### TypeScript (Frontend)
- **Idioma**: Código y comentarios en español
- **Nombres**: camelCase para variables/functions, PascalCase para componentes
- **Tipos**: TypeScript estricto, evitar `any`
- **Estado**: Zustand para estado global, React Query para servidor

## Cómo Ejecutar en Desarrollo

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

## Flujo de Trabajo con Git
1. Crear rama desde `main`: `feat/nombre-funcionalidad`
2. Commits en español con prefijos: `feat:`, `fix:`, `refactor:`, `docs:`
3. PR con descripción clara y tests
4. No hacer push directo a `main`

## Reglas Importantes
- **NO romper la API**: Mantener compatibilidad hacia atrás
- **Porcentaje barbero**: Se aplica SOLO al servicio, nunca a productos/consumibles
- **Privacidad**: Barberos NUNCA ven totales brutos ni datos de otros
- **Offline-first**: La PWA debe funcionar sin internet
- **Sincronización**: Bidireccional con manejo de conflictos (last-write-wins con timestamp)
- **Monedas**: Siempre Decimal, nunca float
- **Fechas**: UTC en backend, local en frontend
