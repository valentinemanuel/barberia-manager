# Tareas 000 — Roles y permisos

Estado: pendiente

- [x] **T1. Crear modelo `Auditoria` y exportarlo.** RF-13
  - Hecho cuando: `backend/app/models/auditoria.py` existe con enum `accion`, y `python -c "from app.models import Auditoria"` no falla.

- [x] **T2. Migración/creacion de tabla auditoria.** RF-13
  - Hecho cuando: al arrancar la app, la tabla `auditorias` existe en `backend/barberia.db` con columnas id, actor_id, accion, usuario_afectado_id, valor_anterior, valor_nuevo, timestamp.

- [x] **T3. Schemas Pydantic de auditoría.** RF-14
  - Hecho cuando: `AuditoriaResponse` y `AuditoriaListResponse` serializan bien un registro de prueba.

- [x] **T4. Servicio `auditoria_service.registrar_auditoria`.** RF-13
  - Hecho cuando: test unitario inserta un registro y lo lee correctamente (JSON serializado, valor_anterior null en crear_usuario).

- [x] **T5. Servicio `admin_service` con `es_ultimo_admin` y `validar_cambio_admin`.** RF-4, RF-4b, RF-4c, RF-5, RF-6
  - Hecho cuando: tests unitarios cubren: último admin no puede ser degradado/desactivado (409), segundo admin sí puede ser degradado, admin puede promoverse/degradarse si hay otro admin.

- [x] **T6. Validación atómica del invariante (RF-4c).** RF-4c
  - Hecho cuando: test con dos peticiones concurrentes degradando los dos admins deja al menos uno activo y una responde 409.

- [x] **T7. Integrar invariante + auditoría en `routers/usuarios.py`.** RF-3, RF-4, RF-4b, RF-5, RF-6, RF-13
  - Hecho cuando: requests de prueba con admin degradando/desactivando admins producen 409/200 según caso, y cada cambio escribe un registro de auditoría.

- [x] **T8. Router `GET /api/auditoria` con paginación y solo admin.** RF-14
  - Hecho cuando: barbero recibe 403, admin recibe items ordenados por timestamp desc con skip/limit.

- [x] **T9. Cambiar 403 → 404 en acceso a corte ajeno (`cortes.py`).** RF-9, RF-12
  - Hecho cuando: test de barbero accediendo a `/cortes/{id}` ajeno devuelve 404; admin ve lo propio en `/mi/*`.

- [x] **T10. Serializadores de catálogo solo `precio_venta`.** RF-7, RF-10
  - Hecho cuando: respuesta de `/servicios`, `/productos`, `/consumibles` no incluye costos ni márgenes.

- [x] **T11. Agregados de reportes para barbero solo propios.** RF-14b, RF-10
  - Hecho cuando: endpoint de resumen de barbero devuelve solo cortes con `barbero_id = usuario_actual.id`.

- [x] **T12. Validación de rol al sincronizar offline (RF-17/18).** RF-17, RF-18
  - Hecho cuando: operación encolada de un usuario desactivado mientras estaba offline se rechaza con 409 y se notifica; operación permitida se acepta.

- [x] **T13. Tests de matriz de roles (RF-1..RF-16).** todos
  - Hecho cuando: `pytest backend/tests/test_roles_permisos.py` pasa.

- [x] **T14. Validación final con sdd-reviewer.** todos
  - Hecho cuando: reviewer reporta "lista" sin hallazgos altos.
