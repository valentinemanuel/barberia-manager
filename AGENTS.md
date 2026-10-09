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
1. Toda rama de trabajo sale de `dev`: `feat/nombre`, `fix/nombre`, `docs/nombre`, `style/nombre`, `refactor/nombre`, `chore/nombre`, `test/nombre`
2. Commits en ingles con prefijos: `feat:`, `fix:`, `refactor:`, `docs:`
3. PR de la rama hacia `dev` con descripción clara y tests
4. `dev` se mergea a `main` periódicamente (release), PR de `dev` → `main`
5. No hacer push directo a `main` ni a `dev`

## Reglas Importantes
- **NO romper la API**: Mantener compatibilidad hacia atrás
- **Porcentaje barbero**: Se aplica SOLO al servicio, nunca a productos/consumibles
- **Privacidad**: Barberos NUNCA ven totales brutos ni datos de otros
- **Offline-first**: La PWA debe funcionar sin internet
- **Sincronización**: Bidireccional con manejo de conflictos (last-write-wins con timestamp)
- **Monedas**: Siempre Decimal, nunca float
- **Fechas**: UTC en backend, local en frontend

## MCP Servers
- Plantilla sin credenciales: `opencode.json.example`. Preparación y validación en `docs/mcp.md`.
- **context7**: documentación actualizada de librerías.
- **playwright**: pruebas de navegador/E2E de la PWA.
- **sqlite**: acceso a `backend/barberia.db`; requiere `uvx`. Configuración verificada (2026-10-09): `mcp-server-sqlite` con `--with mcp==1.9.4 --with pydantic==2.11.7`. Sin esos pines falla al iniciar (pydantic ≥2.12 quitó `eval_type_backport`; mcp ≥1.16 quitó `Server.list_resources`). En este entorno `uvx` no está en el PATH: usar la ruta absoluta del `Scripts` del Python de Microsoft Store. No modificar datos reales sin autorización.
- **github**: usa `GITHUB_PERSONAL_ACCESS_TOKEN` del entorno, nunca un token literal en archivos versionados.
- No usar `chrome-devtools-mcp`: inestable con Edge; usar Playwright MCP.

## Mantenimiento de Documentos
- Tras cambios significativos, actualizar `MEMORY.md` con decisiones, estado y pendientes comprobados. Actualizar `AGENTS.md` cuando cambien las convenciones o herramientas.
- `opencode.json` es configuración local ignorada por Git y nunca se commitea. Si cambia la configuración de MCP, actualizar la plantilla sin copiar credenciales ni datos personales.
