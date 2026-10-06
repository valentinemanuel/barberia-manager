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
1. Spec 002: módulo monetario implementado y revisado (167 tests verdes), aún no conectado a la API. Harness y continuación retirados por el usuario; spec completa pendiente.
2. Duda abierta spec 001: locale del formato de moneda (`$1,234.56` en-US vs `$1.234,56` es-AR)
3. `lucide-react`/`@fontsource-variable/archivo` quedaron dentro del commit de spec 000 (11ba0c9); moverlos al commit de spec 001 si se reordena el historial
4. Tests de integración backend

## Notas Críticas
- Porcentaje barbero SOLO a servicios, nunca productos/consumibles
- Barberos NUNCA ven totales brutos ni datos de otros
- Sincronización: last-write-wins con timestamp
- SQLite en desarrollo, PostgreSQL en producción
- IndexedDB: los booleanos NO son claves válidas → `where('sincronizado').equals(0)` devuelve siempre `[]`; usar `.filter()` en memoria (fix en `useSync.ts`, verificado 0 vs 1)
- Git flow: ramas de trabajo desde `dev` actualizado → PR a `dev`; releases mediante PR `dev` → `main`, decididas y ejecutadas por el propietario. Sin push directo a `dev` ni a `main`.

## Revisión de integraciones (2026-10-05)
- Specs 000 y 001 ya integradas: PR #6 y #7, respectivamente; ambas presentes en `origin/dev` y `origin/main`. La nota anterior de merges pendientes estaba desactualizada.
- PR #8 (flujo Git con `dev`) y #9 (`dev` → `main`) ya integrados. PR #10 (animación del login) también integrado en `main` mediante PR #11, comprobado al preparar la recuperación documental.
- Recuperación selectiva del commit documental histórico `b211ee5`: PR #12 (`docs/recover-mcp-documentation` → `dev`) preparado en worktree independiente. No se ha verificado aquí un merge posterior de ese PR. La rama histórica no se integró ni reescribió.

## Spec 002 — historial de borrador y clarificación (2026-10-05)
- Alcance confirmado: registro online/offline, fecha real, historial propio, edición/anulación, deuda del cliente y comisión del barbero con pagos parciales independientes.
- Valores actuales al aceptar un corte; servicios desactivados posteriormente no invalidan los cortes offline. Admin registra retroactivos para cualquier barbero sin valores históricos manuales.
- Primer cobro del cliente o pago de comisión, aunque parcial, o inclusión en cierre: bloquea edición/anulación del barbero. Correcciones administrativas con motivo y trazabilidad.
- Diez dudas abiertas documentadas para clarificación: redondeo; pagos offline y validaciones; reversos/cierres; estado inicial y movimientos; conflictos; recálculo al editar; entidades inactivas/eliminadas; fechas; datos históricos/historial offline; pagos posteriores al cierre.
- Primera revisión de `sdd-clarifier` realizada por solicitud del usuario: requiere iteración. Hallazgos registrados en la spec; respuestas de primera ronda incorporadas sin iniciar fases posteriores.
- Primera ronda confirmada: pesos argentinos (ARS), redondeo matemático al centavo; elegir cobro pendiente/parcial/completo al registrar; excesos offline pendientes de revisión administrativa; cierre original conservado con ajustes posteriores; edición offline recibida después del primer pago aceptado pendiente de intervención administrativa.
- RF-37 a RF-40 y RNF-1 actualizados; DA-1 a DA-5 acotadas a decisiones restantes. La spec continúa en borrador, sin plan, tareas ni implementación.
- Segunda ronda incorporada (RF-41 a RF-45): porcentajes 0–100 y abonos positivos con hasta dos decimales, rechazo de entradas inválidas/excesos online; recálculo con valores actuales al cambiar servicio, no al cambiar solo método; admin corrige fecha/barbero; históricos sin información sin pagos/deudas inventados; compensaciones con motivo y devoluciones explícitas; servicios separados de movimientos y ajustes en jornada abierta cuando la real ya cerró.
- DA-1 resuelta. Pendientes acotados incluyen resolución de revisiones/saldos, anulaciones/reasignaciones con dinero, datos de movimientos, conflictos y dependencias, entidades inactivas/inexistentes, fechas, cobertura offline y pertenencia a cierres.
- Segunda revisión de `sdd-clarifier`: requiere iteración. Cinco paquetes de políticas propuestos para aprobación, no adoptados: anulación/reasignación; jornadas/fechas; entidades inactivas/inexistentes; movimientos/conflictos; saldos/históricos/historial offline. Correcciones editoriales de RF-12/21/33/41 incorporadas sin introducir decisiones de negocio adicionales.
- Usuario acepta los cinco paquetes: incorporados RF-46 a RF-57 y reglas actualizadas; DA-1 a DA-10 cerradas con trazabilidad. Jornada `America/Argentina/Buenos_Aires`; fechas futuras administrativas rechazadas, retroactivos sin límite y reloj adelantado más de cinco minutos a revisión. Sin jornada abierta: movimiento aceptado pendiente de imputación conserva su saldo financiero.
- Anulación/reasignación conservan dinero como excedente cuando corresponda y no trasladan comisiones ya pagadas entre profesionales. Historial offline de 90 días propios más saldos abiertos y pendientes; importes en revisión/rechazados separados de saldos aceptados. Revisión final de clarificación pendiente, sin aprobación global ni fases posteriores.
- El alcance es transversal; el plan deberá evaluar si requiere división antes de producir más de diez tareas.

