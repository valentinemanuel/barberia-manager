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
- **Fechas**: UTC en backend, local en frontend

## Estado Actual
- [x] Estructura del proyecto
- [x] Documentación base
- [ ] Modelos de base de datos
- [ ] Autenticación JWT
- [ ] CRUD usuarios y servicios
- [ ] Registro de cortes
- [ ] Productos y consumibles
- [ ] Gastos y cierre de caja
- [ ] Reportes y dashboard
- [ ] Frontend completo
- [ ] PWA offline
- [ ] Sincronización
- [ ] Tests

## Pendientes Importantes
1. Implementar modelos SQLAlchemy
2. Sistema de autenticación JWT
3. Lógica de porcentajes (solo servicios)
4. Service worker para offline
5. Estrategia de sincronización con conflictos
6. Tests de integración

## Notas Críticas
- Porcentaje barbero SOLO a servicios, nunca productos/consumibles
- Barberos NUNCA ven totales brutos ni datos de otros
- Sincronización: last-write-wins con timestamp
- SQLite en desarrollo, PostgreSQL en producción
