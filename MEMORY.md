# MEMORY.md - Memoria del Proyecto

## Resumen Ejecutivo
Sistema de gestión para barbería con backend FastAPI + frontend React PWA. Permite registrar cortes, gestionar barberos con porcentajes, productos, consumibles, gastos y reportes. Funciona offline con sincronización.
- **Repo**: `valentinemanuel/barbershop-manager` (renombrado de `barberia-manager`, oct 2026)

## Decisiones Arquitectónicas
- **Backend**: FastAPI + SQLAlchemy 2.0 + SQLite (migrable a PostgreSQL)
- **Frontend**: React 18 + Vite + TypeScript + PWA
- **Auth**: JWT con refresh tokens, roles admin/barbero
- **Offline**: IndexedDB (Dexie) con sync bidireccional
- **Monedas**: Decimal en backend, cents (enteros) en frontend
- **Fechas**: UTC en backend, local en frontend; strings solo-fecha (`YYYY-MM-DD`) se parsean como fecha LOCAL (nunca como UTC, retrocedería un día)
- **Diseño frontend (spec 001)**: sistema propio "Tinta & hueso" — tokens CSS + kit `components/ui`, sin frameworks CSS; Archivo Variable self-hosted, iconos `lucide-react`
- **Herramientas MCP**: plantilla sin credenciales en `opencode.json.example` y guía en `docs/mcp.md`; Playwright para navegador, Context7 para documentación, SQLite y GitHub opcionales. No confundir configuración con conexión verificada.

## Estado Actual
- [x] Estructura del proyecto
- [x] Documentación base
- [x] Modelos de base de datos
- [x] Autenticación JWT
- [x] CRUD usuarios y servicios
- [x] Registro de cortes
- [x] Productos y consumibles
- [x] Gastos y cierre de caja
- [x] Reportes y dashboard
- [x] Frontend completo (spec 001: sistema de diseño unificado, T1–T11 verificadas)
- [x] PWA offline
- [x] Sincronización (E2E offline verde: encolar → reconectar → sincronizar)
- [ ] Tests (backend con pytest; frontend solo tests visuales/E2E Playwright en `frontend/tests/visuales/`)

## Pendientes Importantes
1. Specs 000 y 001 ya integradas mediante PR #6 y #7, presentes en `dev` y `main` (comprobado el 2026-10-05). La corrección del login (PR #10) también está en `main`, integrada mediante la release del PR #11.
2. Duda abierta spec 001: locale del formato de moneda (`$1,234.56` en-US vs `$1.234,56` es-AR)
3. `lucide-react`/`@fontsource-variable/archivo` quedaron dentro del commit de spec 000 (11ba0c9); moverlos al commit de spec 001 si se reordena el historial
4. Tests de integración backend

## Notas Críticas
- Porcentaje barbero SOLO a servicios, nunca productos/consumibles
- Barberos NUNCA ven totales brutos ni datos de otros
- Sincronización: last-write-wins con timestamp
- SQLite en desarrollo, PostgreSQL en producción
- IndexedDB: los booleanos NO son claves válidas → `where('sincronizado').equals(0)` devuelve siempre `[]`; usar `.filter()` en memoria (fix en `useSync.ts`, verificado 0 vs 1)
- Git flow: ramas de trabajo desde `dev` → PR a `dev`; `dev` → `main` por release

## Recuperación documental (2026-10-05)
- Recuperado el contenido útil de `b211ee5` en una rama nueva desde `dev`, sin cherry-pick ni reescritura de la rama histórica `feat/mcp-config-y-offline`.
- Conservados el estado y los pendientes actuales; no se recupera la afirmación antigua de que todos los tests están completos.
- Plantilla MCP adaptada a la documentación de OpenCode V2 (`mcp.servers`, `disabled`, credenciales por entorno). La configuración local existente no se modifica. La conexión de los servidores de la plantilla queda por verificar en cada entorno.