## Spec 002 — resultado vigente de clarificación (2026-10-05)
- Revisión final de `sdd-clarifier`, solicitada expresamente por el usuario: **LISTA PARA PLAN**. No se necesitan nuevas preguntas de negocio ni otra iteración; las notas de rondas previas son históricas, no bloqueantes vigentes.
- Ajustes editoriales incorporados en las definiciones de sincronización y jornada. No se añadió atomicidad todo-o-nada de corte+pago; se mantienen resultados individuales de RF-57.
- Dictamen registrado en la spec, que sigue en borrador hasta aprobación explícita. No se creó `plan.md` ni `tasks.md` ni se modificó código de aplicación. El cambio ajeno en `.opencode/agents/coordinator.md` se preservó sin modificarlo.

## Spec 002 — resultado vigente de planificación (2026-10-05)
- El usuario aprobó la spec completa y autorizó planificar. Spec marcada aprobada; `sdd-planner` creó `specs/002-registro-cortes/plan.md` como borrador de plan global.
- Plan de 670 líneas: exploración, inventario de archivos, modelos/journal por profesional, exactitud Decimal/centavos, migraciones conservadoras, idempotencia por operación, aislamiento por cuenta, interfaces, pseudocódigo, tests y rollback. Matriz documental verificada: 57 RF y 6 RNF presentes, sin whitespace sobrante; no se ejecutaron tests de aplicación ni migraciones.
- Propuesta de ocho macroentregas A–H, no aprobada todavía: fundaciones/migración; registro/historial; outbox/sync/cuentas; abonos/saldos; correcciones/anulación; reasignación/históricos; jornadas/cierres; integración UX/PWA/regresión. No equivalen a ocho tareas pequeñas.
- Estimación global inicial del planner: 140–214 horas efectivas, amplia y provisional, a recalibrar. La propuesta de 35–60 paquetes fue retirada tras auditoría; no se crearon subspecs ni tareas. Se propone únicamente un primer paquete de funciones monetarias puras y tests aislados, 2–4 horas y ≤10 tareas, pendiente de aprobación de división.
- Riesgos explicitados: pendientes/cierres legacy ambiguos, convivencia de clientes v1/v2, protección de claves de almacenamiento local y concurrencia SQLite. Validación de copias sanitizadas y entornos efímeros se autorizará aparte; no acceder a datos reales por aprobar este plan.
- Pendiente aprobación del plan y su estrategia de división. Sin código, commits, push, tareas ni fases posteriores. Los cambios ajenos de coordinación y constitución se preservaron.

