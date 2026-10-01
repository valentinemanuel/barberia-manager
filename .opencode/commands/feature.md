---
description: Implementar feature fullstack barbería (FastAPI + React PWA offline-first)
agent: build
---

Implementa la feature: $ARGUMENTS

Contexto del proyecto (ver AGENTS.md y MEMORY.md):
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, JWT. Estructura en `backend/app/`: `models/` → `schemas/` → `services/` → `routers/`.
- Frontend: React 18 + Vite + TypeScript estricto + Zustand + Dexie (IndexedDB) + PWA offline-first. Estructura en `frontend/src/`: `pages/`, `components/`, `store/`, `services/`, `pwa/`.

Estado actual del repo:

!`git status --short && git diff --stat`

Reglas obligatorias:
1. Español en código y comentarios. Python: `snake_case` + type hints siempre. TypeScript: `camelCase`, `PascalCase` para componentes, evitar `any`.
2. Monedas: `Decimal` en backend NUNCA `float`. En frontend: cents (enteros).
3. Fechas: UTC en backend, hora local en frontend.
4. Porcentaje barbero SOLO al servicio, nunca a productos/consumibles.
5. Privacidad: barberos NUNCA ven totales brutos ni datos de otros barberos.
6. NO romper la API: compatibilidad hacia atrás.
7. Offline-first: toda feature de frontend debe funcionar sin internet y sincronizar bidireccional (last-write-wins con timestamp).
8. Validación con Pydantic schemas para todas las entradas/salidas.

Flujo de trabajo:
1. Inspecciona archivos relevantes en `backend/app/` y `frontend/src/` antes de codificar.
2. Backend primero (modelo → schema → servicio → router), verifica en Swagger `http://localhost:8000/docs`.
3. Frontend después (page → componentes → store → sync offline).
4. Verifica con ejecución: `pytest tests/ -v` si tocaste backend, `npm run build` si tocaste frontend.
5. Resume: archivos creados/modificados con formato `ruta:línea`, cómo probar manual, y qué regla de negocio aplicaste.
