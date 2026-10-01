---
description: Diagnosticar y corregir bug preservando API y reglas de negocio
agent: build
---

Corrige el bug: $ARGUMENTS

Contexto:
- Backend: FastAPI en `backend/app/` (`routers/`, `services/`, `models/`, `schemas/`). Auth JWT con roles admin/barbero.
- Frontend: React PWA en `frontend/src/` con sync offline Dexie.
- Consulta AGENTS.md y MEMORY.md para reglas de negocio.

Estado del repo:

!`git status --short && git log --oneline -5`

Flujo de trabajo:
1. Reproduce primero: identifica pasos, endpoint o página afectada, y log/error real.
2. Inspecciona TODAS las áreas candidatas mencionadas en $ARGUMENTS (routers, servicios, store, sync) antes de concluir. Usa `read`/`grep`, no adivines.
3. Diagnóstico: declara hipótesis y resultado de cada una. Si contradice una suposición previa, dilo explícitamente.
4. Fix mínimo: no refactors grandes, no romper API, respetar `Decimal`, UTC, % solo servicios, privacidad barbero.
5. Verifica: `pytest tests/ -v` si es backend, `npm run build` si es frontend. Haz sanity check de ejecución.
6. Resume: causa raíz (`ruta:línea`), cambio aplicado, cómo verificar, y riesgo de regresión.