## Spec 002 — auditoría antes de tareas (2026-10-05)
- Usuario pide revisar el plan y generar tareas solo después de una revisión satisfactoria. No es posible garantizar cero errores por revisión documental; no se afirmó esa garantía ni se ejecutaron tests.
- `sdd-reviewer` detectó seis P1. Plan corregido por `sdd-planner`: orden global de bloqueos y writers, estados dependientes/idempotencia, origen online/offline estable, claves durables de sesión y compensaciones/capacidad real de devolución. Segunda auditoría considera cinco P1 documentalmente resueltos; LWW permanece bloqueante de negocio en DA-11.
- Precisiones adicionales incorporadas: versiones del lockfile, SQLite raw, pertenencias históricas no inferidas, jornadas ausentes/snapshot paginado y revocaciones aplicadas inmediatamente aun si el pull falla, sin restaurar detalle ya revocado.
- Falta confirmar anulación concurrente terminal vs LWW entre operaciones permitidas y unidad registro/campos acoplados. No se decidió prioridad por cuenta propia.
- Propuesta pendiente: primer paquete aislado `dinero_cortes.py` + test puro, sin API/DB/migración/cifrado/sync, cobertura parcial RF-3/RF-4/RF-41/RNF-1, 2–4h y ≤10 futuras tareas. El resto se divide progresivamente manteniendo el contrato global; no crear `tasks.md` global enorme ni macro-tareas disfrazadas.

## Spec 002 — resultado vigente de tareas (2026-10-05)
- Usuario acepta anulación autorizada terminal y LWW por método/fecha independientes y grupo financiero coherente, sin eludir permisos/pagos/cierre. RF-36/RF-40 y plan actualizados antes del desglose; DA-11 cerrada.
- Usuario autoriza división progresiva y creación de tareas únicamente para el primer paquete monetario puro. No se autoriza implementación ni paquetes posteriores.
- `sdd-reviewer` verifica coherencia de spec/plan: **LISTO PARA TAREAS DEL PAQUETE 1**. Creado `specs/002-registro-cortes/tasks.md`: seis tareas de 20–30 min (2–3h), dependencias, RF/RNF parciales, «Hecho cuando:», comando aislado y evidencia futura explícitamente no ejecutada.
- Segunda revisión de tareas: **TAREAS APTAS PARA EL PAQUETE 1**, sin bloqueantes. Precisión editorial incorporada sobre conservación de todos los parámetros del contexto Decimal.
- Archivos productivos futuros limitados a `backend/app/services/dinero_cortes.py` y `backend/tests/test_dinero_cortes_aislado.py`; no se crearon todavía. Sin API, datos, migraciones, nuevas dependencias ni suite global. Cobertura parcial RF-3/RF-4/RF-41/RNF-1, no cumplimiento integral de 57 RF.
- Próximo paso: aprobación explícita para implementar T1 con tests primero, verde, marcar únicamente esa tarea y parar. No se realizaron commits/push/merges ni modificaciones a cambios ajenos.

## Spec 002 — autorización vigente de implementación
- Usuario responde «Comienza» y luego confirma «Implementar las seis actuales» ante aclaración de alcance. Autoriza T1–T6 del paquete monetario, en orden; no redactar ni implementar paquetes globales adicionales.
- Cada ejecución de `sdd-implementer` aborda solo una tarea y para; el coordinador inicia la siguiente tras verificar evidencia y ausencia de bloqueantes. Se mantienen los dos archivos productivos, aislamiento de pytest y prohibición de DB/API/migraciones/dependencias.

