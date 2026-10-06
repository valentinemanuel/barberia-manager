# Project Constitution — Barbershop Manager

Este documento define los principios no negociables del proyecto. Toda spec, plan, tarea e implementación debe cumplirlo. Si una spec lo contradice, la spec se corrige.

## 1. Producto
- Sistema de gestión para barbería: cortes, barberos, productos, consumibles, gastos, cierre de caja y reportes.
- La PWA debe funcionar **offline-first**: toda funcionalidad crítica opera sin internet y sincroniza al recuperar conexión.

## 2. Stack
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, JWT (python-jose).
- Frontend: React 18, Vite, TypeScript, PWA (vite-plugin-pwa), Dexie (IndexedDB), Zustand.
- DB: SQLite en desarrollo, PostgreSQL en producción.

## 3. Reglas de Negocio (no negociables)
- El porcentaje del barbero se aplica **SOLO al servicio**, nunca a productos ni consumibles.
- Los barberos **NUNCA** ven totales brutos ni datos de otros barberos.
- El dinero se maneja con `Decimal` en backend y centavos (enteros) en frontend. **Nunca `float`.**
- Fechas en UTC en backend, hora local en frontend.
- Sincronización bidireccional con conflictos resueltos **last-write-wins con timestamp**.

## 4. Calidad
- Toda entrada/salida de API validada con schemas Pydantic.
- TypeScript estricto en frontend; evitar `any`.
- Tests con pytest para backend; progreso verificable por tarea.
- No romper la API: mantener compatibilidad hacia atrás.

## 5. Convenciones
- Código y comentarios en español (backend y frontend).
- Backend: snake_case variables/funciones, PascalCase clases, type hints siempre.
- Frontend: camelCase variables/funciones, PascalCase componentes.
- Commits en inglés con prefijos: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
- Toda rama de trabajo parte de `dev` actualizado: `feat/nombre`, `fix/nombre`, `docs/nombre`, `style/nombre`, `refactor/nombre`, `chore/nombre`, `test/nombre`.
- Los cambios se integran mediante PR de la rama de trabajo hacia `dev`, con descripción clara y evidencia de validación. No hacer push directo a `dev` ni a `main`.
- Las releases se realizan mediante PR de `dev` hacia `main`. El propietario del proyecto es quien decide y ejecuta esa integración; el agente no realiza merges hacia `main`.

## 6. Herramientas
- MCP activos: context7 (docs), playwright (E2E), sqlite, github.
- No usar `chrome-devtools-mcp` (inestable con Edge).
- `opencode.json` está en `.gitignore`: nunca commitear tokens.

## 7. Spec-Driven Development
- Toda feature nueva sigue el flujo: 5 preguntas de casos límite → spec.md → clarificación → plan.md → tasks.md → implementación → validación.
- `tasks.md`: tareas de 20–30 min, ordenadas por dependencia, con RFs cubiertos y línea "Hecho cuando:" verificable.
