---
description: Ejecutar y generar tests barbería (pytest backend + checks frontend)
agent: build
---

Ejecuta / genera tests para: $ARGUMENTS

Contexto:
- Backend tests: `backend/tests/` con pytest. Comando: `pytest tests/ -v --cov=app` desde `backend/`.
- Frontend: sin suite aún, validar con `npm run build` y prueba manual del flujo offline.
- Reglas de negocio críticas a cubrir: `Decimal` (no `float`), fechas UTC, % solo a servicios, roles admin/barbero, privacidad de totales.

Estado del repo:

!`git status --short`

Flujo de trabajo:
1. Inspecciona `backend/tests/`, `backend/app/` y `frontend/src/` relacionados con $ARGUMENTS antes de actuar.
2. Si piden generar tests: crea test en `backend/tests/test_<modulo>.py`, con nombres en español, casos éxito + error + permisos (admin vs barbero).
3. Si piden ejecutar: corre `pytest tests/ -v` (backend) y/o `npm run build` (frontend) y muestra salida real, no inventada.
4. Si hay fallo: lista hipótesis investigadas, evidencia encontrada (`ruta:línea`), y declara el issue load-bearing claramente.
5. No des por válido nada sin ejecución. Evidencia antes de síntesis.