## Spec 002 — resultado de implementación del paquete 1
- Ejecutadas seis invocaciones secuenciales de `sdd-implementer`, una por tarea. Creados solo `backend/app/services/dinero_cortes.py` y `backend/tests/test_dinero_cortes_aislado.py`; tres funciones puras Decimal y pruebas aisladas. T1–T6 marcadas con comandos y resultados en `tasks.md`.
- T1: módulo ausente en rojo → 33 verdes. T2: función ausente en rojo → 75 verdes. T3: función ausente en rojo → 117 verdes. T4: 125 verdes iniciales, sin fallo artificial. T5: 24 fallos/143 verdes iniciales → 167 verdes. T6: 167 verdes finales (0.12s, salida 0).
- Contexto privado de aritmética, redondeo explícito solo de comisión, barbería como resto exacto y contexto llamador intacto; sin convertir entradas ni aceptar no-Decimal/no finitos/precisión excesiva. Valores grandes representables y error explícito de límite técnico probados.
- Python 3.11.9/pytest 7.4.3 existentes; imports/configuración comprobados y runner aislado del plan, sin fixtures globales, `app.main`, DB, suite global ni instalaciones. No se cambiaron API/modelos/servicios existentes. Sin commits, push ni merges.
- Cobertura parcial RF-3/RF-4/RF-41/RNF-1 y evidencia RNF-6, no cumplimiento integral de la spec. Próximo paso inmediato: revisión de cierre documental/código/tests del paquete, sin implementar otra tarea o paquete ni iniciar validación integral de la spec.

## Spec 002 — cierre del paquete 1
- `sdd-reviewer` dictamina **APROBADO PAQUETE 1**, sin correcciones ni bloqueantes dentro del alcance. Verificación independiente de imports/configuración, firmas/contratos, aritmética/contexto y seis tareas/evidencia.
- Reejecución exclusiva del test puro con el runner aislado: `167 passed in 0.13s`. Los resultados rojos históricos se contrastaron documentalmente, no se reprodujeron rompiendo código.
- Cierre limitado al paquete de dos archivos; la aplicación todavía no usa esas funciones. No constituye validación integral de 57 RF/6 RNF ni autoriza paquete 2, API, DB, migraciones o frontend. Próximo paso: proponer el siguiente paquete solo si el usuario lo aprueba.
- Git flow: ramas de trabajo desde `dev` → PR a `dev`; `dev` → `main` por release

## Spec 002 — paquete 2 redactado (2026-10-06)
- Simplificación aprobada por el usuario: sin bóveda cifrada (stores por cuenta + wipe), sin barrera global de locks (UoW monoescritor `BEGIN IMMEDIATE`, protocolo completo diferido a PostgreSQL), sin escritura dual (centavos INTEGER solo en tablas nuevas, legacy congelado), pull por cursor+revisión sin manifests, LWW con marcadores por unidad en vez de tablas de candidatos, sin React Query y Vitest mínimo.
- Alcance del paquete 2 aprobado y `tasks.md` redactado (T7–T13, ~3h) en rama `feat/spec-002-paquete-2-fundaciones`: conectar `dinero_cortes` al registro, validación canónica, UoW única (commitean routers), validador en schema usuario, snapshot aplicado, esqueleto Alembic solo-inspección y regresión Decimal exacta. Excluye DTO personal (gate `parte_barberia`), `create_all`, sync, frontend y movimientos.
- Implementación T7–T13 completada (7 commits, pusheados a la misma rama): reparto puro conectado (fix real HALF_UP `0.02`→`0.03`), rechazo de precisión excesiva/no-Decimal con 400, UoW única, validador en schemas usuario, snapshot probado inmutable, Alembic solo-inspección y regresión exacta (36+4+167 verdes). `barberia.db` intacta en toda la secuencia (mismo hash). Hallazgo: el ORM oculta excesos de precisión al leer (raw 10.005 → `10.01`); resuelto con T8-bis (validador en `schemas/servicio.py`, decisión delegada por el usuario). Revisión de cierre ejecutada: **APROBADO PAQUETE 2** sin bloqueantes (4 P2 menores en `tasks.md`); no autoriza paquete 3 ni declara la spec implementada.

## Recuperación documental (2026-10-05)
- Recuperado el contenido útil de `b211ee5` en una rama nueva desde `dev`, sin cherry-pick ni reescritura de la rama histórica `feat/mcp-config-y-offline`.
- Conservados el estado y los pendientes actuales; no se recupera la afirmación antigua de que todos los tests están completos.
- Plantilla MCP adaptada a la documentación de OpenCode V2 (`mcp.servers`, `disabled`, credenciales por entorno). La configuración local existente no se modifica. La conexión de los servidores de la plantilla queda por verificar en cada entorno.
