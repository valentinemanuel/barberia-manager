# Spec 000 — Roles y permisos

Estado: aprobada

## Contexto y objetivo
Formalizar la matriz rol × permiso del sistema. Hoy el rol (`admin` / `barbero`) existe en el modelo y hay guards básicos en `dependencies.py`, pero las reglas son implícitas y hay huecos (auto-desactivación del admin, permisos del barbero no documentados, sin auditoría). Esta spec define QUÉ puede hacer cada rol y protege invariantes del sistema.

## Usuarios
- Admin
- Barbero

## Historias de usuario
- HU-1. Como admin, quiero gestionar usuarios (crearlos, activarlos, asignarles rol y porcentaje) para controlar quién accede.
- HU-2. Como admin, quiero no poder dejar el sistema sin ningún administrador activo.
- HU-3. Como barbero, quiero ver el catálogo con precios de lo que se vende, mi porcentaje asignado y mi acumulado, sin ver datos de otros.
- HU-4. Como admin que también corta, quiero poder registrar mis propios cortes.
- HU-5. Como dueño, quiero un registro de quién cambió roles o porcentajes.

## Definiciones
- **Admin activo**: usuario con `rol = admin` y `activo = true`.
- **Último admin**: cuando existe exactamente un admin activo en el sistema.

## Requisitos funcionales

### Gestión de usuarios
- RF-1: EL SISTEMA permitirá crear usuarios solo a un admin autenticado.
- RF-2: SI un admin intenta crear un usuario, ENTONCES EL SISTEMA le asignará el rol elegido (`admin` o `barbero`).
- RF-3: SI un barbero intenta crear, modificar o desactivar usuarios, ENTONCES EL SISTEMA responderá 403.

### Invariante del administrador
- RF-4: SI un admin intenta desactivarse a sí mismo o quitarse el rol `admin` siendo el último admin activo, ENTONCES EL SISTEMA responderá 409 y no aplicará el cambio.
- RF-4b: EL SISTEMA permitirá que un admin se desactive a sí mismo (o se degrade a barbero) cuando exista al menos otro admin activo.
- RF-5: SI un admin intenta desactivar o degradar a otro admin pero quedaría al menos un admin activo, ENTONCES EL SISTEMA permitirá el cambio.
- RF-6: EL SISTEMA permitirá que un admin promueva a otro usuario al rol `admin`.
- RF-4c: La validación del invariante del último admin y su escritura serán ATÓMICAS (transacción con bloqueo); ante peticiones concurrentes, una de ellas responderá 409.

### Barbero
- RF-7: EL SISTEMA permitirá al barbero ver el catálogo de servicios, productos y consumibles con sus precios de venta (`precio_venta`). Costos de consumibles y márgenes NUNCA se exponen al barbero.
- RF-8: EL SISTEMA mostrará al barbero, en sus resúmenes, solo su acumulado (definido como `SUM(corte.monto_servicio * corte.porcentaje_barbero / 100)` sobre sus cortes, con distinción cobrado/pendiente), el `porcentaje_barbero` registrado en cada corte suyo, su `porcentaje_ganancia` actual como valor por defecto, y cantidad de cortes.
- RF-9: SI un barbero intenta acceder a datos de otro barbero (cortes, acumulados, reportes), ENTONCES EL SISTEMA responderá 404.
- RF-10: EL SISTEMA NO expondrá al barbero totales brutos de ventas, ingresos globales ni datos de otros barberos.
- RF-11: EL SISTEMA permitirá al barbero registrar y consultar únicamente sus propios cortes.

### Admin también barbero
- RF-12: EL SISTEMA permitirá que un usuario con rol `admin` registre cortes y consulte sus propios totales COMO BARBERO; en vistas de barbero verá solo lo propio aun siendo admin. Los totales globales se exponen únicamente en vistas admin.

### Auditoría
- RF-13: SI se crea un usuario, se cambia su rol, su porcentaje o su estado `activo`, ENTONCES EL SISTEMA registrará en una tabla de auditoría: `actor_id`, `accion` (enum: `crear_usuario`, `cambiar_rol`, `cambiar_porcentaje`, `cambiar_activo`), `usuario_afectado_id`, `valor_anterior` y `valor_nuevo` (JSON serializado; `valor_anterior` es null en `crear_usuario`), y `timestamp` (UTC).
- RF-14: EL SISTEMA permitirá al admin consultar el historial de auditoría (ordenado por timestamp descendente, con paginación mínima).
- RF-14b: EL SISTEMA hará que los endpoints de reporte devuelvan al barbero solo agregados de sus propios cortes/ventas; los agregados de otros usuarios se excluyen.

