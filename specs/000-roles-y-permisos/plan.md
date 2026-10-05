# Plan 000 — Roles y permisos

Estado: propuesto

## Objetivo
Formalizar la matriz rol × permiso (RF-1..RF-18) sin romper la API, centralizando la autorización con el rol vigente en DB, protegiendo el invariante del último admin con escritura atómica y añadiendo auditoría de cambios sensibles.

## Archivos a crear o modificar

### Backend

| Archivo | Responsabilidad |
|---|---|
| `backend/app/models/auditoria.py` (crear) | Modelo `Auditoria`: `id`, `actor_id` (FK usuarios), `accion` (enum `crear_usuario, cambiar_rol, cambiar_porcentaje, cambiar_activo`), `usuario_afectado_id`, `valor_anterior` (JSON nullable), `valor_nuevo` (JSON), `timestamp` (UTC, default `datetime.utcnow`). |
| `backend/app/models/__init__.py` (modificar) | Exportar `Auditoria` y su enum. |
| `backend/app/schemas/auditoria.py` (crear) | `AuditoriaResponse` (Pydantic, `from_attributes`), `AuditoriaListResponse` con paginación (`items`, `total`, `skip`, `limit`). |
| `backend/app/schemas/usuario.py` (modificar) | Añadir campos opcionales necesarios (sin tocar `UsuarioCrear/Actualizar` salvo `activo` ya existe). Mantener compatibilidad. |
| `backend/app/services/auditoria_service.py` (crear) | Función `registrar_auditoria(db, actor_id, accion, usuario_afectado_id, valor_anterior, valor_nuevo)`; serializa valores a JSON. |
| `backend/app/services/admin_service.py` (crear) | Lógica pura del invariante: conteo de admins activos, validación de operación (`validar_cambio_admin`), ejecución con bloqueo. |
| `backend/app/dependencies.py` (modificar) | `obtener_usuario_actual` ya consulta DB (RF-15 OK, claim informativo). Añadir `requerir_rol(*roles)` parametrizable si se necesita; mantener `requerir_admin` / `requerir_barbero`. |
| `backend/app/routers/usuarios.py` (modificar) | Integrar invariante del último admin (RF-4/4b/5/6/4c) vía `admin_service`, auditoría (RF-13) en crear/actualizar/cambiar rol-porcentaje-activo, y 403 manejado por dependencias (RF-3). |
| `backend/app/routers/auditoria.py` (crear) | `GET /api/auditoria?skip&limit` restringido a admin (RF-14). |
| `backend/app/main.py` (modificar) | Registrar router de auditoría. |
| `backend/app/routers/cortes.py` (modificar) | RF-9: cambiar 403 por 404 cuando un barbero accede a corte ajeno; admins también barbero ven solo lo propio en vistas `/mi/*` (RF-12 — ya cumple). RF-14b: asegurar resúmenes `/mi/*` ya scoped (OK). |
| `backend/app/routers/reportes.py` (modificar) | RF-14b: endpoints admin intactos; si se expone agregado a barbero, filtrar por `barbero_id = usuario_actual.id` y excluir otros (hoy todos requieren admin, verificar diseño: mantener exclusividad admin y mover agregados del barbero a `/cortes/mi/resumen/*`). |
| `backend/app/routers/servicios.py`, `productos.py`, `consumibles.py`, `gastos.py`, `cierre_caja.py`, `ventas.py` (modificar) | RF-7/RF-15: verificar lectura de catálogo expone solo `precio_venta` a cualquier usuario autenticado (barbero incluido); CRUD/admin solo con `requerir_admin`; consumibles: no exponer costos ni márgenes en serializadores públicos al barbero. |
| `backend/app/services/sync_service.py` o donde viva sync (crear/modificar según exista) | RF-18: validar operaciones encoladas contra rol/activo actuales al sincronizar; rechazar 409 con lista de rechazadas. |
| `backend/tests/test_roles_permisos.py` (crear) | Tests matriz RF-1..RF-16. |
| `backend/tests/test_auditoria.py` (crear) | Tests RF-13/RF-14. |
| `backend/tests/test_invariante_admin.py` (crear) | Tests RF-4/4b/4c/5/6 incl. concurrencia. |

### Frontend

