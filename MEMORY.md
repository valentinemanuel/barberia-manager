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
1. Spec 000 (roles y permisos) sin merge: rama `feat/spec-000-roles-permisos`; spec 001 va apilada encima (`feat/frontend-design-system`)
2. Duda abierta spec 001: locale del formato de moneda (`$1,234.56` en-US vs `$1.234,56` es-AR)
3. `lucide-react`/`@fontsource-variable/archivo` quedaron dentro del commit de spec 000 (11ba0c9); moverlos al commit de spec 001 si se reordena el historial
4. Tests de integración backend

## Notas Críticas
- Porcentaje barbero SOLO a servicios, nunca productos/consumibles
- Barberos NUNCA ven totales brutos ni datos de otros
- Sincronización: last-write-wins con timestamp
- SQLite en desarrollo, PostgreSQL en producción
- IndexedDB: los booleanos NO son claves válidas → `where('sincronizado').equals(0)` devuelve siempre `[]`; usar `.filter()` en memoria (fix en `useSync.ts`, verificado 0 vs 1)