### Operación offline
- RF-17: MIENTRAS el usuario opere offline, EL SISTEMA usará el último rol conocido (cache local) para permitir las acciones que ese rol tiene permitidas.
- RF-18: SI al sincronizar operaciones encoladas offline se detecta que el rol del usuario cambió o fue desactivado, ENTONCES EL SISTEMA validará cada operación contra el nuevo estado: las permitidas se aceptan y las no permitidas se rechazan (409) con notificación al usuario.

## Requisitos no funcionales
- RF-15: Todos los endpoints que hoy usan la dependencia `requerir_admin` (usuarios, reportes, gastos, cierre_caja, crear/actualizar/eliminar en servicios, productos, consumibles, ventas) seguirán requiriendo JWT válido; la autorización se evalúa con el rol actual en DB, no solo con el claim del token (el claim es informativo).
- RF-16: Los cambios de rol/activo en DB deben reflejarse de inmediato en futuras requests del usuario afectado.

## Matriz rol × acción

| Acción | Admin | Barbero |
|---|---|---|
| Ver catálogo con precios de venta | ✅ | ✅ |
| Registrar su corte | ✅ | ✅ |
| Ver sus cortes e historial | ✅ | ✅ |
| Ver todos los cortes | ✅ | ❌ |
| Ver totales globales / reportes | ✅ | ❌ |
| Ver agregados de sus cortes | ✅ | ✅ |
| Gestionar usuarios / roles | ✅ | ❌ |
| CRUD servicios/productos/consumibles | ✅ | ❌ (solo lectura) |
| Gastos y cierre de caja | ✅ | ❌ |
| Ver auditoría | ✅ | ❌ |

## Bootstrap
El primer administrador se crea con el script `python -m app.scripts.create_admin` (fuera de la API); no pasa por RF-1.

## Casos límite
- Intentar degradar/desactivar al último admin (409).
- Un admin se promueve a sí mismo como barbero teniendo otro admin activo: permitido.
- Un barbero intenta leer `/cortes/{id}` de otro barbero: 404.
- Token con claim `rol=admin` pero usuario ya degradado en DB: se usa el rol de DB.
- Usuario desactivado con token vigente: 401/403 inmediato.

## Fuera de alcance
- Nuevos roles (recepcionista, supervisor).
- Refresh tokens.
- UI de auditoría avanzada (filtros, exportación).

## Criterios de finalización
- Todas las RFs tienen tests que pasan.
- La matriz rol × permiso está documentada en `docs/constitution.md` o en esta spec.
- No hay endpoint administrativo accesible sin `requerir_admin`.
- Los tests de invariante del último admin pasan.

## Dudas abiertas
- Ninguna por ahora.

## Registro de clarificación (2026-10-04)
- Segunda pasada con sdd-clarifier: 14 hallazgos. Resueltos: política offline (RF-17/18), carrera del último admin (RF-4c), precio de catálogo limitado a venta (RF-7), acumulado definido (RF-8), matriz rol × acción añadida, contrato de auditoría (RF-13), paginación en auditoría (RF-14), reportes solo agregados propios del barbero (RF-14b), contexto de vistas para admin (RF-12), auto-desactivación no-última (RF-4b), bootstrap documentado, decisiones del registry integradas en los RF.
- **Ambigüedad RF-9**: "403 o 404" — se decide **404** para no revelar que el recurso existe (alineado con privacidad).
- **Ambigüedad RF-8**: el porcentaje existe en dos lugares (`usuario.porcentaje_ganancia` por defecto y `corte.porcentaje_barbero` snapshot por corte). Se aclara: el barbero ve el `porcentaje_barbero` registrado en cada uno de sus cortes, y su `porcentaje_ganancia` actual como valor por defecto.
- **Ambigüedad RF-15**: se aclara que el claim `rol` del JWT es informativo; la autorización siempre consulta el rol vigente en DB.
- **Contradicción revisada**: RF-4 y RF-5 no se contradicen — RF-4 protege al último admin, RF-5 permite cambios cuando queda al menos otro admin activo.
- **Conflicto con constitution**: ninguno; auditoría y privacidad refuerzan los principios existentes.
- **Caso límite nuevo cubierto**: bootstrap — el primer usuario se crea con el script `create_admin` (fuera de la API), por lo que RF-1 no bloquea el primer alta.
- **Alcance**: la UI de auditoría se limita a listado simple; filtros/exportación fuera de alcance.