| Archivo | Responsabilidad |
|---|---|
| `frontend/src/services/api.ts` (verificar/modificar) | Añadir manejo de 409 en sync (RF-18) notificando al usuario; no romper llamadas existentes. |
| `frontend/src/store/authStore.ts` (modificar) | Persistir último `rol` y `activo` conocido ya incluido en `usuario` (RF-17) — documentar que se usa `usuario.rol` para permisos offline; exponer `actualizarPerfil()` para refrescar rol desde `/usuarios/me/perfil` al recuperar conexión (RF-18). |
| `frontend/src/services/sync.ts` (crear/modificar) | Al aplicar cola offline: si responde 409 con error de rol/desactivación, marcar operaciones rechazadas y notificar (RF-18); forzar logout/bloqueo si usuario desactivado (RF-16). |
| `frontend/src/App.tsx` (modificar) | Router guards ya usan `usuario.rol` del store (RF-17); asegurar que al refrescar perfil y cambiar rol se redirigja según nuevo rol (RF-16). |
| `frontend/src/pages/Auditoria.tsx` (crear, opcional simple) | Listado simple de auditoría solo admin (RF-14, fuera de alcance filtros). |

## Funciones puras

| Función | Firma | Descripción |
|---|---|---|
| `es_ultimo_admin` | `... -> bool` | `True` si `count(admins activos) == 1`. Parámetros: `admins_activos: int`. No toca DB (recibe conteo). |
| `puede_cambiar_a` | `... -> bool` | Decide si un usuario `afectado` (rol, activo) puede pasar a `nuevo_rol`, `nuevo_activo` sin violar el invariante: simular el cambio y verificar que quede ≥1 admin activo. |
| `es_permitido` | `... -> bool` | Matriz rol × acción pura: `(rol, accion) -> bool`. Centraliza RF-matriz. |
| `serializar_valor` | `... -> Optional[dict]` | Convierte valor de campo a dict JSON-serializable para auditoría (`None` en `crear_usuario` para anterior). |
| `acumulado_barbero` | `... -> Decimal` | `sum(Decimal(monto) * Decimal(pct) / 100)` sobre cortes del barbero con distinción cobrado/pendiente. Todas las cantidades `Decimal`. |
| `operacion_permitida_sync` | `... -> bool` | `(rol_nuevo, operacion) -> bool` para decidir aceptación al sincronizar (RF-18). |

Pseudocódigo de `puede_cambiar_a`:

```
funcion puede_cambiar_a(afectado, nuevo_rol, nuevo_activo, total_admins_activos):
    sera_admin_activo = (nuevo_rol == ADMIN y nuevo_activo == True)
    era_admin_activo = (afectado.rol == ADMIN y afectado.activo == True)
    si era_admin_activo y no sera_admin_activo:
        si total_admins_activos == 1:
            retornar False   # último admin: 409
    retornar True
```

Pseudocódigo de `validar_y_escritura` (RF-4c):

```
transaccion:
    bloquear fila/tabla usuarios (SELECT ... FOR UPDATE) o usar transacción serializable
    total = contar admins activos
    si no puede_cambiar_a(...): abortar con 409
    aplicar cambio
    registrar_auditoria(...)
    commit
# Ante concurrencia: una de las transacciones espera y al recontar ve 1 admin -> 409
```

Pseudocódigo auditoría en `actualizar_usuario`:

```
por cada campo sensible (rol, porcentaje_ganancia, activo):
    si cambio:
        registrar_auditoria(actor_id=admin.id, accion=..., usuario_afectado_id=...,
                            valor_anterior=valor_json(ant), valor_nuevo=valor_json(nuevo))
```

## Interfaz (endpoints nuevos/alterados)

- `GET /api/auditoria?skip=0&limit=50` → `200 AuditoriaListResponse` (admin). 403 para barbero.
- `PUT /api/usuarios/{id}`: conserva contrato; ahora puede responder `409` cuando el cambio viola el invariante; registra auditoría; sigue 403 para barbero (RF-3).
- `GET /api/cortes/{id}`: barbero ajeno → 404 (antes 403).
- `GET /api/cortes/mi/resumen/*`: ya scoped; se añade distinción cobrado/pendiente y porcentaje por corte (RF-8).
- Sin nuevos endpoints de reportes para barbero (RF-14b): los agregados propios ya están en `/cortes/mi/*`; los globales solo admin.

## Decisiones justificadas

1. **Autorización siempre con rol de DB (RF-15/RF-16)** — Descartado confiar en el claim del token (inseguro ante degradación/desactivación). El claim queda informativo para UX.
2. **404 en RF-9** — Alinear con aclaración de clarificación y constitución (no revelar existencia). Descartado 403 por fuga de información.
3. **409 para último admin** — Consistente semánticamente con conflicto de estado; descartado 400 (no valida invariante de negocio global).
4. **Bloqueo por transacción + recuento (RF-4c)** — Descartado validación fuera de transacción (race) y solo lock de aplicación en memoria (no multi-worker). En SQLite dev se usa transacción con `BEGIN IMMEDIATE` vía `db.execute(text("BEGIN IMMEDIATE"))` o lock de fila donde soporte; documentado.
5. **Auditoría en tabla propia** — Descartado log en archivo (no consultable por API, RF-14).
6. **Acumulado = SUM(precio * porcentaje_barbero / 100)** (RF-8). El modelo `Corte` ya guarda `parte_barbero`; se añade test que verifica equivalencia con la fórmula del RF; si difieren se ajusta `corte_service` a recomputar con `Decimal`. (Nota: spec dice `monto_servicio`; el campo real es `precio` — se asume equivalencia.)
7. **Matriz rol×acción en función pura (`es_permitido`)** — Descartado middleware global (oculta rules, difícil testear); se usa como base para guards por endpoint y sync.
8. **Frontend offline: último rol cacheado (RF-17) + revalidación al sync (RF-18)** — Descartado bloquear offline hasta revalidar (rompe offline-first).

## Estrategia de tests

- **Unitarias de funciones puras**: `es_ultimo_admin`, `puede_cambiar_a`, `es_permitido`, `serializar_valor`, `acumulado_barbero`, `operacion_permitida_sync`. Cubre RF-4, RF-18, RF-matriz, RF-8.
- **API con TestClient + DB temporal**:
  - RF-1/2/3: crear usuario como admin OK; barbero crea/modifica/desactiva → 403.
  - RF-4/4b/5/6: último admin auto-degradación/desactivación → 409; otro admin activo presente → permitido; promover → permitido; degradar a otro con otro admin restante → permitido.
  - RF-4c: dos peticiones concurrentes degradando el único admin → una 200/permitida según invariante y otra 409; al final ≥1 admin activo.
  - RF-9: barbero lee `/cortes/{id}` ajeno → 404.
  - RF-12: admin en vistas `/mi/*` ve solo lo propio.
  - RF-13: crear/cambiar rol/porcentaje/activo genera fila de auditoría con campos correctos y `valor_anterior=null` en crear.
  - RF-14: admin lista auditoría ordenada desc con paginación; barbero → 403.
  - RF-15/16: usuario degradado en DB con token `rol=admin` → futuro request usa rol DB (403 en admin).
  - RF-7: catálogo público no expone costos de consumibles ni márgenes; excluye campos sensibles.
  - RF-14b: agregados de reportes admin no accesibles a barbero (403) y resúmenes propios no mezclan datos ajenos.
- **Frontend (Vitest/manual + Playwright)**:
  - RF-17: sin red, App usa `usuario.rol` cacheado del store para mostrar rutas.
  - RF-18: al sincronizar con rol cambiado en servidor, cola con operaciones no permitidas → 409, notificación y bloqueo si desactivado.
  - RF-16: cambio de rol en servidor y refresco de perfil → re-routing según nuevo rol.

## Mapeo RF → archivos

- RF-1/2/3, RF-4/4b/5/6/4c, RF-13: `usuarios.py` + `admin_service.py` + `auditoria_service.py` + modelo auditoría + tests.
- RF-7: serializadores de `servicios/productos/consumibles` + tests.
- RF-8, RF-11, RF-12, RF-9, RF-14b: `cortes.py`/`reportes.py` + tests.
- RF-15/16: `dependencies.py` + tests con token degradado.
- RF-14: `auditoria.py` router + tests.
- RF-17/18: `authStore.ts` + `sync` frontend + tests Playwright.

## Fuera de este plan
- Nuevos roles, refresh tokens, UI avanzada de auditoría (filtros/exportación).
