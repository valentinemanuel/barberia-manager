# Plan técnico — Spec 002: Registro de cortes del barbero

Estado: **módulo monetario implementado y revisado, aún no conectado a la API; spec completa pendiente**. Continuación retirada por el usuario.
Fecha: 2026-10-05. Rama comprobada: `feat/spec-002-registro-cortes`.
Entrada normativa: `spec.md` aprobada, RF-1–RF-57 y RNF-1–RNF-6, `docs/constitution.md`, `AGENTS.md`, spec 000 y diseño 001. `MEMORY.md` leído como contexto; sus rondas anteriores no sustituyen el estado vigente de la spec.

Este documento es un plan global, **no un tasks.md**. Historial: el dictamen inicial fue REQUIERE CORRECCIONES Y DIVISIÓN; después se aprobaron DA-11, división progresiva y tareas/implementación del paquete monetario (§2). Su cierre fue aprobado por `sdd-reviewer`, con 167 tests aislados verdes según `tasks.md`; las funciones aún no están conectadas a la aplicación. El usuario retiró la continuación posterior: se conservan el plan global y la evidencia monetaria, sin autorización vigente para continuar. No se afirma que una revisión documental equivalga a tests verdes.

**DA-11 resuelta en la spec aprobada:** anulación autorizada terminal prevalece frente a ediciones concurrentes, incluso con timestamp anterior. Entre ediciones todavía permitidas, LWW por método, momento real y grupo financiero íntegro servicio/barbero/precio/porcentaje/reparto. No elude autorización, pagos/cierre, ni reactiva. §6.C refleja esa decisión, no un candidato completo que pise campos independientes. No reabrir DA-11. El gate privacidad/compatibilidad (§4) es una decisión separada, no resuelta por la aprobación anterior.

## 1. Resultado de exploración y alcance técnico

### Evidencia del checkout

| Área | Situación comprobada | Consecuencia para 002 |
|---|---|---|
| `backend/app/models/corte.py` | ID entero, reparto `Numeric`, una `fecha` UTC naive; no anulación, versión, movimientos ni vínculo a cierre | Ampliación aditiva; conservar snapshots históricos e IDs |
| `services/corte_service.py` | `quantize` sin `ROUND_HALF_UP`; servicio necesariamente activo; `commit` interno | Corregir redondeo y trasladar transacción al orquestador; no reutilizar este `commit` en operaciones compuestas |
| `routers/cortes.py` | Registro solo del actor, historial propio y detalle con 404 ajeno; respuestas únicas con reparto; resúmenes desde medianoche UTC y sin límite superior | Mantener rutas; añadir contrato personal seguro, historial, movimientos y límites de negocio |
| `routers/sync.py` | Envelope `id/accion/datos`, resultado booleano; no journal idempotente, fecha, mapping servidor/local ni resultado financiero | Protocolo ampliado y typed; compatibilidad del envelope antiguo, resultados individuales |
| `models/cierre_caja.py`, router/schema | Snapshot de totales aportado por cliente; no apertura, pertenencias ni ajustes; resumen equipara precio del servicio con ingreso | Añadir jornada explícita, snapshots de pertenencia y journal de ajustes, sin reescribir cierres |
| `routers/reportes.py` | Suma todos los cortes, incluyendo futuros anulados; cálculo devengado de servicios, no movimientos | Cambio mínimo para excluir anulados; no crear reportes globales nuevos ni convertir devengado en caja silenciosamente |
| `database.py`, `main.py` | `create_all` al importar app; no infraestructura Alembic aunque `alembic==1.13.0` está instalado | Migración versionada y arranque sin DDL sobre la base real al importar tests |
| Auditoría actual | `Auditoria` es específica de cambios de usuarios, servicio hace `commit` | Auditoría de cortes separada y dentro de la misma transacción que la operación |
| Backend/dependencias | FastAPI 0.104.1, SQLAlchemy 2.0.23, Pydantic 2.5.2, pytest 7.4.3, httpx 0.25.2; Python 3.11+ | No actualización general de stack; probar sobre versiones fijadas |
| `frontend/package.json` / `package-lock.json` | Rangos declarados React ^18.2.0/Vite ^5.0.8/TS ^5.3.3/Dexie ^3.2.4/PWA ^0.17.4; lockfile resuelve **React/react-dom 18.3.1, Vite 5.4.21, TS 5.9.3, Dexie 3.2.7, PWA 0.17.5, Zustand 4.5.7**; sin React Query/Vitest | Versiones resueltas son la referencia; nuevas dependencias compatibles sin actualizar stack |
| `services/api.ts` | Convierte recursivamente toda cadena numérica a `Number`; interceptor obtiene token global en el envío | Cliente typed sin esa conversión para 002, auth capturada por solicitud y protección ante cuenta distinta |
| `services/db.ts` | Dexie v1 global; importes fraccionarios `number`, IDs locales confundibles con servidor; sin outbox independiente | Migración local conservadora; stores/account context, centavos y UUID separados |
| `useSync.ts` | Cola global de cortes; descarta catálogos válidos cuando falla red; marca sincronizado sin recuperar valores definitivos; no baja historial | Sincronizador por cuenta y operaciones; actualización transaccional sin borrar cache ante errores |
| `RegistroCortes.tsx` | Previsualización flotante, fecha tomada después del fallo de POST, fallback por índice booleano `activo=1` | Outbox antes de red, instante único de captura y filtro activo válido |
| Dashboard, auth y shell | DashboardBarbero solo online; persistencia auth global; useSync en indicador de Layout; admin inicia en dashboard global | Contexto personal explícito y consultas locales; desmontaje/cancelación y aislamiento por generación de sesión |
| PWA | `generateSW`, `autoUpdate`; precache omite woff/woff2; runtime API `NetworkFirst` genérico | Shell/fuentes offline de producción; ninguna cache compartida de respuestas autenticadas |
| Tests/scripts | pytest por módulo con DBs locales y overrides globales; test corte compara con float; Playwright Python visuales/dev con login fijo e import `/src/…`; npm solo `dev/build/preview`, **no lint ni test unitario** | Fixtures temporales seguras y pruebas exactas; E2E producción; no reclamar ejecución de scripts inexistentes |

No se ejecutaron tests, migraciones ni consultas contra bases reales para elaborar este plan. La revisión de archivos no equivale a evidencia de tests verdes.

### Fronteras

- Reutilizar React 18, Vite, Dexie, Zustand, axios y el kit Tinta & hueso. No Vue, rediseño general, refresh tokens ni cola Workbox paralela.
- Servicios, precios de catálogo y porcentajes actuales continúan en sus módulos actuales. Solo ajustar validación de precisión del porcentaje donde se introduce.
- Ventas/productos/consumibles/gastos conservan su lógica. La separación de servicios y movimientos de cortes en caja no presupone un nuevo ledger de ventas.
- Correcciones financieras, evidencia histórica y revisiones quedan disponibles al admin, incluidos sus estados offline; aceptación definitiva siempre revalida servidor.
- No añadir un valor predeterminado a la elección pendiente/parcial/completo del cobro inicial.

## 2. División progresiva: historial del primer desglose

**El alcance global no cabe en diez tareas de 20–30 minutos.** La aprobación inicial se limitó al paquete monetario aislado de debajo, ya cerrado. Esta tabla y sus estimaciones son **históricas, no un compromiso de duración/cantidad de paquetes**; se conservan para trazabilidad. La continuación fue retirada por el usuario.

| Entrega propuesta | RF principales (más invariantes transversales) | Dependencias | Rango de trabajo efectivo |
|---|---|---|---|
| A. Fundaciones monetarias, temporales y migración | 3–6, 41, 44, RNF-1/2/3/6 | Ninguna | 14–22 h |
| B. Registro, contratos personales e historial online | 1–15, 31, 52, 56 | A | 16–24 h |
| C. Outbox, aceptación idempotente y cuenta aislada | 28–36, 51, 55, 57; infraestructura de privacidad | A/B | 24–36 h |
| D. Abonos y saldos independientes, cobro inicial | 16–21, 23, 25, 37–38, 41, 53, 57 | A/B/C | 18–28 h |
| E. Edición/anulación, revisión y correcciones financieras | 22–27, 36, 40, 42–43, 46 | C/D | 20–30 h |
| F. Reasignación, justificantes y evidencia histórica | 44, 47–48, 54, 56 | D/E | 12–20 h |
| G. Jornadas, cierres inmutables e imputación | 24, 39, 45, 49–52 | D/E/F; C para tardíos | 18–28 h |
| H. Integración UX, producción PWA, contratos y regresión | Todos RF/RNF; especialmente 29, 33, 35, 48, 55, 57 | A–G | 18–26 h |

Estimación global **histórica, amplia y no validada: 140–214 h efectivas**. No se utiliza para autorizar ni estimar la continuación actual. Los rangos anteriores no prueban que cada entrega quepa en diez tareas; rojo/verde pertenece a cada futuro paquete, no solo H. No se promete cantidad total de tareas, paquetes o specs hijas.

### Primer paquete aprobado y cerrado: reparto y validación monetaria puros

- **Alcance:** función de reparto Decimal con `ROUND_HALF_UP` y resto exacto; validadores puros de porcentaje 0–100/≤2 decimales y abono positivo/≤2 decimales, finitos y sin corrección silenciosa. Base del reparto contiene solo precio del servicio; no sumar productos/consumibles. Vectores de redondeo y entradas inválidas. Sin tiempo/reloj, DB ni efectos.
- **Archivos creados en el paquete cerrado:** `backend/app/services/dinero_cortes.py` (solo esas funciones puras) y `backend/tests/test_dinero_cortes_aislado.py` (tests que importan solo dominio, **nunca `app.main` ni routers**). Este módulo sustituirá la ubicación del reparto/validadores en los módulos generales del inventario, que los reutilizarán posteriormente.
- **Dependencias:** Decimal de biblioteca estándar y pytest ya fijado. Comprobar que importar el módulo puro no crea motor/Session ni abre DB; ejecutar solo ese archivo aislado en el paquete. No cambiar requirements, fixtures globales, modelos ni servicios existentes en este primer alcance.
- **Fuera:** API, schema usuario actual, conexión del cálculo al registro pagable, cambios a `corte_service.py`, saldo disponible/excesos/devoluciones, cents frontend, migraciones, permisos, outbox y LWW. Ningún comportamiento productivo financiero cambia antes de validar sus contratos.
- **Trazabilidad parcial:** parte aritmética de RF-3, aislamiento de base RF-4, precisión de entrada de RF-41 y RNF-1; **no** aceptación inicial, abonos concurrentes ni cumplimiento integral de esos RF, y mucho menos de los 57 RF.
- **Estimación provisional:** **2–4 h**, para desglose aprobado de **≤10 tareas de 20–30 min** incluyendo rojo/verde y evidencia; el coordinador redacta tareas, este agente no. Si excede el límite, reducir/reproponer antes de continuar. No se autoriza implementar por aprobar el desglose.

No se propone ni se da por aprobada una cantidad de specs hijas. Los restantes paquetes se definirán de uno en uno según decisiones, evidencia y dependencias; persistencia, concurrencia y E2E no se esconderán dentro de tareas enormes.

Las entregas se pueden integrar detrás de capacidades no expuestas hasta cerrar sus dependencias. Un corte con estado financiero incompleto no debe aparecer «listo» en una entrega parcial. El contrato de 57 RF sigue siendo el criterio de finalización global; cada propuesta hija referenciará RF e invariantes transversales y requerirá aprobación independiente.

**Decisión inicial (histórica):** «Sí realiza todo eso», incorporada a la spec: división progresiva y tareas únicamente del paquete puro de 2–4 h. No volver a pedir aprobación de DA-11/división ya resueltas. El límite de dos archivos se respetó en ese paquete.

### Interfaces exactas del primer paquete (para el coordinador de tareas)

Contratos ya implementados del paquete cerrado en `backend/app/services/dinero_cortes.py` y `backend/tests/test_dinero_cortes_aislado.py`. El límite de dos archivos corresponde a ese paquete. Funciones sin DB, reloj, estado global, Pydantic, conversión de cadenas o construcción desde float:

| Firma pública exacta | Resultado / contrato | Referencias parciales |
|---|---|---|
| `validar_porcentaje(valor: Decimal) -> Decimal` | Valor finito, representación con ≤2 decimales, 0–100 inclusive; retorna el **mismo Decimal sin cambiar valor/escala/signo** | RF-41 |
| `validar_importe_abono(importe: Decimal) -> Decimal` | Finito, ≤2 decimales, estrictamente >0; retorna el mismo Decimal; **sin saldo/origen ni aceptación financiera** | RF-41 |
| `calcular_partes(precio: Decimal, porcentaje_barbero: Decimal) -> tuple[Decimal, Decimal]` | Valida precio canónico del servicio y porcentaje; retorna `(parte_barbero, parte_barberia)` en Decimal al centavo, comisión ROUND_HALF_UP y resto exacto | RF-3/4, RNF-1 |

Validación estable: primero tipo Decimal, después finitud, precisión representada y rango. **TypeError** para un no-Decimal, sin convertir `str`, `int`, `bool` ni `float`; **ValueError** para Decimal no finito, precisión o rango inválidos. Mensajes en español específicos del campo: «El porcentaje debe ser Decimal» / «El importe del abono debe ser Decimal» / «El precio del servicio debe ser Decimal»; después «[campo] debe ser finito», «[campo] debe tener como máximo dos decimales», «El porcentaje debe estar entre 0 y 100», «El importe del abono debe ser positivo» o «El precio del servicio no puede ser negativo». Sin clases de error externas ni archivo auxiliar.

«Hasta dos decimales» se comprueba sobre `Decimal.as_tuple().exponent` finito (≥−2), **no** contando dígitos de un string, multiplicando con float, `normalize()` o redondeando la entrada. `Decimal("50.000")` no se corrige silenciosamente a50.00; `Decimal("1E+2")` representa100 sin parte fraccionaria y cumple. Un porcentaje `Decimal("-0.00")` está matemáticamente dentro de 0–100 y **se admite**, conservando su representación; no inventar prohibición de signo− para cero. Un abono cero, positivo o negativo de signo, no es >0 y se rechaza. Válidos no se quantizean en los validadores.

**Boundary precio:** Decimal canónico, finito, no negativo y escala ≤2/exacto en centavos, procedente del catálogo existente; no precio histórico libre. Se rechaza precisión inválida, sin corregirla. Cero (incluido signo− matemáticamente cero) sigue siendo no negativo; no añadir precio mínimo ni tope de negocio. La limitación persistente actual de Numeric(10,2) se controla fuera de este módulo en paquetes de frontera posteriores: el cálculo puro no la transforma en un máximo nuevo, y prueba precio exacto grande representable (>10 dígitos). No sustituye el diagnóstico raw SQLite ni acepta floats leídos allí.

**Aritmética independiente del contexto llamador:** tras validar, construir contexto Decimal privado completo y entrar/salir mediante `localcontext`; precisión derivada de dígitos/exponentes de operandos, suficiente para producto exacto, división exacta por100, quantize de comisión a0.01 y resta/representación del resto exactos. Fijar ROUND_HALF_UP explícito en la comisión; no redondear dos partes separadas. Configurar exponentes y traps/flags de trabajo propios para que precisión baja/rounding distinto/traps Inexact o Rounded del llamador no cambien resultado válido. No llamar `setcontext`, no modificar contexto/flags globales; restaurar al salir incluso ante excepción. Cualquier límite técnico de representabilidad Decimal debe informarse con ValueError en español («No se puede representar el reparto con exactitud»), **no** truncar ni imponer un tope comercial. Los tests verifican resultado y contexto llamador íntegro antes/después.

Pseudocódigo puro: validar tipos/finitud/escala/rangos → en contexto local suficiente calcular comisión exacta `precio × porcentaje / 100` → ROUND_HALF_UP a0.01 → resto exacto `precio − comisión`, representado al centavo sin nueva pérdida → retornar tupla. Ejemplos: precio0.08/porcentaje30 genera comisión0.024→0.02, resto0.06; precio0.05/50 genera0.025→0.03, resto0.02. No pasar0.024 como precio de servicio válido ni tratar esos valores intermedios como abonos ordinarios. Sin generación de movimiento de importe0.

**Runner del paquete 1, ejecutado durante implementación/revisión según tasks.md, no reejecutado en esta actualización:** cwd `backend`, entorno bash (también disponible en Windows); solo este módulo, sin discovery de otros tests:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q
```

`--confcutdir` limita ascendientes, **no basta por sí solo**: `--noconftest` impide cargar cualquier harness/conftest; entorno deshabilita autoload terceros y plugins/addopts inyectados, sin un `-p` que cargue otros. `-p no:cacheprovider` y PYTHONDONTWRITEBYTECODE evitan caches generadas. Imports del test: stdlib, pytest y `app.services.dinero_cortes` exclusivamente; sin `app.main`, `database`, modelos, routers ni tests ajenos. `app/__init__.py`, `services/__init__.py`, `tests/__init__.py` se verificaron vacíos para ese paquete; si cambian antes de ejecutar, volver a verificar cadena/config y **parar si puede abrir DB**, no editar esos archivos bajo este scope. No se localizaron entonces conftest/config pytest de proyecto; si aparece configuración que cargue código, aislarla antes con aprobación, no confiar en flags como garantía contra código externo desconocido. Especificar ruta de test exacta y no ejecutar `pytest tests/`, coverage de toda app, migraciones ni suite global. Evidencia de sus ejecuciones previas en tasks.md; ninguna ejecución nueva en esta actualización.

## 3. Arquitectura y persistencia

### Capas y transacciones

1. Dominio puro: Decimal, balances, reparto, autorización de acciones, recálculo, períodos y decisiones de imputación. No conoce FastAPI, SQLAlchemy ni reloj global.
2. Servicios de aplicación: una unidad transaccional por operación; autorizan, bloquean recursos, calculan, escriben journal/auditoría y registro idempotente; **sin commits en helpers**.
3. Proyecciones: consultas SQL filtradas por contexto `personal` o `gestion`; DTOs explícitos. No enviar ORM completo y ocultarlo en React.
4. API HTTP y sync usan el mismo ejecutor; no duplicar reglas entre registro online/offline.
5. Frontend: operaciones se persisten primero, independientemente de conectividad. Dexie es la fuente durable; React Query representa lecturas del servidor; Zustand sesión/UX, nunca ledger monetario.

Atomicidad requerida: **cada operación** con sus escrituras, idempotencia y auditoría. No atomicidad corte+cobro inicial: el corte puede aceptarse y un pago permanecer en revisión/rechazo/dependencia. RF-57 exige informar ambos resultados.

### Protocolo único de exclusión y orden global de locks

El ejecutor, cierre, apertura, correcciones, resolución/replay y escritores de datos usados como valores actuales comparten **el mismo protocolo**, no órdenes locales distintos:

1. Abrir transacción de escritura limpia: SQLite `BEGIN IMMEDIATE` antes de leer, PostgreSQL lock de fila singleton `ControlEscrituraCortes` precreada por migración. Esa fila es una barrera técnica, **no una jornada abierta** ni apertura automática.
2. Bajo esa barrera descubrir el conjunto completo de recursos y releer valores actuales; luego adquirir locks en el orden **usuarios → servicios → jornadas → cortes → asignaciones → movimientos/originales/journal correctivo → operaciones/dependencias/resoluciones → imputaciones/ajustes**. Dentro de cada clase, PK ascendente; jornadas por fecha negocio e ID. Usuarios incluye actor, destinatario y profesionales previos afectables. Jornadas incluye real, origen y todos los destinos; journal incluye fuentes y devoluciones que consumen capacidad.
3. Si el conjunto observado exige incorporar un recurso de clase/clave anterior ya omitido, abortar/reintentar desde la barrera y redescubrir; nunca adquirirlo fuera de orden. El discovery queda estable porque **todos** los escritores relevantes participan en la barrera. En SQLite la exclusión es de DB, no `FOR UPDATE`; en PostgreSQL el orden se mantiene aunque la barrera sea conservadora y serialice comandos.
4. Autorizar y validar precio/porcentaje, saldos, evidencias, titularidad y estado de cierre **solo desde esas lecturas protegidas**. No usar la Session de auth/objetos precargados ni cache como fuente de la aceptación. Capturar snapshot precio/porcentaje del destinatario y registrar operación/resultado bajo la misma exclusión; cambios de catálogo/porcentaje no pueden intercalarse entre lectura y aceptación.
5. Commit/rollback libera todos los locks; nada de red/cifrado cliente dentro. Reintento acotado conserva UUID/payload/origen. No adquirir la barrera después de haber tomado locks individuales.

**Escritores participantes:** rutas de creación/edición/desactivación/eliminación existentes de usuarios (incluidos porcentaje/rol/activo e invariante del último admin), cambios/desactivación de servicios, adaptadores legacy que escriban cortes/cierres y todos los comandos 002. Ajustes mínimos a su transacción son dependencia RF-5/34/41/49, no nuevas capacidades. El servicio actual de admin no puede emitir segundo BEGIN/commit dentro del ejecutor; las escrituras/auditorías del mismo comando no deben liberar la barrera entre rol y porcentaje. `auditoria_service` tendrá vía de agregar/flush sin commit para caller dueño de UoW, preservando su contrato legacy externo/enum de usuarios y un único commit final. Auth previa solo verifica credencial; estado/actor se releen protegidos.

No se puede bloquear una jornada que todavía no tiene fila. La barrera garantiza observar su ausencia sin carrera con una apertura: **no insertar estado `abierta` para conseguir un lock**. Si no existe destino abierto, el movimiento financiero se acepta con imputación pendiente y solicita apertura admin. Solo el comando admin crea una apertura; con filas existentes se respeta el orden anterior. Para fechas reales no abiertas/sin fila, guardar referencia de fecha sin destino imputado hasta apertura, nunca inferir apertura por ausencia de cierre.

La barrera global se elige por seguridad inicial para una barbería; reducir su alcance requiere medición y otra revisión de exclusión/phantoms. Un mutex del proceso o bloquear solo corte no es alternativa válida. Lecturas paginadas usan protocolo de snapshot descrito en §6.F, no una colección de SELECT independientes.

### Identidad, origen estable y máquina de operaciones

Envelope inmutable y hash canónico incluyen: actor inferido del token/namespace autorizado, UUID, acción/versión, **`modo_captura: online|offline`**, timestamp del cambio, momento real, base versión y referencias de base por unidad si aplica, campos explícitos, referencias originales/dependencias e importes. Unidades tocadas se derivan/validan en servidor; snapshot financiero aplicado es salida servidor, no precio/porcentaje aportado por cliente. Credencial/generación HTTP y estados servidor **no** forman parte del payload financiero. Modo se decide al capturar y persistir, no al recibir un error/reintentar; una operación capturada online que pierde respuesta conserva modo online. El servidor fija modo/hash en primera recepción, valida enum/estructura/namespace/coherencia y rechaza otro payload con la misma UUID.

Modo es metadata del cliente, no prueba criptográfica de disponibilidad física de red. El servidor no puede verificar retrospectivamente esa conectividad; siempre valida permisos/importes y un exceso declarado offline solo conserva revisión sin reconocer dinero automáticamente. No reclasificar un exceso online en revisión cambiando modo tras fallo. Legacy sin campo se adapta una sola vez según endpoint (POST directo online, envelope sync legacy offline) y persiste esa clasificación; no extrapolar garantías v2 a datos v1 sin identidad suficiente.

| Estado persistido | Terminal para reejecución financiera | Reacción a replay del mismo hash |
|---|---|---|
| `aceptada` (incluida imputación pendiente) | Sí | Acuse/resultados autorizados actuales; no ejecutar ni recalcular dinero |
| `rechazada` | Sí | Conservar causa; subsanación con **nueva** operación relacionada, no cambiar payload de la vieja |
| `dependiente_sin_aplicar` | **No** | Reexaminar padres y relación segura bajo locks; si se habilita, validar estado vigente y ejecutar exactamente una vez; si no, devolver causa/dependencias actuales |
| `revision` | No para resolución; nunca autoejecutar con replay | Mantener pendiente; solo nueva resolución admin vinculada y validada habilita efecto |
| `resuelta` | Sí para decisión original | Referenciar decisión/resultado efectivo; no reconocer otra vez base/compensación |

La existencia de una fila idempotente no significa terminalidad. Unique de efecto por operación y resolución de una revisión protege tanto replay de `dependiente` como carrera entre resolución/replay. Estado/datos de resultado pueden avanzar por transiciones auditadas; **hash/UUID/origen/dependencias originales nunca mutan**.

Relación segura: `depende_de` referencia la UUID de creación de **ese corte original**, no un ID libre reasignable. Si padre en revisión es resuelto, un `VinculoResolucionOperacion` conserva padre UUID, resolución UUID y corte UUID original; un hijo encuentra allí su mismo recurso y revalida titular/actor. Un padre rechazado no se autoabre; una subsanación nueva debe enlazarse explícitamente al mismo corte UUID preservado, verificada por gestión/autorización/evidencia, antes de habilitar hijos. No se enlaza automáticamente por servicio/fecha/barbero parecido ni a otro corte existente. Si no se puede demostrar esa identidad, padre/hijos continúan conservados sin aplicación para intervención. Ciclos/dependencias inexistentes no generan ledger. Las referencias de resolución son metadata servidor auditada, no retarget del payload hijo.

### Modelo propuesto

| Entidad / ubicación | Campos e invariantes relevantes |
|---|---|
| `Corte` ampliado | Mantener id/fecha/reparto legacy y revisión global para consultas; metadata de ganador **por unidad** `metodo`, `momento_real`, `finanzas` (timestamp cambio/UUID/ref candidato). `anulado_en`/operación/autor/motivo terminal independientes de esas claves: ninguna edición vuelve a activo. Snapshots/versiones base y referencia de asignación monetaria vigentes; fecha sigue momento real, no timestamp LWW ni sync. |
| `CandidatoEdicionCorte` / `VersionUnidadCorte` (en `models/corte.py`) | Operación/base global y bases por unidad preservadas; solo unidades tocadas, antes/candidato/después y clave cambio/UUID. Método/fecha son escalares independientes. Finanzas guarda candidato íntegro servicio/barbero/precio/porcentaje/reparto y snapshot de valores actuales aceptados bajo locks; índice único operación+unidad. No candidato fullrecord ni ledger sustituible. |
| `AsignacionComision` | ID propio, corte, profesional, vigencia y obligación conocida/desconocida, precio/porcentaje/comisión aplicados. Conserva períodos/asignaciones anteriores; la nueva asignación no recibe pagos anteriores. Una sola vigente por corte, incluidas obligaciones nulas al anular. |
| `MovimientoCorte` | UUID estable, corte, concepto cliente/comisión, asignación/profesional monetario cuando comisión, tipo abono/compensación/devolución, importe exacto, autor, método, momento real opcional solo para evidencia histórica sin fecha conocida, registrado/aceptado UTC, original y motivo/evidencia en correctivos. Append-only. Estado de aceptación y estado de imputación separados. Correcciones administrativas del momento real se conservan en eventos `CorreccionMomentoMovimiento` vinculados: original intacto, instante efectivo corregido para consultas y ajustes sin crear un segundo abono. |
| `FuenteEfectivo` / `ConsumoDevolucion` | Fuente vinculada al movimiento original y concepto/asignación; evidencia/correcciones de efectivo reconocidas por resolución, nunca raw como cap. Cada devolución asigna consumo exacto a fuentes bajo lock, con operación única; snapshots/proyección no duplican efecto de evidencia y asiento correctivo. |
| `AuditoriaCorte` | Acción, actor, corte, operación UUID, recibido UTC, anterior/posterior, motivo y evidencia; privada de gestión. No extender arbitrariamente el enum de auditoría de usuarios. |
| `OperacionCorte` | Clave única `(actor_id, namespace_cliente, operacion_id)`; envelope/hash/origen/bases inmutables, unidades tocadas derivadas, resultados aplicados/omitidos por unidad y refs de snapshots; dependencias/recepción/transiciones. Replay terminal no reconstruye ni recalcula candidato. `dependiente_sin_aplicar` reexamina habilitación, `VinculoResolucionOperacion` liga mismo corte original sin retarget. |
| `ControlEscrituraCortes` | Fila técnica precreada que serializa writers relevantes y revisión monotónica por commit para pull; no es jornada, pago ni apertura. |
| `SnapshotPullCortes` / `CambioAccesoCorte` | Manifest paginado materializado por actor/contexto/revisión, expiración y tombstones sanitizados; autorización actual en cada página y barrera de finalización. |
| `JornadaCaja` | Fecha de negocio única, zona fija, estado abierta/cerrada, autor/apertura y cierre referencia. Apertura administrativa explícita; no automática por recibir un pago. Fecha es día de negocio, instantes son UTC. |
| `PertenenciaCierre` | Cierre original, corte y snapshot de servicio/reparto/version incluido; inmutable. Para tardíos, asociación al cierre mediante ajuste, no inserción en el snapshot original. |
| `ImputacionMovimiento` | Movimiento, jornada real y destino, cierre afectado cuando exista, estado imputado/pendiente; única por destino de la misma operación. No constituye un nuevo abono. |
| `AjusteCierre` | Operación/corte/movimiento/asignación, cierre original, jornada destino opcional, cambios/deltas de obligaciones y dinero separados, autor/motivo/instantes. Append-only; evita contar como dinero una corrección de servicio. |
| `ClaveAlmacenLocal` | Clave de cifrado por usuario versionada, protegida en servidor; devolución solo al titular autenticado para desbloquear sus stores sensibles. No en listados de usuarios ni en auditorías/logs. Es infraestructura de aislamiento, no nuevo rol ni login offline. |

Índices: UUIDs únicos; idempotencia única; `(barbero_id, fecha, id)`; `(profesional_id, asignacion_id)`; `(corte_id, concepto, aceptacion)`; `(estado, actor_id)` operaciones; fecha de jornada única; referencias de ajustes/originales; estado de imputación. FKs para recursos existentes y originales. Los envelopes preservados sin recursos recuperables viven en `OperacionCorte`, no en filas con identidad ficticia. Restricciones de importe/tipo/porcentaje se validan en dominio y DB donde corresponda.

### Exactitud monetaria en SQLite y PostgreSQL

- Backend opera **solo con Decimal**. API: cadenas de pesos con dos decimales; porcentajes como cadenas de hasta dos decimales. Redondear únicamente comisión con `ROUND_HALF_UP`, barbería = precio − comisión.
- Nuevos importes autoritativos se almacenan como centavos `BIGINT` mediante un tipo/adaptador Decimal↔entero estricto; porcentajes en centésimas de punto. Evita que SQLite `NUMERIC` pase aritmética fraccionaria por REAL. No son cálculos de negocio en int en backend: conversión exacta solo en frontera de persistencia.
- Snapshot exacto aditivo para precio, porcentaje y reparto de Corte; columnas `Numeric` anteriores permanecen para compatibilidad, pero **no son fuente** para saldos nuevos. Escritura dual validada; lectura legacy serializa desde snapshot exacto cuando existe.
- Catálogo y usuarios aún usan Numeric: inspeccionar también **representación SQLite original** (`typeof`/lectura textual sin adaptador que quantize a escala2) en copias para detectar precisión inválida/artefactos REAL. No asumir que `Numeric(…,2)` demuestra que el dato raw tenía ≤2 decimales: el ORM puede ocultar exceso. Valores recuperables requieren diagnóstico y correspondencia verificable al snapshot de centavos, bajo locks al aceptar. Ante exceso de precisión/discordancia no hacer `quantize` ni truncar silenciosamente para «reparar»; detener conversión del dato y conservar para revisión/evidencia. No recalcular históricos ni usar SUM REAL como autoridad. La representación original se preserva; su tratamiento exacto se valida en copia, no con datos reales en esta fase.
- Frontend `Centavos` es entero seguro; porcentaje en centésimas de punto. Conversión de cadenas por dígitos, no `parseFloat`, `Number(decimal)` ni `*100` de un decimal binario. Comisión estimada con intermediarios enteros exactos (BigInt cuando la multiplicación pueda exceder entero seguro), mitad hacia arriba, resultado a Centavos validado.
- Límite técnico de representabilidad: respetar el rango monetario existente de `Numeric(10,2)` en contrato legacy y rechazar overflow, nunca truncar. No introducir un tope de negocio diferente. No mezclar pesos y cents en el mismo tipo.

### Saldos, desconocidos y journal por profesional

Para cada obligación conocida: `saldo = max(obligacion − neto_reconocido, 0)` y `excedente = max(neto_reconocido − obligacion, 0)`. Estado conocido nulo: pagado/saldado sin generar abono cero. Neto = abonos aceptados + compensaciones reconocidas − devoluciones explícitas; pendientes de envío/revisión/rechazados se presentan aparte. Una aceptación pendiente solo de imputación **sí cuenta** financieramente.

Compensación corrige registro, no prueba una devolución real. Por **fuente original** de cada concepto/asignación se mantienen (a) importe registrado original inmutable, (b) base documental reconocida + compensaciones contables referenciadas, (c) dinero efectivo reconocido con evidencia y sus rectificaciones documentales, (d) devoluciones reales consumidas contra esa fuente. No sumar el original raw como dinero físico si fue corregido; no contar una compensación como salida física. Estado de aceptación/revisión es independiente del importe raw. Todos los efectos de una rectificación comparten `resolucion_id` y referencias para impedir que proyecciones sumen dos veces la evidencia y la compensación.

`capacidad_devolucion_fuente = max(efectivo_reconocido_corregido − devoluciones_aceptadas_de_esa_fuente, 0)`. La devolución requiere asignación explícita a fuentes autorizadas del concepto/profesional y consume esa capacidad bajo locks; no basta un agregado de abonos raw. Corrección positiva solo incrementa capacidad si hay evidencia de dinero real, no por elevar precio/comisión ni por un signo contable positivo. Correcciones sucesivas se calculan contra el último reconocido de la fuente, no siempre contra el original; replay no vuelve a restar/añadir. Si evidencia y neto reconocido son incompatibles, conservar revisión, no fabricar efectivo ni aprobar devolución por heurística.

Ejemplos exigidos (importes Decimal, sin movimiento físico implícito):

| Caso | Aceptación/compensación exactas y final visible |
|---|---|
| Original **aceptado registrado100**, admin acredita **real50**, sin devolución previa | Mantener asiento original100; operación admin nueva agrega compensación contable−50 vinculada y evidencia que rectifica efectivo reconocido a50. Neto reconocido50; capacidad de devolución50, **no100**. No registrar una devolución50 por esa corrección. |
| Original **pendiente revisión100**, admin acredita **real50**, saldo suficiente para50 | No aplicar−50 sobre base0 (daría neto−50 falso). Una resolución transaccional conserva el original100, reconoce su **base documental100 y compensación−50 juntas**, y evidencia efectivo50. Ninguna vista/commit intermedio reconoce físicamente100; final neto50/capacidad50, original `resuelta` por corrección con importe original100 y resultado efectivo50. Ese reconocimiento documental no es un segundo abono ordinario ni el caso RF-53 de dinero real íntegro100. |
| Pendiente100 acredita **real100** contra obligación80 | Reconocimiento íntegro100 sin compensación por exceso: saldo0/excedente20, capacidad100 menos devoluciones existentes. No bajar importe a80. |
| Tras corrección real50, devolución explícita30, dos devoluciones concurrentes de20 | Neto financiero20 y capacidad20 restante. Como máximo una nueva devolución20; la otra no puede consumir la misma fuente. Reintentar devolución aceptada no consume otra vez. |

En el segundo ejemplo, creación del efecto documental original, compensación y evidencia forman **una** unidad correctiva atómica (RF-43/53), distinta de atomicidad corte+pago ordinario. El original nunca se borra ni se edita a50 y no se anuncian100 como dinero realmente aceptado. Una evidencia histórica/rectificación que descubre devoluciones ya superiores al real requiere intervención sobre esos datos; no crear pagos/deudas/devoluciones automáticos para ocultarlo. Este plan no añade política de recuperación de dinero por fuera de lo aprobado.

Concepto desconocido: obligación/saldo no se infieren de un método de pago o de un cierre agregado; comisión devengada histórica registrada se conserva, comisión pagada/pendiente conocida no se inventa. UI permite evidencia administrativa para completar conocimiento; si no permite validar un saldo para abonar offline, no confirmar un abono ordinario inexistente. No generar pagos usando la fecha actual como reemplazo de una fecha histórica desconocida.

Reasignación A→B: cerrar obligación de asignación A conservando journal de A y su excedente; crear obligación B con porcentaje actual, sin movimientos abonados heredados. Deuda cliente pertenece al corte y no cambia por cambiar únicamente barbero. A ya no consulta corte ni snapshots nuevos: solo DTO de justificantes propios y regularización de su journal, sin nombre/ID/porcentaje del nuevo profesional. Los pagos correctivos/devoluciones para A se refieren a la asignación anterior, no a B.

### Journadas y cierre inmutable

- `America/Argentina/Buenos_Aires`; intervalos de jornada `[00:00, 00:00 siguiente)` convertidos a UTC con `zoneinfo`. Semana lunes–domingo; mes y total tienen límites explícitos.
- Cierre captura servicios realizados y movimientos imputados como se conocen **al aceptar**; no asume cobrado=precio. Los cortes de su jornada quedan bloqueados por pertenencia; los tardíos quedan vinculados por ajuste y también bloqueados.
- Dinero usa momento real del movimiento, no fecha del corte. Si jornada real **existe y está abierta**, se imputa allí; si cerrada, generar ajuste a la abierta actual. «No tiene cierre» o «no tiene fila» **no demuestra apertura**: si falta el destino abierto requerido, aceptar dinero, saldo actualizado, imputación pendiente/referencia real y solicitud de apertura administrativa; ninguna fila se crea abierta por recibir dinero.
- Corrección de fecha/servicio/barbero de corte cerrado mantiene asociaciones/snapshots originales y genera deltas referenciados para las jornadas afectadas; nunca UPDATE de totales originales.
- Cierre, recepción tardía, abonos, edición y resolución de pendientes usan bloqueo común de jornada/corte para no «pasar por el hueco» del cierre. Apertura/imputación pendiente se serializa; la acción de imputar no puede aplicar dos veces dinero. Corregir el momento de un movimiento es solo administrativo, con original/momento efectivo y trazas separados: puede producir ajustes de imputación entre jornadas, pero nunca otro efecto sobre saldo por el mismo dinero.
- El resumen nuevo de caja distingue precio/devengado de servicios, cobros y pagos por método, ajustes y desconocidos; no sustituir el significado histórico de `total_cortes` ni reinterpretar cierres legacy.

## 4. Migraciones y compatibilidad de despliegue

### Backend: expansión versionada, idempotente y conservadora

Alembic ya es dependencia, pero no hay configuración/revisiones. Proponer baseline que cree tablas preexistentes **solo si faltan**, inspeccione estructura compatible y se detenga ante diferencias; después revisión aditiva 002. No hacer `stamp` a ciegas ni importar `app.main` desde env de migración.

Proceso futuro exclusivamente sobre copia temporal primero:

1. Inventariar schema, versiones y cantidades; backup verificado/restaurable. Detectar FK huérfanas, importes no recuperables, cierres duplicados/fechas ambiguas. Emitir diagnóstico, no reparar/importar identidad ficticia.
2. Crear tablas/columnas nuevas, inicialmente nullable donde hace falta backfill; constraints/índices al terminar validación. Usar operaciones compatibles SQLite, batch solo cuando sea imprescindible; inspección para instalaciones ya parcialmente expandidas, sin sobrescribir filas nuevas.
3. UUID estable para filas legacy a partir de namespace y PK; `fecha` antigua se conserva como UTC según contrato existente. Separar creado/aceptado desconocidos cuando no existe evidencia, no poner `ahora` como fecha histórica inventada.
4. Inspeccionar precisión/representación raw SQLite además del valor ORM (que puede ocultar decimales); copiar snapshots recuperables **sin recalcular ni quantize reparador**. Conservar representación/checksum raw y diagnosticar discordancias antes de convertir. Estados cliente/comisión legacy = sin información salvo evidencia comprobable. Método del corte/totales de cierre no son evidencia; no insertar abonos sintéticos.
5. Mantener originales de cierre idénticos. **Compartir fecha con un cierre legacy no demuestra que el corte haya sido incorporado**: el esquema anterior no registra esa pertenencia. Migrar vínculos solo con evidencia verificable de incorporación y conservar desconocimiento/diagnóstico cuando falte; no bloquear cortes históricos mediante una asociación inferida por fecha. RF-49 aplica a cierres aceptados mediante el nuevo protocolo y a tardíos de jornadas de cierre cuya identidad/pertenencia pueda verificarse. La sola presencia de un cierre antiguo no implica jornada abierta/relación reconstruida. Cierres múltiples/fechas ambiguas detienen su conversión; no elegir uno arbitrariamente ni decidir la pertenencia por importes coincidentes.
6. Verificar conteos, checksums de snapshots/cierres, repartos y desconocidos; ejecutar upgrade de nuevo y comprobar mismo contenido/índices. Un upgrade repetido no vuelve a rellenar campos corregidos por admin.

No afirmar que `create_all` migra columnas existentes: retirarlo del import de `main.py`. El servidor arranca tras revisión de schema requerida; instalación nueva usa migraciones. Los tests no importarán DDL sobre `DATABASE_URL` real.

### IndexedDB: no perder ni atribuir filas v1

- Mantener esquema v1 y agregar esquema v2 y marca de migración; no borrar el store antes de copiar. Separar `idLocal`/UUID/`idServidor`; mapear referencia y dependencias por UUID.
- Cuenta propietaria de operación es el actor, no necesariamente `barbero_id` (admin registra para otro). Crear namespace de cuenta y stores sensibles cifrados para cortes/proyecciones/outbox/justificantes; catálogo de venta no lleva costos ni datos administrativos.
- Datos v1 fueron escritos sin autor distinto del barbero, con floats y sin ID servidor. Convertir solo filas atribuibles **con evidencia de actor**, no solo `barbero_id`, y precisión recuperable sin redondeo silencioso; no asumir que sincronizado implica mapping servidor conocido. Filas ambiguas se conservan en cuarentena de custodia, nunca cifradas con la clave de la cuenta nueva «porque está conectada»; protocolo/limitación operativa abajo.
- Los pendientes antiguos que pudieron aceptarse antes de perder respuesta carecen de journal servidor histórico: **no se puede prometer deduplicación retroactiva perfecta**. No reenviarlos ciegamente. Reconciliar con evidencia o revisión administrativa conservando el registro. Documentar esta limitación de datos previos, no extenderla a operaciones v2.
- Upgrade estructural Dexie es transaccional; cifrado/red se preparan fuera. Importación v1→v2 en lotes idempotentes con ID de origen estable/hash **dentro del payload cifrado** y copia/verificación durable antes de purgar plaintext. No confiar en derivar propietario o recuperar centavos exactos desde float sin diagnóstico. Las ambiguas requieren custodia cifrada independiente de cuentas; no abrir nuevos stores personales si esa transición no ha sido protegida.
- Cache válida de catálogo se reemplaza tras respuesta validada en transacción; un fallo conserva última copia. Índices de estado usar string/número, nunca booleano como clave IndexedDB.

### Ciclo explícito de claves, sesión offline y cuarentena

1. **Provisión inicial conectada:** después de login/perfil del titular, obtener clave/versión y handle opaco de vault propio en respuesta `no-store` no cacheable ni logueada; importar AES-GCM como CryptoKey no exportable. Persistir en IndexedDB un **único slot de sesión activa** con clave(s) necesarias del titular actual, handle/versión, generación y último rol conocido. No persistir un mapa de claves de cuentas anteriores. Preparar cifrado fuera de tx; AAD liga vault/generación de datos/versión/UUID, con nonce nuevo por cifrado. Outbox no guarda token.
2. **Durabilidad y startup offline:** antes de confirmar primera operación offline deben existir tanto clave activa durable como ciphertext verificado. Al recargar/reabrir la PWA **sin volver a autenticarse**, leer primero el slot activo/generación y CryptoKey por structured clone de IndexedDB, comprobar concordancia con la sesión cacheada y abrir solo su vault. El token puede requerir login al reconectar; no exigir validación online para reapertura offline de la sesión ya conocida. Si el navegador no conserva CryptoKey/IndexedDB o se perdió clave, no confirmar nuevas operaciones indecriptables: informar limitación y conservar ciphertext para recuperación conectada del titular.
3. **Logout/cambio:** primero marcar en la sesión durable nueva generación/invalidez y eliminar todas las claves del slot activo en una tx; después limpiar espejo Zustand/localStorage, QueryClient, plaintext en memoria, red y DB handles. Instalar B requiere nueva generación y únicamente sus claves; A mantiene ciphertext pero no una clave recuperable por B. Login siguiente del titular A recupera sus versiones desde servidor, no de una clave/password antigua ni un endpoint admin. Un fallo de transición deja UI bloqueada, no B con clave A.
4. **Multi-tab/BFCache:** `BroadcastChannel`/evento storage avisa, pero la autorización local depende del slot durable/generación comprobada antes de envío, lectura sensible, resultado y al retomar foco/`pageshow`. Tabs suspendidas invalidan memoria al reanudar; no basta escuchar un evento que pudo perderse. Las tareas deberán probar cierre navegador/reapertura, no solo recarga de una pestaña abierta.
5. **Service worker:** precache solo shell/fuentes/estáticos; no API autenticada, claves, ciphertext de outbox ni tokens en CacheStorage/cola BackgroundSync. Al activar nueva versión eliminar caches API legacy conocidas (`api-cache`), sin borrar IndexedDB/session slot ni exigir auth nueva para offline. Los datos sensibles se sirven por repositorio de sesión, nunca por respuesta SW compartida. Actualizar SW no rota ni descarta claves con pendientes.
6. **Metadata:** ciphertext/nonce/versión y IDs opacos técnicos pueden estar fuera; nombres, roles anteriores, `barbero_id`, conceptos, importes, estados/causas, momentos financieros y mapping servidor son cifrados. Namespace de DB es handle opaco, no nombre/email de usuario; registro activo solo describe titular actual. Cuarentena no expone propietario presumido, fila plaintext, error con datos monetarios ni índices de usuario a ninguna cuenta normal.

**[DATO OPERATIVO A VALIDAR — BLOQUEA ROLLOUT LOCAL, NO NUEVO LOGIN OFFLINE]** Para v1 de propietario ambiguo se necesita custodia recuperable que no use claves de usuarios: propuesta técnica de copia cifrada por lote con clave aleatoria envuelta con **clave pública de recuperación operativa**, cuya privada no esté en el navegador ni accesible a cuentas/admin de la app. Antes de borrar v1 verificar copy/hash/recuperabilidad en copia sanitizada, y antes de activar el upgrade disponer de esa pública/proceso de custodia y autorización separada. Clasificar propiedad exige evidencia y una intervención de recuperación autorizada, no un flujo nuevo de acceso admin a otros usuarios. No subir filas ambiguas como operaciones del usuario actual.

Si falta pública/custodia, no es posible simultáneamente eliminar todo plaintext v1 y prometer recuperación offline de filas sin titular conocido: **detener transición/marcar limitación, conservar original y no habilitar cambio de cuenta/producto v2 sobre esa migración incompleta**; validar el procedimiento operativo antes del rollout. No resolverlo perdiendo filas o atribuyéndolas a A/B. La nueva outbox v2 con propietario conocido sí se conserva y reabre con el ciclo anterior. El plan no promete borrar datos que otro cliente v1 ya haya expuesto, ni revocar físicamente memoria de procesos suspendidos/OS ni de un equipo totalmente desconectado; aislamiento entre sesiones cooperantes, eliminación de claves persistidas ajenas y gates reales son verificables, no una garantía contra XSS/control del dispositivo.

### Contratos antiguos y clientes en convivencia

- Conservar rutas y bodies mínimos de registro/consulta, ID entero, `fecha` momento real, strings Decimal y métodos existentes. Registro legacy sin evidencia de cobro crea corte pero **no pago**; no forzar nuevos campos obligatorios en su body.
- Mantener consultas admin de reparto y resúmenes legacy `total_cortes/acumulado/porcentaje_asignado` como proyecciones compatibles (acumulado devengado propio vigente). Agregar metadatos/DTOs nuevos, no renombrar claves en respuestas anteriores.
- DTO personal nuevo excluye `parte_barberia` y todo costo/margen/bruto. La allowlist legacy observada en **CorteResponse propio** es `id, barbero_id, servicio_id, precio, porcentaje_barbero, parte_barbero, parte_barberia, metodo_pago, fecha, sincronizado`. **Propuesta anterior de conservar `parte_barberia` detenida por gate de privacidad/compatibilidad: no es una excepción normativa aprobada.** Verificar titularidad y campos permitidos no resuelve por sí solo la exposición de la parte del negocio. Aclarar contrato/versionado antes de implementar ese adaptador; no añadirla a DTO/cache/resúmenes nuevos ni redefinir «margen» para justificarla. Tampoco eliminarla/nullificarla automáticamente rompiendo compatibilidad por decisión del agente. El resto de compatibilidad se valida tras esa decisión.
- Nueva API personal/gestión explícita; admin en `/mi/…` solo propio. Nuevos recursos financieros/admin no usan DTO legacy amplio.
- Envelope sync viejo conserva `aceptadas/rechazadas/resultados` y campos `id/accion/aceptada/status_code/motivo/notificacion`; agregar `estado`, `dependencias`, resultado typed y revisión. `aceptada=false` no significa que se descartó una revisión; solo el cliente v2 entiende todos los estados.
- Clientes v1 sin UUID/device namespace no permiten distinguir perfectamente colisiones de IDs locales entre dispositivos. Mantener recepción compatible, conservar conflictos para revisión y no mezclar recursos. El rollout exige actualizar PWA para nuevas capacidades y comunicar recuperación de pendientes legacy. No alegar idempotencia universal donde la entrada vieja es insuficiente.
- El cliente financiero 002 usa instancia/API codecs propios sin convertir strings recursivamente. No cambiar todas las páginas ajenas a cents bajo esta spec. Adaptador legacy existente continúa para módulos no tocados; aislamiento de auth/errores sí se aplica al transporte compartido.
- Mantener reportes existentes como devengados, excluyendo anulados y utilizando límites de jornada en sus consultas de cortes afectadas. Caja nueva presenta movimientos aparte, sin cambiar venta/gasto ni generar reportes globales adicionales.

### Rollback

- Despliegue expand→backend compatible→frontend v2→habilitación por capacidades; pruebas con cliente viejo y nuevo antes de activar. No publicar UI que escriba contra un backend sin protocolo v2.
- Rollback **de aplicación**: conservar tablas/columnas/journal y pendientes; deshabilitar nuevas escrituras/capacidades, no ejecutar downgrade destructivo. Frontend antiguo no debe consumir una DB local v2 con semántica incompatible: conservar versión v2 o modo de solo lectura/recuperación, no volver a exponer stores viejos.
- Restauración de backup solo bajo mantenimiento y conciliación de operaciones posteriores; nunca perder abonos aceptados restaurando silenciosamente una foto anterior. No ofrecer downgrade que elimine dinero nuevo.
- Snapshot de cierres y hashes deben mantenerse iguales durante upgrade, reintento y rollback; medir restauración en fixtures/copias antes de cualquier base de trabajo.

## 5. Inventario preciso de archivos para implementación futura

`M` = modificar existente; `C` = crear. La lista es inventario arquitectónico, **no tareas**. Todos los archivos siguientes pertenecen a una implementación posterior aprobada; aquí solo se escribe `plan.md`.

### Backend / despliegue

| Acción y ruta | Responsabilidad | RF/RNF |
|---|---|---|
| M `backend/app/models/corte.py` | Snapshot/identidad, versiones/bases/candidatos por unidad, anulación terminal separada y relación asignación | 3–6, 8–11, 22–27, 36, 40, 42, 44, 46–49 |
| C `backend/app/models/finanzas_corte.py` | Asignaciones, movimientos y correcciones de momento append-only por profesional/concepto | 13, 16–21, 37–38, 41, 43–44, 46–48, 51, 53–54 |
| C `backend/app/models/operacion_corte.py` | Registro idempotente/estados, bases inmutables y resultados por unidad, vínculos seguros de resolución/dependencia | 30, 32, 34, 36, 38, 40, 51, 56–57 |
| C `backend/app/models/control_escritura_cortes.py` | Barrera técnica singleton para todos writers participantes, no abre jornadas | 5, 23–24, 34, 41, 49–50 |
| C `backend/app/models/snapshot_pull_cortes.py` | Manifest de snapshot paginado/revisión/actor, tombstones de revocación, expiración | 14–15, 33, 48, 52, 55 |
| C `backend/app/models/auditoria_corte.py` | Antes/después, motivo, evidencia, autor e instante | 26, 39, 42–43, 47, 54 |
| M `backend/app/models/cierre_caja.py` | Relaciones aditivas, snapshot original protegido | 24, 39, 45, 49–50 |
| C `backend/app/models/jornada_caja.py` | Jornada, pertenencia, imputaciones y ajustes | 24, 39, 45, 49–52 |
| C `backend/app/models/clave_almacen_local.py` | Material de desbloqueo local por titular, versionado | 33, 48; RNF-5 |
| M `backend/app/models/__init__.py` | Registrar modelos para metadata/migraciones | RNF-3 |
| Ya creado `backend/app/services/dinero_cortes.py` | Reparto/validadores puros del paquete monetario cerrado; reutilización productiva posterior pendiente, aún no conectado a API | 3/4/41 y RNF-1 **parciales** |
| C `backend/app/services/dominio_cortes.py` | Edición, bloqueo, candidatos/merge por método/fecha/grupo financiero y anulación autorizada terminal (§6.C); reutiliza reparto puro | 3–6, 22–27, 36, 40–42, 46–47 |
| C `backend/app/services/dominio_finanzas.py` | Saldos/conocimiento/excedentes, validación y devoluciones | 13, 16–21, 38, 41, 43–44, 46–47, 53–54 |
| C `backend/app/services/tiempo_negocio.py` | UTC, zona, jornadas/períodos, futuros/revisión reloj | 8–10, 45, 49–52, 55; RNF-2 |
| M `backend/app/services/corte_service.py` | Crear/editar/anular con snapshots; retirar commit interno | 1–10, 22–27, 31, 40, 42, 46–47, 56 |
| C `backend/app/services/movimiento_corte_service.py` | Aplicar abonos/compensaciones/devoluciones/evidencia, corregir instante real sin duplicar saldo y resolver revisiones | 16–21, 37–38, 41, 43, 46–47, 51, 53–54 |
| C `backend/app/services/operacion_corte_service.py` | Ejecutor común online/sync; idempotencia, roles, dependencias | 14, 30–34, 36, 38, 40, 51, 56–57 |
| C `backend/app/services/consulta_cortes_service.py` | Proyecciones propias/gestión, históricos, justificantes, acumulados y revocaciones | 11–15, 21, 44, 48, 52–55 |
| C `backend/app/services/jornada_caja_service.py` | Apertura/cierre, bloqueo, snapshot, ajustes e imputación pendiente | 24, 39, 45, 49–50 |
| C `backend/app/services/almacen_local_service.py` | Provisión titular de clave protegida, nunca por admin para otro | 33, 48; RNF-5 |
| M `backend/app/services/admin_service.py`, M `backend/app/routers/usuarios.py` | Integrar writers de porcentaje/rol/activo en barrera y orden global, conservar invariante000 sin BEGIN/commit anidados | 5, 34, 41; RNF-3 |
| M `backend/app/services/auditoria_service.py` | Agregar/flush sin commit en UoW de writers usuarios, mantener contrato legacy/acciones; no liberar guard entre escrituras de un comando | 5, 34; RNF-3 |
| M `backend/app/routers/servicios.py` | Writer catálogo/desactivación participa en exclusión de aceptación, sin cambiar permisos/contrato | 5, 31, 56; RNF-3 |
| C `backend/app/persistencia/dinero.py`, C `backend/app/persistencia/__init__.py` | Tipo exacto Decimal/centavos y conversiones sin float | RNF-1 |
| C `backend/app/persistencia/transacciones.py` | Unidad de trabajo, bloqueo SQLite/PostgreSQL, retry acotado | 23–24, 32, 36, 41, 49–50 |
| M `backend/app/database.py` | FKs/control de transacciones y fábrica testable, sin DDL automático | RNF-1/3/6 |
| M `backend/app/main.py` | Registro de routers nuevos, retirar create_all al import; schema requerido | RNF-3/6 |
| M `backend/app/config.py` | Configuración de protección clave local/capacidades, sin secretos en repo | RNF-5 |
| M `backend/app/schemas/corte.py` | Bodies compatibles, bases/campos explícitos de edición y DTO personal/gestión con versiones por unidad sanitizadas | 1–15, 22–27, 36, 42, 47 |
| C `backend/app/schemas/movimiento_corte.py` | Entradas y saldos discriminados; correctivos y evidencia | 16–21, 37–38, 41, 43–44, 46–48, 53–54 |
| C `backend/app/schemas/operacion_corte.py` | Uniones Pydantic por acción y resultado, sin dict Any nuevo | 30, 32–34, 36, 40, 51, 56–57 |
| C `backend/app/schemas/jornada_caja.py` | Apertura/cierre/ajustes/resumen separación de caja | 39, 45, 49–52 |
| C `backend/app/schemas/almacen_local.py` | Desbloqueo propio sin metadata de otro titular | 33; RNF-5 |
| M `backend/app/schemas/usuario.py` | Validador porcentaje: 0–100, dos decimales, no normalizar | 41 |
| M `backend/app/schemas/cierre_caja.py` | Mantener legacy y referenciar nuevos snapshots aditivos | 39, 45, 49; RNF-3 |
| M `backend/app/routers/cortes.py` | Rutas legacy y personales, edición/anulación; DTOs/404 | 1–15, 22–27, 42, 47, 52, 55 |
| C `backend/app/routers/movimientos_corte.py` | Movimientos, justificantes, correcciones monetarias/de momento y evidencia por contexto | 14, 16–21, 25–26, 41, 43–44, 46–48, 51, 53–54 |
| C `backend/app/routers/revisiones_corte.py` | Lista y resolución administrativa con motivo y nueva identidad de operación | 38, 40, 51, 53–54, 56–57 |
| M `backend/app/routers/sync.py` | Adaptar envelope viejo; ejecutar typed nuevo y pull filtrado | 28–36, 38, 40, 51, 55–57 |
| M `backend/app/routers/cierre_caja.py` | Delegar cierres; rutas estáticas antes de ID; resumen legacy compatible | 24, 39, 45, 49–50 |
| C `backend/app/routers/jornadas_caja.py` | Abrir y consultar jornada, imputar pendientes; solo admin | 39, 45, 49–50 |
| M `backend/app/routers/auth.py` | Endpoint de contexto local autenticado, no cambiar login actual | 33; RNF-5 |
| M `backend/app/routers/reportes.py` | Evitar contar corte anulado; límites de jornada para cortes | 27, 52; RNF-3 |
| C `backend/alembic.ini`, C `backend/alembic/env.py`, C `backend/alembic/script.py.mako` | Infraestructura Alembic sin URL/secretos incrustados | RNF-3/6 |
| C `backend/alembic/versions/001_base_legacy.py` | Baseline inspeccionada para DB vacía o legacy | RNF-3 |
| C `backend/alembic/versions/002_registro_cortes.py` | Expansión/backfill idempotente y estados desconocidos | 44, 49, 54; RNF-1/3 |
| M `backend/requirements.txt` | Añadir pytest-cov si se exige comando AGENTS; fijar cryptography usada directamente para clave local | RNF-5/6 |
| C `docs/registro-cortes-operacion.md` | Protocolo/versiones, recuperación legacy, rollout/rollback y evidencia de copia | RNF-3/5/6 |

No ampliar auditoría/gestión de usuarios ni catálogo: además de precisión de schema, solo los cambios de transacción/locks necesarios para que sus writers no eludan la aceptación protegida; preservar invariante000 y permisos. No introducir borrados físicos. `backend/app/dependencies.py` se reutiliza para preflight; decisión final relee actor bajo unidad de trabajo, sin nuevo rol.

### Frontend

| Acción y ruta | Responsabilidad | RF/RNF |
|---|---|---|
| C `frontend/src/types/cortes.ts` | Tipos dominio/API, centavos, conceptos, estados y contextos | Todos contratos de 002 |
| C `frontend/src/utils/dinero.ts` | Parse/format exactos y comisión estimada integer; validaciones | 3, 7, 41; RNF-1 |
| C `frontend/src/utils/tiempoNegocio.ts` | Períodos y captura de instantes, `ahora` parametrizado | 8–10, 51–52, 55; RNF-2 |
| C `frontend/src/services/cortesApi.ts` | Codecs strict strings Decimal↔centavos; auth/contexto capturados | 1–21, 30, 33, 42, 47, 52–57 |
| M `frontend/src/services/api.ts` | No reemplazar token explícito; invalidar respuesta/error de sesión anterior; separar cliente 002 del converter legacy | 33; RNF-1/3/5 |
| M `frontend/src/services/db.ts` | Schema versionado, claves/metadata y bases/versiones por unidad dentro de payload cifrado; preservar migración v1 | 28–29, 33, 35–36, 48, 55 |
| C `frontend/src/services/almacenCuenta.ts` | Stores sensibles por cuenta, cifrado/desbloqueo y cierre; repositorios scoped | 14–15, 28–29, 33, 48; RNF-5 |
| C `frontend/src/services/migracionCortesLocal.ts` | Importación idempotente v1, cuarentena y dedup de mapping | 29, 32–33; RNF-1/3/5 |
| C `frontend/src/services/operacionesCortes.ts` | UUID por corte/operación, outbox persist-first, refs base inmutables/campos explícitos y resultados por unidad, dependencias | 22–23, 28–30, 32–34, 36–40, 51, 56–57 |
| C `frontend/src/services/syncCortes.ts` | Lease por cuenta, push/pull, reintentos y revocación de cache | 30–36, 38, 40, 48, 55–57 |
| C `frontend/src/services/consultasCortes.ts` | QueryClient scoped/keys personales/gestión, cancelar/limpiar; no segunda cola de mutaciones | 11–15, 33, 48, 52, 55 |
| C `frontend/src/services/proyeccionesCortes.ts` | Combinar aceptado/estimado/pendiente sin tocar saldos reconocidos | 7, 11–13, 21, 44, 52–53, 55, 57 |
| M `frontend/src/hooks/useSync.ts` | Delegar motor único por cuenta; estados por operación y cache válida | 28–36, 48, 55–57 |
| C `frontend/src/hooks/useCortes.ts` | Consultas scoped servidor/local y cobertura; reactividad Dexie | 11–15, 28, 52, 55 |
| M `frontend/src/store/authStore.ts` | Generación de sesión, perfil typed, separar claves, logout/cuenta invalidan contexto también entre tabs mediante eventos de sesión | 28, 33–34, 48 |
| M `frontend/src/pages/Login.tsx` | Obtener/desbloquear contexto propio luego de auth sin asumir token previo | 33; RNF-5 |
| M `frontend/src/main.tsx` | Provider consultas scoped y arranque seguro de cache | 28–29, 33 |
| M `frontend/src/App.tsx`, M `frontend/src/components/Layout.tsx` | Rutas propias/gestión, scope explícito, única sync visible, admin también personal | 11–15, 28, 33; RNF-4 |
| M `frontend/src/pages/RegistroCortes.tsx` | Selección activa, ganancia estimada, destino/admin/fecha y cobro inicial sin default | 1–10, 28–29, 35, 37, 41, 51, 56–57 |
| C `frontend/src/pages/HistorialCortes.tsx` | Historial propio/cobertura, saldos, períodos, estados y navegación detalle | 11–15, 21, 27, 44, 48, 52–55 |
| C `frontend/src/pages/DetalleCorte.tsx` | Journal, pagos, edición/anulación y bloqueo; 404 uniforme | 14, 16–27, 40, 42–43, 46–48 |
| C `frontend/src/pages/GestionCortes.tsx` | Vista admin explícita para terceros, revisiones/evidencia/justificantes anteriores | 2, 10, 26, 38–40, 43, 47–48, 51, 53–54, 56 |
| M `frontend/src/pages/DashboardBarbero.tsx` | Acumulados propios confirmed/estimated/paid/due/unknown con fallback local | 7, 12–13, 28, 44, 52–55 |
| M `frontend/src/pages/CierreCaja.tsx` | Jornada/apertura, servicios vs dinero, ajustes y pendiente imputación; cents | 39, 45, 49–50; RNF-1/4 |
| C `frontend/src/components/cortes/FormularioMovimiento.tsx` | Concepto/método/momento propio e importe/parcial/restante; nunca abono cero | 16–21, 25, 37–38, 41, 51 |
| C `frontend/src/components/cortes/FormularioCorreccion.tsx` | Campos permitidos, motivo/evidencia admin; anulación sin reactivar | 22–27, 40, 42–43, 46–47, 54 |
| C `frontend/src/components/cortes/EstadoOperacion.tsx` | Pendiente/revisión/rechazo/aceptado e imputación separada, por operación | 7, 29–30, 38, 40, 50, 53, 57 |
| C `frontend/src/components/cortes/SaldosCorte.tsx`, C `frontend/src/components/cortes/ResumenComisiones.tsx` | Conocido/desconocido/excedente, saldo reconocido vs pendiente y cobertura | 11–13, 21, 44, 52–55 |
| M `frontend/src/styles/vistas.css` | Estados/formularios nuevos con tokens 001, sin framework CSS | RNF-4 |
| M `frontend/vite.config.ts`, M `frontend/src/pwa/ServiceWorkerRegistration.ts` | Shell/fuentes precache, API no cacheada, retirar cache autenticada previa y registro único | 29, 33, 48; RNF-4/5 |
| M `frontend/package.json`, M `frontend/package-lock.json` | React Query compatible React18 y Vitest/testing-library/fake-indexeddb fijados | RNF-6 |
| C `frontend/vitest.config.ts`, C `frontend/tests/setup.ts` | Harness unitario separado del build producto; fake IndexedDB/crypto | RNF-6 |

No migrar DashboardAdmin, Reportes o GestiónProductos a React Query/cents por esta spec. Cuando transporten importes hacia la frontera nueva, codec explícito; no tocar lógica ajena.

**Candidatos de dependencias nuevas, no instalados/aprobados aún:** metadata npm consultada de versiones exactas: `@tanstack/react-query@5.60.5` (peer React ^18||^19), `vitest@2.1.9` (dep Vite ^5.0.0, Node ^18||>=20), `@testing-library/react@16.1.0` (React/react-dom/types ^18||^19, peer DOM^10), `@testing-library/dom@10.4.0`, `jsdom@24.1.3`, `fake-indexeddb@6.0.0` (Node>=18). Compatibilidad declarada con React18.3.1/Vite5.4.21; Node del checkout observado v24.21.0 satisface esos engines. No usar Vitest latest con requisitos de Vite mayor ni actualizar React/Vite/TS/Dexie/PWA para instalar tests. En futuro paquete frontend autorizado fijar esas nuevas versiones, revisar diff de lock/transitivos y ejecutar install/build/typecheck/tests; metadata peer/engine **no prueba** compatibilidad runtime o con TS5.9.3. El primer paquete monetario no instala ninguna.

### Archivos de tests previstos

| Acción y rutas | Cobertura |
|---|---|
| C `backend/tests/conftest.py`; M `backend/tests/test_cortes.py`, M `backend/tests/test_sync_roles.py`, M `backend/tests/test_roles_permisos.py` | Fixtures sin DB real/import DDL, preservar contratos/matriz 000 y assertions Decimal |
| C `backend/tests/test_dinero_cortes_aislado.py` | Primer paquete puro, importa solo dinero_cortes; RF3/4/41 y RNF1 parciales, sin `app.main`/DB |
| C `backend/tests/test_dominio_cortes.py`, C `backend/tests/test_dominio_finanzas.py`, C `backend/tests/test_tiempo_negocio.py` | U1–U3 |
| C `backend/tests/test_cortes_contratos.py`, C `backend/tests/test_cortes_privacidad.py` | I1/I2, rutas legacy/v2 y auth/contexto/clave local |
| C `backend/tests/test_movimientos_corte.py`, C `backend/tests/test_correcciones_corte.py` | I3/I4, saldos/correctivos/evidencia/reasignación |
| C `backend/tests/test_operaciones_corte.py`, C `backend/tests/test_concurrencia_cortes.py` | I5/I6, idempotencia/dependencias/LWW/serialización real |
| C `backend/tests/test_jornadas_cortes.py`, C `backend/tests/test_migracion_registro_cortes.py` | I7/I8, cierres/tardíos/imputación/upgrade repetido |
| C `frontend/tests/unitarios/dinero.test.ts`, C `frontend/tests/unitarios/proyeccionesCortes.test.ts`, C `frontend/tests/unitarios/tiempoNegocio.test.ts` | F1/F2, exactitud, coverage y estados |
| C `frontend/tests/unitarios/almacenCuenta.test.ts`, C `frontend/tests/unitarios/migracionCortesLocal.test.ts`, C `frontend/tests/unitarios/syncCortes.test.ts` | F3/F4, persistencia/cifrado/cuenta tardía/catálogo/reintentos |
| C `frontend/tests/unitarios/registroCortes.test.tsx`, C `frontend/tests/unitarios/detalleCorte.test.tsx` | F5, elección sin default, bloqueo, importe real, resultado parcial, accesibilidad |
| C `frontend/tests/e2e/conftest.py`, C `frontend/tests/e2e/test_registro_cortes.py`, C `frontend/tests/e2e/test_finanzas_cortes.py`, C `frontend/tests/e2e/test_offline_cuentas.py`, C `frontend/tests/e2e/test_jornadas_cortes.py` | E1–E4, fixture autenticada y build producción con backend temporal |
| M `frontend/tests/visuales/verificar_e2e_offline.py`, M `frontend/tests/visuales/verificar_sync_offline.py` | Retirar supuestos v1/login fijo; mantener regresión visual/dev separada de gates producción |

## 6. Funciones puras y algoritmos críticos

Firmas conceptuales; pseudocódigo, **no implementación**. DTOs/repositorios de la sección de interfaces aportan tipos reales al crear tareas.

### Funciones puras backend

- `validar_porcentaje(valor: Decimal) -> Decimal`, `validar_importe_abono(importe: Decimal) -> Decimal`, `calcular_partes(precio: Decimal, porcentaje_barbero: Decimal) -> tuple[Decimal, Decimal]`: **interfaces exactas del paquete aprobado §2**, sin saldo ni efectos y contexto local protegido.
- `validar_abono(importe: Decimal, saldo: SaldoConocido, origen: OrigenOperacion) -> DecisionAbono`: función posterior fuera del primer paquete, reutiliza validación pura; online exceso rechaza, offline exceso revisa.
- `calcular_saldo(obligacion: Decimal | None, movimientos: tuple[MovimientoReconocido, ...]) -> Saldo`: unknown independiente, neto/estado/saldo/excedente.
- `limite_devolucion(fuentes: tuple[FuenteEfectivoCorregida, ...], devoluciones: tuple[ConsumoFuente, ...]) -> Decimal`: capacidad por fuente real/evidencia, sin sumar raw corregido ni fabricar dinero con compensaciones.
- `decidir_edicion(actor: Actor, corte: SnapshotCorte, cambio: CambioCorte, origen: OrigenOperacion) -> Decision`: titularidad/rol, bloqueo/pagos/cierre, anulado sin reactivación.
- `recalcular_snapshot(base_financiera: SnapshotFinanzas, cambio: CambioFinanciero, valores: ValoresActuales) -> SnapshotFinanzas`: RF-42/47, campos omitidos dentro del grupo desde base financiera coherente; no leer estado de llegada arbitrario. Método/fecha no invocan recálculo.
- `construir_candidatos(bases_inmutables: BasesPorUnidad, campos: CambioCorte, valores_financieros: ValoresActuales | None) -> tuple[CandidatoUnidad, ...]`; `comparar_lww(ganador_actual: VersionUnidad, entrante: CandidatoUnidad) -> GanadorUnidad`; `integrar_unidades(vigentes: SnapshotUnidades, ganadores: tuple[CandidatoUnidad, ...]) -> SnapshotUnidades`: solo unidades tocadas y permitidas, clave `(instante_cambio_utc, operacion_id)` por unidad, nunca fecha histórica ni recepción; finanzas íntegro. Autorización/terminalidad se resuelven antes, no mediante comparación LWW.
- `validar_momento(momento: datetime, origen: OrigenMomento, ahora: datetime) -> DecisionMomento`: manual admin futuro rechaza; automático >ahora+5min revisa; pasado no expira por atraso.
- `jornada_de(instante: datetime, zona: ZoneInfo) -> date` y `limites_periodo(periodo: Periodo, hoy: date, zona: ZoneInfo) -> IntervaloUTC`: cero dependencia del reloj global.
- `decidir_imputacion(jornada_real: date | None, cierres: EstadoJornadas, jornada_abierta_actual: date | None, hoy: date) -> DestinoImputacion`: conservar real/original, pending cuando falta destino, fecha desconocida no inventada.
- `proyectar_resumen(cortes: tuple[SnapshotPersonal, ...], movimientos: tuple[MovimientoPersonal, ...], cobertura: Cobertura, periodo: IntervaloUTC) -> ResumenPersonal`.

### Funciones puras frontend

- `pesosACentavos(texto: string) -> Resultado<Centavos, ErrorImporte>`; `centavosAPesos(importe: Centavos) -> DecimalTexto`; parse estricto y entero seguro.
- `porcentajeABases(texto: string) -> PorcentajeBases`; `estimarComision(precio: Centavos, bases: PorcentajeBases) -> Centavos`.
- `proyectarCorte(snapshotAceptado, operacionesLocales) -> VistaCorte`: separar valores aceptados/estimaciones, causas y movimientos sin descontar aceptados.
- `agruparComisiones(cortes, movimientos, periodo, cobertura) -> ResumenComisiones`: servicio y dinero por momentos propios, sin sumar unknown como due.
- `accionesDisponibles(contexto, corte, journalLocal) -> Acciones`: bloqueo local desde primer pago capturado; el servidor sigue siendo autoritativo.
- `validarFechaAdministrativa(instante, ahora)` y `coberturaDisponible(registros, pendientes, hoy, ultimaActualizacion)`.

Generación UUID, cifrado, lectura de reloj, red y DB son efectos inyectados. `ahora/hoy` se capturan una vez en frontera y se pasan; tests congelan esos valores. No usar `new Date()` disperso para decidir períodos/aceptación.

### A. Captura online/offline y resultado parcial

```text
contexto = capturar cuenta, rol conocido, generación, credencial y namespace
momentoReal = reloj inyectado (o fecha admin validada)
modoCaptura = online u offline conocido AL CAPTURAR; incluir en envelope/hash y nunca cambiar en retry
instanteCambio = captura automática del cambio, distinto de momentoReal editable solo admin
crear UUID corte y UUID operación; no reutilizar ID autoincremental local como ID servidor
validar catálogo disponible/activo, elección cobro y entradas
cobroCompleto = importe exacto del precio mostrado, NO precio futuro al sincronizar
preparar cifrado fuera de transacción IndexedDB
en una transacción local: guardar proyección provisional + operación corte + abono dependiente si existe
si falla persistencia: mostrar error; NO confirmar guardado
si éxito: mostrar guardado local/estimado; intentar enviar si hay conexión
aplicar resultado de cada operación, conservando identidades y cantidades
si corte aceptado y abono revisión: éxito solo del corte, causa/importe revisión del abono
si corte rechazo/revisión: conservar abonos dependientes SIN aplicar; informar subsanación
si cambió cuenta/generación: no actualizar UI/almacén activo; resultado recuperable al volver a cuenta original
```

### B. Aceptación idempotente y concurrencia monetaria

```text
para operación en orden topológico (dependencias faltantes/ciclo => conservar causa sin aplicar):
  abrir UoW limpia -> barrera técnica -> discovery -> TODO el orden global §3
  releer actor/destinatarios/servicio/saldos/cierres; autorizar (ajeno y no existe => mismo 404)
  consultar/insertar clave idempotente única; validar mismo payload/hash/modo original
  si hash distinto: conflicto de identidad, no escribir efecto ni reclasificar modo
  si estado terminal: devolver acuse persistido sanitizado, no reejecutar
  si estado revision: devolver causa o procesar SOLO resolución admin nueva vinculada
  si estado dependiente_sin_aplicar: reexaminar padres/vínculo de resolución de MISMO corte UUID
  si padre aún no habilitado: conservar causa dependiente, sin ledger, commit resultado actualizado
  si se habilitó: continuar con MISMA UUID/hash/origen y efecto único, no inventar nuevo pago
  validar momento real y timestamp automático de captura/cambio (>5min adelantado conserva revisión)
  validar valores recuperables; selección activa o excepción de desactivación offline
  leer precio/porcentaje ACTUALES bajo locks SOLO para aceptación inicial/recálculo autorizado
  si abono ordinario sobre anulado: rechazo
  si inválido o exceso online: rechazo persistido sin ledger
  si exceso offline/reloj adelantado/valores inexistentes: conservar revisión y payload real, sin saldo
  si aceptado: escribir snapshot/movimiento y saldo proyectable + auditoría + resultado idempotente
  aplicar imputación o pending-imputación; no confundir con revisión
  commit; responder datos definitivos de esa operación
```

Reintento **terminal** no recalcula corte ni dinero; reintento dependiente sí vuelve a examinar habilitación, sin mutar payload. Dos abonos distintos conservan UUIDs y validan saldo bajo protocolo global §3, incluido actor/destinatario/servicio y journal de devoluciones. No tomar locks de corte antes de jornada o barrera en ninguna ruta. Contención/busy/deadlock produce retry acotado con identidad/origen inmutables; no un segundo pago ni reclasificación online/offline.

Actor/rol se revalida al ejecutar, no con claim JWT. Un replay después de reasignación no devuelve snapshots revocados aunque el journal guarde el resultado original; devolver acuse seguro/justificante permitido, nunca el corte nuevo. La clave idempotente no es un permiso de acceso.

### C. Edición/anulación vs pagos/cierre y LWW

**Regla vigente aprobada (DA-11/RF-36/40/46):** anulación autorizada terminal, independiente del LWW; entre ediciones todavía permitidas, tres unidades de conflicto:

| Unidad | Candidato y metadata | Aplicación |
|---|---|---|
| `metodo` | Método explícitamente editado, base/version de esa unidad, clave cambio/UUID | Solo método; no tocar fecha, grupo financiero ni métodos de movimientos existentes |
| `momento_real` | Momento explícitamente corregido por admin, base/version de unidad, clave cambio/UUID | Solo fecha real; permisos/futuros/ajustes de jornadas validados, no recalcular precio/reparto |
| `finanzas` | Servicio/barbero/precio/porcentaje/reparto **íntegros**, base financiera/version, clave cambio/UUID, snapshot de valores actuales de aceptación | Reemplazar solo grupo financiero ganador coherente, con trazabilidad/obligaciones/asignaciones/ajustes RF-42/47; nunca ledger ni otras unidades |

Cliente envía campos explícitos y refs `base_version/bases_por_unidad`; servidor deriva unidades tocadas y reconstruye bases preservadas del **mismo corte autorizado**, no una versión de otro recurso/titular ni un snapshot libre proporcionado por cliente. Campo omitido de **otra unidad** no es candidato ni se copia de base sobre su ganador vigente: así una edición de método no restaura un servicio/fecha anterior. Campos omitidos **dentro del grupo financiero tocado** se heredan de su snapshot base coherente, no del estado que casualmente llegó primero; se construye **un** candidato financiero indivisible. Ejemplos: cambiar solo servicio conserva identidad de barbero de esa base y aplica precio/porcentaje actuales protegidos de servicio/profesional; cambiar solo barbero conserva precio de base y aplica porcentaje actual del nuevo; cambiar ambos aplica precio actual del servicio y porcentaje actual del destinatario. Sin precio/porcentaje manual cliente. Una edición solo de método/fecha ni construye candidato financiero ni recalcula o revierte su ganador.

Cada unidad mantiene máximo `(instante_cambio_utc, operacion_id)` entre candidatos autorizados/permitidos; desempate lexical UUID técnico. Actualizar revisión global/antes/después no sustituye las claves por unidad. Guardar candidatos, snapshots de valores actuales y resultado aplicado/omitido por unidad de la operación en **misma tx protegida**. Un perdedor no aporta partes financieras ni reejecuta en retry; un ganador ya aceptado conserva su snapshot, no se reconstruye con catálogo nuevo. Una operación puede ganar método y perder otra unidad: respuesta indica resultados por unidad, nunca borra journal. Base faltante conserva causa sin aplicar ni rellenar desde presente; reexaminarla sigue la máquina segura de dependencias §3.

**Convergencia de unidades (mismo conjunto permitido y snapshots de aceptación):** base S1/efectivo, E1(ts1) edita servicioS2, E2(ts2) edita método tarjeta. E1→E2 y E2→E1 conservan S2/reparto de candidato financiero E1 **y tarjeta E2**; ninguna operación pisa unidad ajena. Si E1 cambia servicio y E2 cambia barbero sobre la misma base financiera, ambos tocan finanzas: gana íntegro el candidato de mayor clave, incluso sus campos heredados de base; no combinar precio de E1 con porcentaje de E2. Con cambios externos de catálogo/rol/titularidad/pagos/cierre, la admisibilidad y los valores actuales se revalidan al aceptar: no prometer snapshots idénticos contra valores que realmente variaron entre aceptaciones. La convergencia no permite ignorar esos cambios de negocio.

**Convergencia A/E aprobada:** A anula(ts10), E edita(ts11), misma base activa, ambos actores autorizados y sin pagos/cierre intercalados. A→E: A valida y establece terminal; E conserva resultado/causa de corte anulado sin aplicar unidades ni reactivar. E→A: E aplica sus unidades permitidas; A vuelve a validar y establece terminal **aunque ts10 sea menor**, sin comparar A con claves LWW de edición. Estado final anulado y obligaciones conocidas canceladas en ambos órdenes; anteriores/candidatos realmente aplicados y snapshots previos permanecen trazables, no se falsifica historial para hacerlo byte-idéntico. Terminalidad se guarda fuera de unidades (`anulacion_terminal`, operación/autor/motivo/instante); editar nunca puede escribirla falsa.

No es «cualquier anulación siempre gana»: si A carece de permiso/titularidad o actor activo, no aplica; si A del barbero llega bloqueada por pago/cierre, RF-40 revisión offline o bloqueo online, **sin terminalizar**. Admin puede anular/corregir bloqueado con motivo y ajustes, respetando journal y cierre; sobre anulado solo ajustes/devoluciones administrativos trazables, no edición que reactive. Una anulación concurrente autorizada no traslada pagos ni permite al actor operar sobre otro titular. Estos controles usan actores/destinatarios/bases/corte/jornals del orden global §3 en **ambos órdenes**, incluidos admin gestión y admin personal, y privacidad de resultados/replay.

```text
usar barrera/discovery/orden global §3; autorizar titular/actor y releer bloqueo
si operación es replay terminal: acuse seguro, ningún recálculo ni transición nueva
si barbero y bloqueado:
  si operación offline edición/anulación: conservar revisión administrativa (RF-40)
  si online: informar bloqueo, no aplicar
  terminar operación sin aplicación automática
si admin corrige/anula bloqueado/cerrado: exigir motivo antes de aplicar; preparar antes/después/ajustes
si ya anulado: edición no aplica, abonos ordinarios prohibidos; solo correctivos admin permitidos
si anulación nueva autorizada:
  guardar terminal independiente de LWW, cancelar obligaciones conocidas y conservar unknown/journal
  auditar, ajustar si cierre; no comparar contra timestamp mayor de una edición
si edición permitida:
  validar base/versiones preservadas y derivar unidades tocadas
  para cada unidad tocada: comparar clave CAMBIO/UUID con ganador de ESA unidad
  si finanzas gana: candidato íntegro desde base financiera, valores actuales bajo locks RF42/47
  si solo método/fecha: no crear/recalcular/reescribir finanzas
  integrar únicamente unidades ganadoras; guardar aplicadas/omitidas y versiones/candidatos/auditoría
  nunca reemplazar movimientos distintos, claves de otra unidad ni estado terminal
ningún LWW reemplaza/elimina movimientos distintos; no hace devolución ni reasignación automática
```

Timestamp de cambio es automático e inmutable; corregir fecha histórica solo compite en `momento_real`, no altera clave LWW a fecha del corte. El movimiento que inicia bloqueo puede aceptarse, pero no habilita edición/anulación posterior prohibida. Journal append-only se conserva fuera del estado editable, con excedentes/devoluciones y asignaciones por profesional del plan global. DA-11 dejó de ser bloqueante; implementar ese algoritmo sigue fuera del primer paquete aprobado.

### D. Revisión monetaria, compensación, anulación y reasignación

```text
admin resuelve operación pendiente con nueva UUID/motivo/evidencia; bloquear según §3
si exceso representa dinero real: reconocer importe íntegro original
  aplicar hasta obligación y proyectar resto excedente, sin generar devolución
si registro erróneo: conservar original + compensación vinculada con motivo
  si original ya aceptado: delta = reconocido corregido objetivo - reconocido actual documental
  si original revisión sin base reconocida: reconocer base original + delta en UNA transacción
  evidenciar efectivo real corregido por fuente; NO aplicar delta negativo a una base inexistente
  no inventar devolución; resultado conserva importe original/efectivo corregido/refs separados
si devolución explícita: asignar consumo por fuente real corregida, validar cap bajo locks y registrar salida
si anula: obligación conocida cliente/comisión = 0; unknown sigue unknown
  dinero permanece, excedente visible; no reactivar ni nuevos abonos ordinarios
si reasigna:
  cerrar asignación anterior y conservar journal de profesional anterior
  nueva asignación con precio anterior y porcentaje actual (o precio nuevo si cambia servicio)
  no mover abonos anteriores; saldo de nueva comisión independiente
  revocar acceso al corte para anterior; generar revocación local y justificante sanitizado
auditar y generar ajustes referenciados si hay cierre; resolución idempotente
habilitar dependientes solo mediante vínculo validado padre/resolución/MISMO corte UUID
```

Un abono/compensación conocido sobre un histórico no completa por sí solo toda evidencia desconocida. La resolución histórica explicita qué concepto se completa y qué fechas tienen evidencia; no falsear fecha con el momento del registro administrativo.

### E. Cierre/tardíos e imputación

```text
cerrar jornada: barrera -> discovery -> usuarios/servicios/jornadas/cortes/asignaciones/journals/resto §3
  capturar snapshot de servicios y dinero, vincular cortes de jornada real y aceptar cierre una vez
aceptar corte tardío: si jornada servicio ya cerrada
  conservar fecha, vincular mediante ajuste posterior, bloquear para barbero
aceptar movimiento:
  calcular jornada real con su instante
  si jornada real existe abierta: imputar allí; sin fila no significa abierta
  si jornada real cerrada: ajuste al destino abierto actual
  si destino requerido no existe: aceptar dinero, imputación pendiente, saldo reconocido
abrir/imputar admin:
  barrera/discovery/orden global (no empezar por pendiente/destino fuera de orden)
  apertura solo comando admin; ausencia de fila conserva pending hasta ese comando
  escribir referencia única de imputación; no insertar otro abono
  no cambiar totales/snapshot del cierre original
corregir fecha de corte o momento real de movimiento después de cierre:
  conservar original y evento administrativo de corrección, validar no futuro
  ajustes referencian origen y destino; no mover snapshot original ni duplicar saldo
```

### F. Cuenta, pull y cache local

```text
antes de enviar, capturar actor/generación/token/namespace; payload no puede autodeclarar otro actor
rehidratar offline desde slot activo durable y vault propio, sin requerir nueva auth de red
adquirir lease local por cuenta (multi-tab), sin guardar token en outbox
enviar operaciones no terminales habilitables con mismas UUIDs/hash/modo original, fuera de tx Dexie
antes de procesar respuesta/error, comprobar generación y cuenta
si cambió: descartar actualización visible; nunca usar token nuevo para un envío antiguo
persistir resultados definitivos y mapping UUID->ID en almacén de cuenta original solo si autorizado
bajar manifest snapshot autorizado de revisión S, páginas keyset del MISMO snapshot
por página, servidor revalida actor/titularidad ACTUALES; si scope cambió invalidar snapshot y no enviar ajenos
aplicar inmediatamente revocaciones recibidas y retirar detalle/cache/query de recursos revocados, aun si snapshot falla
staging local cifrado, no mezclar páginas con revisiones distintas ni publicar total definitivo
finalizar snapshot con barrera T: aplicar cambios/revocaciones (S,T] + resumen/cobertura a revisión T
procesar revocaciones primero, reemplazar proyección/staging/mapping en tx local de esa cuenta/generación
solo tras terminar manifest y finalización marcar cobertura completa/última actualización T
fallo/expiración/scope cambiado: conservar solo copia previa todavía autorizada, descontando revocaciones ya recibidas
si cambió scope y aún no se puede verificar autorización de una parte, no exponer esa parte hasta revalidación
mantener cobertura incompleta/fecha anterior y reintentar; no restaurar detalles revocados desde staging
logout/cambio: primero tx durable invalida generación y elimina slot/key; abortar red y cerrar lease/DB
  después limpiar QueryClient/memoria/Zustand; otras tabs avisan por canal y verifican slot al reanudar
conservar pendientes cifrados de cuenta anterior; desbloquear solo al autenticar ese titular
```

Límite físico offline: no puede conocerse una reasignación remota hasta recuperar conexión. Al recibirla, retirar detalle y datos nuevos; no prometer revocación instantánea en un equipo totalmente desconectado. No exponer datos de otra cuenta en el mismo dispositivo siquiera leyendo sus stores plaintext.

**Snapshot/cursor consistente:** al iniciar pull, bajo barrera transaccional capturar revisión monotónica S y materializar IDs y DTOs autorizados propios (90 días+abiertos+pendientes+justificantes) y resumen/cobertura del mismo corte de datos. No conservar una transacción HTTP abierta durante todas páginas ni paginar tabla viva por OFFSET/fecha mutable. Cursor opaco liga actor/contexto/namespace/manifest S y última clave estable; expiración obliga a reiniciar sin declarar cobertura completa. Manifest server es efímero, con purga/versionado, no journal financiero duplicado ni un cache público.

Antes de cada página y finalización revalidar rol/activo/titular actual bajo barrera: si una reasignación/degradación invalida el manifest, devolver invalidación segura y revocaciones del scope previamente autorizado, **no DTO de corte revocado aunque figure en snapshot S**. De otro modo, finalizar con deltas/changelog hasta revisión T y resumen consistente T; si el delta precisa paginación, fijar T/materializar deltas y repetir misma validación, no usar un watermark móvil infinito. Cliente no mezcla aceptación de nuevas escrituras en su conjunto S/T sin reconciliar UUID/versiones y conservar outbox.

Tombstone lleva referencia opaca de recurso previamente visible y causa genérica; no nuevo titular ni datos posteriores. Cada revocación recibida se aplica sin esperar finalización del manifest: invalida detalle/cache/QueryClient en la cuenta correspondiente, incluido staging, aunque la descarga posterior falle o expire. Solo puede conservarse copia anterior todavía autorizada; invalidar un scope obliga a ocultar lo no revalidado hasta actualizarlo. No borrar outbox/justificantes propios ni devolver datos del nuevo titular al retirar el detalle. Revocaciones se conservan fuera de la ventana90 y requieren cursor continuo; si expiró retención, pedir resnapshot completo del scope y eliminar caches que ya no estén autorizadas, sin borrar pendientes sin resultado. Solo la finalización completa acredita cobertura **a fecha/revisión T**, no actualidad física perpetua ni totalidad histórica fuera del conjunto local. Pruebas intercalan pagos, cambio de fecha y reasignación entre páginas y fallo antes de finalizar; sumas/resumen/manifest deben representar un mismo corte de datos permitido y ningún rollback local restaurará información revocada.

## 7. Interfaces HTTP y tipos

### Contexto y privacidad

| Contexto | Consulta y mutación permitida | Proyección |
|---|---|---|
| Barbero personal | Cortes vigentes propios; movimientos sobre los propios autorizados; justificantes de su journal anterior | DTO personal sin bruto/costos/márgenes/datos de otro profesional; 404 ajeno idéntico a inexistente |
| Admin personal | Exactamente filtro `actor.id`, aun teniendo rol admin | Mismo DTO personal y resúmenes propios |
| Admin gestión | Registro/revisión/correcciones/fecha/barbero/evidencia/cierre según spec | DTO gestión explícito; no reutilizarlo en cache personal |

Filtrar en SQL antes de paginar/agregar. Mensajes de errores, hash de operación, audit antes/después, IDs de dependencia y tombstones no deben revelar nuevo titular o existencia de recurso ajeno. Autor de un pago es trazable en servidor; justificante personal no expone identidad de otro profesional innecesariamente.

### Rutas conservadas y nuevas propuestas

Todas bajo `/api`; entradas/salidas Pydantic; OpenAPI **a comprobar en implementación**, no validado en esta fase. Registrar rutas estáticas antes de rutas de IDs.

| Método / ruta | Contrato y autorización |
|---|---|
| POST `/cortes/` | Body legacy `servicio_id/metodo_pago` válido; nuevos campos opcionales UUID/operación y destino/fecha solo admin. Respuesta corte compatible; cobro inicial se envía como operación separada dependiente, no campo booleano |
| GET `/cortes/`, GET `/cortes/{id}` | Mantener listado admin y detalle compatible filtrado; 404 uniforme para barbero ajeno |
| GET `/cortes/mi/historial`, GET `/cortes/mi/resumen/{dia,semana,mes}` | Mantener shape legacy y filtro propio, admin incluido |
| GET `/cortes/mi/historial-v2` | `{items: CortePersonal[], cursor, cobertura, ultima_actualizacion}`; filtros fecha/servicio/estados, propio exclusivamente |
| GET `/cortes/mi/acumulados?periodo=dia|semana|mes|total` | `ResumenPersonal`; confirmada/estimada local/pagada/pendiente/desconocidos separadas; información de cobertura |
| GET `/cortes/mi/justificantes` | Journal propio previo a reasignación; sin acceso al detalle posterior ni datos nuevo titular |
| GET `/cortes/mi/{id}/detalle` | CortePersonal y movimientos filtrados; no autoriza corte revocado |
| PATCH `/cortes/{id}`; POST `/cortes/{id}/anular` | UUID/modo/instante cambio/base global+bases por unidad/campos explícitos/motivo; merge por método/fecha/finanzas coherentes, anulación autorizada terminal §6.C; resultados por unidad y snapshot aceptado. No fullrecord/DELETE/reactivate |
| GET/POST `/cortes/{id}/movimientos` | Body movimiento ordinary con concepto/importe/método/UUID/momento automático o admin; corte propio/admin gestión. Correctivos separados |
| POST `/movimientos-corte/{id}/compensaciones`, POST `/movimientos-corte/{id}/devoluciones` | Solo admin; original, motivo/evidencia, importe/signo correctivo validado y profesional original |
| POST `/movimientos-corte/{id}/correcciones-momento` | Solo admin; instante real corregido no futuro, motivo/evidencia, operación UUID; conserva original y saldo, registra ajustes de imputación si corresponde |
| POST `/cortes/{id}/evidencia-financiera` | Admin completa concepto desconocido; evidencia y fecha real documentada o desconocida explícita; autor/registrado UTC |
| GET `/cortes/gestion/historial`, GET `/cortes/gestion/{id}/detalle` | Admin, DTO gestión explícito, sin transformar `/mi` en global |
| GET `/revisiones-cortes/`, POST `/revisiones-cortes/{id}/resolver` | Admin, resolución typed con operación UUID propia, reconocimiento íntegro o compensación documentada; nunca reducción silenciosa |
| POST `/sync/` | Envelope compatible ampliado con modo/hash estable; resultados individuales y estado terminal/no terminal; dependiente reexaminable sin retarget, revisiones solo resolución autorizada |
| GET `/sync/cortes?cursor=…`, POST `/sync/cortes/finalizar` | Manifest propio revisiónS y finalizaciónT conforme §6.F; cursor actor/scope, revocaciones autorizadas, resumen/cobertura consistentes; gestión contexto admin explícito |
| POST `/jornadas-caja/abrir`, GET `/jornadas-caja/actual` | Solo admin; fecha negocio/motivo si procede e ID operación; no abrir por sync automáticamente |
| POST `/jornadas-caja/{id}/cerrar` | Admin, inputs caja reales exactos, snapshot computado por servidor, identidad idempotente |
| GET `/jornadas-caja/{id}/resumen`, GET `/jornadas-caja/pendientes-imputacion` | Admin, separar servicios de movimientos y ajustes |
| POST `/jornadas-caja/{id}/imputaciones` | Admin imputa movimientos ya aceptados, referencias únicas sin abono nuevo |
| GET/POST `/cierre-caja/`, GET detalle/resumen existentes | Adaptadores compatibles; nuevos cierres enlazan jornada y snapshot sin reescribir históricos |
| GET `/auth/contexto-local` | Solo titular autenticado activo, clave de desbloqueo/versión propios; `Cache-Control: no-store`, sin logs/body telemetry |

No aceptar barbero_id/precio/porcentaje del cliente como autoridad. `momento_real` automático offline se conserva y se valida, no habilita edición manual al barbero. Nuevos cuerpos rechazan campos extra monetarios/identidad no permitidos; legacy mantiene su mínima compatibilidad documentada.

### Tipos conceptuales compartidos

```text
MetodoPago = efectivo | tarjeta | transferencia
UnidadCambio = metodo | momento_real | finanzas
ClaveCambio = { instante_cambio_utc, operacion_id }
VersionUnidad = { referencia_snapshot, clave_ganadora }
BasesPorUnidad = { metodo?: ReferenciaBase, momento_real?: ReferenciaBase, finanzas?: ReferenciaBase }
ResultadoUnidad = { unidad, aplicada, causa?, version_unidad, snapshot_aceptado_ref? }
SnapshotFinanzas = { servicio_id, barbero_id, precio, porcentaje_aplicado, parte_barbero, parte_barberia }
Concepto = cliente | comision
EstadoOperacion = pendiente_envio | aceptada | rechazada | revision | dependiente_sin_aplicar
                  | resuelta
ModoCaptura = online | offline (inmutable por UUID)
EstadoImputacion = imputada | pendiente_imputacion
Saldo =
  { conocimiento: desconocido, neto_documentado?: DecimalTexto, evidencia_incompleta: true }
  | { conocimiento: conocido, obligacion, neto, restante, excedente: DecimalTexto,
      estado: pendiente | parcial | pagado }
Operacion = { version_protocolo, operacion_id, namespace_cliente, accion discriminante,
              modo_captura, instante_cambio_utc, momento_real?, base_version?, bases_por_unidad?,
              depende_de[], referencia_original?, datos typed }
Resultado = { id, accion, aceptada, status_code, estado, terminal_financiero, causa?, notificacion?,
              recurso_autorizado?, mapping?, version?, estado_imputacion?, dependencias[],
              resolucion_id?, importe_original?, efecto_reconocido_corregido?, resultados_unidades? }
PaginaPull = { manifest, revision_snapshot, items_autorizados, cursor, completa: false }
FinalizacionPull = { manifest, revision_final, deltas, revocaciones, resumen, cobertura, completa }
CortePersonal = { id, uuid, servicio, momento_real, metodo_pago, porcentaje_aplicado,
                  comision, anulacion, sincronizacion, bloqueo_y_acciones,
                  saldo_cliente, saldo_comision, version, versiones_por_unidad }
JustificantePersonal = { uuid, concepto, tipo, importe, metodo, momento_real?,
                         referencia_propia, estado, excedente_propio }
ResumenPersonal = { periodo, cortes_vigentes, comision_confirmada,
                    comision_pagada, comision_pendiente_conocida,
                    cantidad_conceptos_desconocidos, dinero_por_momento,
                    ajustes_imputacion_separados, cobertura }
```

`SnapshotFinanzas` es tipo **interno/gestión**, no body de edición ni un DTO personal nuevo que exponga parte_barberia: salida personal por unidad se sanitiza conforme §7 y referencias a versiones previas no revelan otro titular. `anulacion` en respuesta se proyecta desde transición terminal servidor, nunca se acepta `anulado:false` de una edición. `DecimalTexto` se conserva hasta codec; frontend derivado usa Centavos/PorcentajeBases. Estimadas/locales no son dinero aceptado. Históricos sin fecha evidenciada aparecen en «fecha desconocida», no en el período de su registro administrativo; el total explicita cobertura temporal. Motivos/códigos typed no repiten lógica financiera. Rechazo/401 tardío de A no desloguea B.

## 8. Interfaz UX y props

- `/cortes`: servicio por tarjetas existente, método propuesto, comisión estimada previa a aceptación; selección explícita de cobro pendiente/parcial/completo (sin default), importe parcial, método del cobro independiente. Admin elige propio/otro y fecha; no precio/porcentaje históricos. Instantánea del precio mostrado determina el cobro «completo» real offline.
- `/cortes/historial`: propio para ambos roles; tabs día/semana/mes/total, servicio/fecha local y porcentaje aplicado; saldos de cliente/comisión separados. Anulado permanece visible sin devengado vigente. Banner de cobertura/última actualización y totales incompletos.
- `/cortes/:id`: detalle propio, acciones disponibles con explicación del bloqueo; movimientos ordenados con importe/método/instante propio, abonar parcial/restante por concepto. Pendientes/revisión/rechazos aparte de reconocidos; edición de cobro genera movimiento, no un booleano de pagado.
- `/cortes/gestion`: acceso solo admin, historial de terceros y revisión con motivo/evidencia; cambio servicio/fecha/barbero, compensación/devolución, completar históricos. No es módulo genérico de reportes. Admin puede cambiar a vista personal y cache/filtros se aíslan.
- Justificantes anteriores visibles en historial propio como sección separada, sin enlace a corte reasignado; admin puede regularizar journal original sin confundir nuevo profesional.
- CierreCaja: indicar jornada abierta/cerrada, servicios realizados y dinero efectivamente cobrado/pagado por separado; pendientes de imputación con solicitud de apertura y acción administrativa, sin «reabrir cierre».
- Toast de éxito solo al resultado aceptado de esa operación; guardado local anuncia pendiente, revisión expresa causa e importe real. Resultado parcial mantiene formulario/identidades para recuperar, sin repetir un corte aceptado.
- Estados loading/empty/error/blocked/offline con kit 001; modal accesible/foco y confirmación anulación, targets táctiles y contraste; validar error inline antes de envío. Font Archivo self-hosted también precacheada.

Props propuestas (tipos de dominio, no `any`):

| Componente | Props |
|---|---|
| `FormularioMovimiento` | `corte: CortePersonal`, `concepto: Concepto`, `saldo: SaldoCentavos`, `metodoPropuesto: MetodoPago`, `contexto: ContextoCuenta`, `ahora: InstanteUTC`, `onConfirmar(EntradaMovimiento): Promise<ResultadoOperacion>`, `onCancelar()` |
| `FormularioCorreccion` | `corte`, `acciones: AccionesPermitidas`, `contexto`, `catalogo: CatalogoVenta`, `profesionales?: ProfesionalGestion[]` (solo admin), `ahora`, `onConfirmar(CambioCorte)` |
| `SaldosCorte` | `cliente`, `comision`, `movimientosNoAceptados`, `imputacion`; unknown es discriminante, no `0` |
| `EstadoOperacion` | `resultado`, `importeReal?: Centavos`, `onReintentar?` (misma operación), `onRevisar?` (admin) |
| `ResumenComisiones` | `resumen`, `estimadas: Centavos`, `cobertura`, `periodo`, `onPeriodoCambio(Periodo)` |

## 9. Decisiones técnicas justificadas

| Decisión | Justificación / alternativa descartada |
|---|---|
| Journal append-only + asignaciones por profesional | Permite correcciones, excedentes, reasignaciones y justificantes; dos flags «pagado» o sumar por titular actual pierde dinero/titularidad |
| Unidad transaccional por operación | Idempotencia/saldo/auditoría coherentes; descartar transacción todo-o-nada corte+pago, no exigida por RF-57 y ocultaría aceptación parcial |
| LWW por unidades + anulación autorizada terminal | DA-11/RF36 aprobados: método/fecha independientes, finanzas como grupo indivisible y terminal fuera de LWW. Descartar candidato fullrecord, merge financiero por campos sueltos, prioridad terminal que eluda pagos/cierre o reactivación |
| Barrera + único orden global de locks | Protege valores actuales, cierre/aceptación/devoluciones y ausencia de jornada; descartar órdenes locales corte→jornada vs jornada→corte o writers catálogo/usuarios que no participan |
| Terminalidad explícita / resolución vinculada | Replay de un dependiente puede habilitarse una vez; descartar devolver para siempre el primer resultado pendiente, mutar su payload o aplicar pago a corte distinto |
| Origen de captura inmutable | RF38/41 no cambian por retry; descartar reclasificación por conectividad del momento de respuesta |
| Clave UUID + hash canónico persistido | Reintentos y pérdida de respuesta no recalculan/duplican; descartar ID autoincremental Dexie como identificador global |
| Decimal en dominio, enteros en almacenamiento y frontend | Exactitud SQLite y ARS; descartar floats/parseFloat/sumar `Numeric` SQLite como autoridad nueva |
| Estados aceptación e imputación ortogonales | RF-50 reconoce dinero aun sin jornada abierta; descartar un único estado «pendiente» que descuente/ignore dinero incorrectamente |
| Cierre snapshot + ajustes vinculados | Mantiene originales/tardíos; descartar recalcular/reabrir cierres o convertir devengado en cobrado |
| API personal y gestión separadas | Admin personal también aislado, DTO no excesivo; descartar respuesta global filtrada en React |
| Dexie única outbox durable; React Query lecturas | React Query no está instalado; añadir dependencia compatible React18, acotada a 002, conforme AGENTS. Descartar cola de mutaciones persistidas React Query y BackgroundSync Workbox paralelas: duplicarían reintentos, credenciales y fuente financiera |
| Cache por cuenta con payload sensible cifrado | Slot activo durable permite recarga/reapertura offline, sin mapa de claves anteriores; cuarentena ambigua requiere custodia operativa aparte, **no basta nombrarla protegida**. Descartar perder pendientes al logout o cifrar ambiguos con clave de B |
| Clave local recuperable por titular | Sesión activa recupera CryptoKey local sin auth nueva offline; tras logout/relogin conectado titular obtiene versiones propias del servidor. Descartar key solo en memoria (perdería reapertura), password como única key, tokens outbox o endpoint admin que exponga otras claves |
| Capacidad de devolución por fuente corregida | Registrado100/real50 implica cap50; base documental+compensación+evidencia transaccionales para pendientes erróneos; descartar sumar raw100, restar−50 sobre base0 o devolver ficticiamente la diferencia |
| Manifest pull materializado + finalización | Mantiene revisión consistente y revalidación de titular cada página; descartar OFFSET de tabla viva/mezclar páginas como «total» y snapshots que devuelven revocados |
| Sin cache HTTP de API autenticada | Reduce fugas/revocaciones tardías; descartar `NetworkFirst` compartido para auth/datos financieros. Offline usa Dexie scoped, no service worker como servidor de saldos |
| Baseline + expansión Alembic | Repetible en DB nueva/existente; descartar create_all como migración, recalcular históricos o asumir cobros por método |
| Instante de cambio UTC + desempate UUID estable | Desempata cada unidad entre ediciones permitidas, no fecha del corte. Anulación se valida y terminaliza independientemente conforme RF36, aunque timestamp menor; retry recupera snapshot aplicado sin recalcular |

### Evidencia Context7 consultada (2026-10-05)

- `/websites/dexie`: `https://dexie.org/docs/Dexie/Dexie.version()` y `Dexie.PrematureCommitError`: upgrade y transacciones, no red/crypto async externa dentro. Docs sin versión fijada, **no prueban structured clone/recuperación de CryptoKey en todos los navegadores objetivo**; probar sobre Dexie3.2.7 + navegador real. No upgrade a Dexie4.
- `/websites/sqlalchemy_en_20`: `https://docs.sqlalchemy.org/en/20/dialects/sqlite.html`: driver Python 3.11 usa control legacy de BEGIN; hooks permiten BEGIN explícito, DDL/SELECT pueden no participar como se espera. Sustenta unidad dedicada y prueba de `BEGIN IMMEDIATE` en versiones fijadas; no extrapolar autocommit Python 3.12 a 3.11.
- `/tanstack/query/v5.60.5`: docs `guides/mutations.md`, `reference/QueryClient.md`: mutaciones offline persistidas requieren funciones tras reload; clear limpia caches. Evidencia para descartar segunda cola, no aislamiento por sí sola. Verificar peer **React18.3.1/TS5.9.3** y fijar nueva versión compatible durante paquete autorizado; no seleccionar último major ni actualizar stack existente.
- `/vite-pwa/docs`: precache/generate-sw `globPatterns`, denylist y NetworkOnly; docs **no versionadas a 0.17.4/0.17.5**. La versión resuelta es **0.17.5**, no el rango declarado ^0.17.4. Probar opciones/activación/cache antigua sobre esa versión/build real; evidencia documental no demuestra compatibilidad ni tests verdes.
- Consulta adicional `/tanstack/query/v5.60.5` (installation/typescript) no aportó por sí sola los límites peer/engines. Metadata exacta read-only de `https://registry.npmjs.org/<paquete>/<versión>` aportó los candidatos de §5: React Query5.60.5, Vitest2.1.9, TestingLibraryReact16.1.0/DOM10.4.0, jsdom24.1.3/fake-indexeddb6.0.0. Son declaraciones de paquetes, no resultado de instalación/pruebas; no se cambió ningún lockfile ni dependencia.
- `/pytest-dev/pytest` (plugins) confirma distinción autoload/env vs plugins explícitos; docs actuales muestran flag `--disable-plugin-autoload` añadido en8.4, **no usarlo en7.4.3**. Verificación read-only adicional del source versionado `https://raw.githubusercontent.com/pytest-dev/pytest/7.4.3/src/_pytest/config/__init__.py` y `src/_pytest/main.py` confirmó variables PYTEST_DISABLE_PLUGIN_AUTOLOAD/PYTEST_PLUGINS/PYTEST_ADDOPTS y opciones --noconftest/--confcutdir del comando futuro §2. No se ejecutó pytest ni se importó la app para comprobarlo.

No se modificó configuración MCP ni se enviaron secretos a documentación.

## 10. Estrategia de tests rojo → verde y seguridad de ejecución

Para cada futura tarea pequeña: escribir assertion que falle por ausencia de capacidad/regla, ejecutar rojo en fixtures, implementar mínimo, ejecutar verde y regresión relevante, guardar evidencia y parar. No marcar RF cubierto con un screenshot o solo una función mockeada.

Harness backend global futuro: DB temporal por prueba; Decimal/UTC; app sin DDL al importar; overrides limpiados al finalizar; concurrencia con **dos conexiones independientes y barreras**, no la misma Session. Migraciones con schema legacy manual sintético; PostgreSQL efímero, nunca `DATABASE_URL` real. **Paquete monetario cerrado no usa ese harness**: exclusivamente comando aislado §2 y test_dinero_cortes_aislado. No correr la suite actual que importa DDL real; la estrategia futura requiere aprobación y aislamiento previos.

Harness frontend: Vitest compatible Vite5, Testing Library, fake-indexeddb para lógica y componentes; navegador real para constraints IndexedDB, WebCrypto, SW y navegación offline. Los mocks no prueban upgrade real ni cierre/reapertura offline.

### Grupos de evidencia

- **U1 — Dinero/reparto**: primer paquete solo tres firmas exactas §2; validar retornos Decimal sin normalizar/as_tuple conservado, 0/100 % y porcentaje−0.00 admitido, abono±0 rechazado, no-Decimal/NaN/sNaN/Infinity y precisión>2 rechazados en español. Precio canónico cero/nonnegative/exacto y grande representable sin tope nuevo. Ejemplos0.08×30%=0.024→0.02 y0.05×50%=0.025→0.03, resto y suma exactos. Caller prec2/rounding distinto/traps Inexact/Rounded/Emin/Emax alterados: resultado válido idéntico y todos parámetros/flags caller íntegros tras éxito/excepción. Prueba import/scope sin main/DB. Frontend cents y límites persistentes se probarán **en paquetes posteriores**, no dentro del puro ni como cobertura ya lograda.
- **U2 — Dominio financiero/correcciones**: saldo known/unknown, pagos parciales independientes, netos/compensaciones/excedentes/devoluciones, anulación, cambio solo método/fecha/servicio/barbero y combinado; no transferir pagos.
- **U3 — Tiempo/períodos/políticas**: medianoche AR/semana lunes/fin mes, fecha local vsUTC, admin futuro/retroactivo, reloj+5min vs>5min. Fecha corregida no altera prioridad de cambio. LWW por método/fecha/grupo coherente: mismas operaciones permitidas en dos órdenes conservan independientes y financiero ganador íntegro; anulación autorizada ts10 frente ediciónts11 ⇒ anulado en ambos órdenes, sin reactivar, con obligaciones conocidas canceladas y journal intacto. No sustituir estos por asserts de bytes idénticos de auditoría real.
- **I1 — Contratos/registro**: bodies/rutas viejos, valores actuales iniciales, snapshots inmutables, destino admin/propio, servicio desactivado durante offline, información inexistente preservada, timestamps reales y DTOs.
- **I2 — Privacidad/rol/titular**: 404 idénticos recurso ajeno/inexistente, enum/subrecursos/errores no filtran; campos prohibidos ausentes en JSON de todos endpoints/pull/sync; admin `/mi` propio; cambio DB de rol/activo, clave local solo propia, reasignación/replay no filtra titular nuevo.
- **I3 — Finanzas**: cliente30+70/comisión10+40 sobre100/50; independencia; exceso online vs offline con modo inmutable en retries y payload conflictivo; real100 contra obligación80 ⇒ saldo0/excedente20; original aceptado100 corregido real50/comp−50 ⇒ neto/cap50; **pendiente100 corregido real50 ⇒ base100+comp−50 atómicas y neto/cap50, nunca−50**; comp/evidencia no contadas dos veces, devoluciones por fuente y errores sin devolución implícita; offline completo100/precio120 ⇒ saldo20.
- **I4 — Correcciones/journal/históricos**: primer parcial y cierre bloquean; admin motivo; anulado no devenga, obligaciones conocidas canceladas, unknown conservado; corrección errónea no borra original ni devuelve dinero; reasignación con pagado al anterior, excedente A y saldo independiente B, justificantes A; evidencia histórica fechada/desconocida.
- **I5 — Operaciones**: respuesta perdida/mismaUUID simultánea/hash distinto; hijo primero dependiente, padre se acepta o resuelve después, **replay hijo reevalúa y ejecuta una sola vez**; resolución/subsanación UUID nueva enlaza corte original inmutable, padres rechazados no se autoabren, retarget/hash/mode alterados rechazados; misma resolución/replay concurrentes sin duplicar; terminal aceptado no recalcula, reviews no autoaplican, parciales visibles; recursos ausentes conservados.
- **I6 — Concurrencia**: abonos/devoluciones misma fuente/saldo; precio/porcentaje/rol/activo cambian durante aceptación; cierre vs registro/pago/corrección/apertura. Instrumentar mismo orden §3 en writers usuarios/servicios/admin/legacy, sin decisión de aceptación preguard ni BEGIN anidado; dos conexiones SQLite/PostgreSQL efímeras. Permutar ediciones método+servicio, fecha+finanzas y dos financieros desde bases/versiones preservadas: independientes conservados, candidato financiero completo sin mezcla, retry no recalcula valores aceptados. A(ts10)/E(ts11) autorizadas sin pagos/cierre ⇒ terminal en ambos órdenes; luego casos actor desactivado/titular ajeno/pago/cierre bloquea A del barbero ⇒ NO forzar anulación, revisión offline RF40. Admin con motivo corrige/anula bloqueado mediante ajuste y journal preservado; admin personal sigue scoped. Cambios externos no justifican prometer los mismos valores actuales entre momentos de aceptación distintos.
- **I7 — Jornadas/cierres**: cierre original hash idéntico tras corrección/anulación/cambio fecha/barbero, corrección administrativa de momento de movimiento conserva original y no duplica saldo, tardío de jornada cerrada bloqueado, movimiento real cerrado a ajuste abierto, sin abierta financiero reconocido+pending, imputar tras apertura una sola vez, agrupación servicio/dinero distinta y evidencia de fecha desconocida fuera de períodos fechados.
- **I8 — Migración/rollback**: DB vacía/legacy/parcial, upgrade dos veces; raw SQLite con >2 decimales que ORM habría ocultado ⇒ diagnóstico sin quantize reparador; precisión REAL dudosa preservada; corte comparte fecha de cierre legacy sin evidencia ⇒ **no inferir pertenencia/bloqueo**; snapshots intactos/unknown, no abonos inventados; huérfanos/duplicados diagnosticados, copia restaurable sin pérdida post-upgrade.
- **F1 — Codecs**: Decimal string↔cents no floats, `id`/UUID/cadenas que parecen números no transformadas recursivamente, porcentajes/bounds; errores y formato no alteran monto.
- **F2 — Proyecciones**: aceptado distinto estimado, movimientos review/rejected/pending no reducen saldo, pending-imputación sí; unknown no suma due; coverage paginada incompleta/90 días+abiertos+pendientes y períodos por momento correspondiente.
- **F3 — Persistencia/cuenta**: slot activo/CryptoKey durable antes de guardar; reload y **cerrar/reabrir navegador offline** desbloquea mismo titular sin auth nueva; key/storage fallo no confirma; logout cambia generación y elimina key persistida ajena mientras conserva ciphertext; tabs suspendidas/retomadas revalidan slot; v1 owner ambiguo no cifrado a B, metadata sin datos personales, recuperación/copia/hash antes de purga; catálogo fallido conserva válido. Browser real, no solo mocks de clave.
- **F4 — Sync/transporte**: lease/retry mismo UUID/hash/modo, hijo pasa de dependiente a aceptado una vez tras padre/resolución, auth capturada y respuestas/401 tardíos A no mutan/desloguean B; páginas mismo manifest/S, cambio fecha/pago/reasignación entre páginas provoca delta/invalida seguro, expirar cursor no anuncia cobertura completa; finalización/revisiónT/revocación preceden exposición, no detalle posterior en justificante A.
- **F5 — UI**: pendiente/parcial/completo sin opción preseleccionada; importe realmente capturado; método propio; fecha admin no barbero; unknown/excedente y causa/bloqueo; motivo y accesibilidad de modal/errores; resultado parcial no toast éxito completo.
- **E1 — Registro/historial**: dos roles, online/offline, valores cambiados, retroactivo, períodos/datos visibles/privacidad; pruebas mobile y desktop 001.
- **E2 — Finanzas/correcciones**: abonos ambos conceptos, bloqueo primer parcial, admin corrige/anula/devuelve/reasigna y antiguos justificantes, revisiones/histórico desconocido.
- **E3 — Offline producción/cuentas**: build/SW/backend temporal, auth A y slot/clave durable, cortar red y **recargar ruta profunda, cerrar/reabrir navegador con perfil persistente**; usar datos y guardar pendientes sin nueva auth. A→B en vuelo/cierre sesión con tab suspendida, inspección metadata/ciphertext/keyslot; caída postcommit, origen estable, padre resuelto desbloquea hijo una vez. SW nuevo elimina api-cache previa sin borrar clave/outbox; cuarentena v1 sin custodia impide rollout y no pierde original. Comprobar red/almacenamiento, no solo pantalla; en entorno sintético, no claves/datos reales.
- **E4 — Jornadas**: corte ayer sync hoy con cierre ayer, pago posterior/ajuste, sin jornada abierta, apertura/imputación, cierre original intacto y saldos propios; horario Buenos Aires controlado.

Build/typecheck y pytest global serán gates de entregas integradas **tras aislar su harness**; primer paquete solo gate puro aislado. npm actual no tiene lint/test: no reclamar «lint pasó», añadir runner/script solo en paquete de frontend autorizado y verificar compatibilidad con versiones lock resueltas (sin actualizar stack). Mantener visuales001; suite nueva usa fixtures, no credenciales reales/hardcodeadas ni sleeps como evidencia. Nada de esta estrategia fue ejecutado/verificado verde en la corrección documental.

### Trazabilidad global RF → responsabilidad → evidencia futura (no cumplimiento)

La presencia de las 57 filas y seis RNF es cobertura **documental del plan**, no 57 requisitos implementados/probados. DA-11 resuelta: RF36/40/46 referencian algoritmo/pruebas §6.C. Evidencia implementada/revisada solo del paquete monetario RF3/4/41/RNF1 **parciales** §2; continuación retirada por el usuario. No completar toda esta matriz con mocks/fixtures ni atribuirles cumplimiento de registro.

| RF | Responsabilidad técnica | Pruebas |
|---|---|---|
| 1 | Registro propio, catálogo activo/método, servidor impone titular | I1/I2, F5, E1 |
| 2 | Destino admin/propio y contexto gestión | I1/I2, F5, E1 |
| 3 | Dominio Decimal ROUND_HALF_UP/reparto | U1, F1, I1 |
| 4 | Base servicio aislada de ventas | U1, I1/I2 |
| 5 | Snapshot en aceptación inicial con valores actuales | I1/I5/I6, E1/E3 |
| 6 | Snapshot aceptado no recalculado por catálogo | I1/I5, E1 |
| 7 | Proyección estimada/confirmada y preview cents | U1, F1/F2/F5, E1/E3 |
| 8 | Momento automático barbero inmutable manualmente | U3, I1/I2, F5, E1 |
| 9 | Fecha real en envelope/aceptación/pull | I1/I7, E3/E4 |
| 10 | Retroactivo admin sin precio/porcentaje manual | I1/I2, F5, E1 |
| 11 | Historial propio DTO completo seguro | I2, F2, E1/E3 |
| 12 | Resumen separa confirmado/estimado/pagado/due/unknown | U2, I3/I4, F2, E1/E2 |
| 13 | Dos obligaciones y journals, saldo propio independiente | U2, I3, F2, E2 |
| 14 | Filtro titular, subrecursos y 404 uniforme | I2, F3/F4, E1/E3 |
| 15 | DTO/SQL personal; admin personal no global | I2, F3, E1/E3 |
| 16 | Movimientos cliente/comisión autorizados | I2/I3, F5, E2 |
| 17 | Abono parcial/restante con método/momento/autor propios | I3, F5, E2 |
| 18 | Cobro cliente solo modifica concepto cliente | U2, I3, E2 |
| 19 | Pago profesional solo su comisión | U2, I3, E2 |
| 20 | Saldado vía movimiento exacto, no flag | I3, F5, E2 |
| 21 | Neto, saldo, parcial/pagado/unknown/review/excedente | U2, I3/I4, F2/F5, E2 |
| 22 | Cambios permitidos propios y cobro genera movimiento | U3, I4/I6, F5, E2/E3 |
| 23 | Primer pago bloquea; pago inicial permitido | I3/I4/I6, F5, E2 |
| 24 | Pertenencia cierre y bloqueo aun sin pagos | I4/I6/I7, E4 |
| 25 | Abonos posteriores pese a bloqueo, no al anulado | I3/I4, F5, E2 |
| 26 | Admin motivo, autor/anterior/posterior, sin borrado | I2/I4, F5, E2 |
| 27 | Anulado preservado y fuera de devengado vigente | U2, I4, F2, E2 |
| 28 | Repositorios locales, rol conocido y acciones suficientes | F2/F3/F5, E3 |
| 29 | Persist-first, reload/reapertura, estado pendiente | F3/F5, E3 |
| 30 | Sync resultado typed individual definitivo/causa | I5, F4/F5, E3 |
| 31 | Desactivación posterior servicio no invalida offline | I1/I5, E1/E3 |
| 32 | Journal único y retry sin recalcular/duplicar | I5/I6, F4, E3 |
| 33 | Namespace actor/generación, clave/cache y cancelación | I2, F3/F4, E3 |
| 34 | Actor activo/rol vigente y validaciones bajo transacción | I2/I5/I6, F4, E3 |
| 35 | Catálogo insuficiente sin confirmar; fallo no borra válido | F3/F5, E3 |
| 36 | LWW por método/fecha/finanzas íntegro desde bases preservadas; anulación autorizada terminal independiente; journal intacto | U3, I5/I6, F4, E3 |
| 37 | Elección cobro sin default e importe precio mostrado | I3/I5, F5, E1/E2/E3 |
| 38 | Exceso offline íntegro revisión, saldo no aplicado | I3/I5/I6, F2/F5, E2/E3 |
| 39 | Ajustes y snapshot original inmutable | I4/I7/I8, E4 |
| 40 | Edición/anulación offline bloqueada a revisión; prioridad terminal nunca evita actor/titularidad/pagos/cierre | I4/I5/I6, F4/F5, E3 |
| 41 | Precisión/porcentaje/abonos/límite devolución concurrente | U1/U2, I3/I6, F1/F5, E2 |
| 42 | Recálculo servicio, método conserva; admin fecha/barbero | U2, I4/I6, F5, E2 |
| 43 | Compensación referenciada/excedente/devolución explícita | U2, I3/I4/I6, E2 |
| 44 | Legacy unknown por concepto, comisión conservada | I4/I8, F2/F5, E2 |
| 45 | Servicio vs dinero, momentos/jornadas y ajustes | U3, I7, F2, E4 |
| 46 | Anulación autorizada terminal, obligaciones conocidas canceladas/unknown conservado; dinero excedente y no reactivar | U2/U3, I4/I6, F5, E2 |
| 47 | Asignación/journal profesional independiente y recálculo | U2, I4/I6, E2 |
| 48 | Revocación detalle/local y justificante propio sanitizado | I2/I4/I5, F3/F4, E2/E3 |
| 49 | Cierre vincula snapshot; tardío ajuste y bloqueo | I6/I7, E4 |
| 50 | Dinero aceptado pending-imputación, apertura/imputación idempotente | I6/I7, F2/F5, E4 |
| 51 | Retroactivos admin, futuro rechazo/reloj revisión | U3, I1/I5, F5, E1/E3 |
| 52 | Períodos AR/momento propio/cobertura e imputación aparte | U3, I1/I7, F2, E1/E4 |
| 53 | No aceptados aparte; resolución real íntegra/erróneo compensado | U2, I3/I4/I5, F2/F5, E2/E3 |
| 54 | Evidencia histórica admin, fecha desconocida no falseada | I2/I4/I8, F5, E2 |
| 55 | Pull90 días+abiertos+pendientes y cobertura/actualización | I1/I2, F2/F4, E3 |
| 56 | Activos para selección, inactivos destino admin, missing revisa dependientes | I1/I2/I5, F5, E1/E3 |
| 57 | Identidades/dependencias y resultado corte/movimientos separado | I3/I5/I6, F4/F5, E1/E3 |

| RNF | Evidencia requerida |
|---|---|
| 1 | U1/U2, F1; roundtrip SQLite/PostgreSQL sin float; reparto suma precio, abonos no normalizados |
| 2 | U3/I1/I7/E4; ISO UTC y presentación local, fecha-only local separada de instante |
| 3 | I1/I8; contratos legacy, upgrades repetidos y rollout mixto controlado, suite000 intacta |
| 4 | F5/E1–E4 y scripts visuales001; tokens/kit existentes, mobile/desktop y estados accesibles |
| 5 | I2/F3/F4/E3; JSON/red/store/caches/account switching/replay/justificantes, no solo UI |
| 6 | Matriz completa anterior, gates unit/integration/E2E, rojo→verde por futura tarea y evidencia archivada |

## 11. Estado de decisiones y gates de paquetes posteriores

DA-11 y división progresiva **resueltas por el usuario y reflejadas en la spec**; módulo monetario cerrado con revisión aprobada, aún no conectado a la API. Continuación retirada por el usuario; spec completa pendiente. El conflicto privacidad/compatibilidad queda detenido antes de adaptar respuestas personales, no se inventa una decisión. Riesgos/gates conservados para una eventual continuación aprobada:

1. **Legado sin identidad idempotente ni movimientos:** no se puede reconstruir dinero/fecha/titular a partir de booleanos de sync o totales de caja. Reconciliación protegida/unknown y diagnóstico, sin datos inventados. Si la copia muestra cierres ambiguos, faltan decisiones sobre esos datos concretos; detener migración y preguntar, no aplicar heurística monetaria.
2. **Contrato legacy — bloqueante del adaptador personal:** `parte_barberia` no tiene excepción constitucional aprobada. Detener ese adaptador y aclarar privacidad/compatibilidad/versionado antes de implementarlo, conforme §4.
3. **SQLite:** Numeric legado y driver BEGIN legacy son insuficientes como fundamento de concurrencia exacta. Tests con conexiones reales/centavos autoritativos; no inferir garantías de PostgreSQL desde SQLite.
4. **Claves/custodia:** ciclo inicial conectado→slot activo durable→reapertura offline sin auth→logout elimina key→titular recupera versiones conectado, con gates browser real. Cuarentena owner ambiguo requiere custodia de clave privada fuera de app y validación previa; falta de ese dato operativo bloquea rollout local, no justifica nuevo login offline ni filas perdidas/asignadas a B. No prometer revocación física de memoria/OS/XSS ni de dispositivo desconectado.
5. **Revocación offline:** aislamiento entre cuentas es inmediato al cambiar sesión; reasignación remota solo se conoce al actualizar. Pull debe traer revocaciones incluso de registros fuera de ventana90. No descartar outbox por reasignación sin resultado/causa.
6. **Alcance/dependencias:** React Query y tests unitarios no existen; validar compatibilidad/fijar versiones sin upgrade general. PWA actual cachea shell/fuentes incompleto; build producción y reapertura offline son gates, no el test dev actual.
7. **Operaciones no terminales/efectivo:** dependiente debe reexaminarse tras habilitación segura del mismo corte, revision solo admin/resolución nueva, terminal nunca reejecuta. Modo/hash/UUID originales inmutables. Capacidad usa fuente real corregida, no raw; pendiente erróneo exige base+compensación+evidencia atómicas, no delta a cero. Ejemplos §3 guían assertions, no demuestran implementación.
8. **Caja fuera de cortes:** no generalizar movimientos a ventas/gastos por conveniencia. Los summaries deben etiquetar devengado y dinero de cortes, preservando componentes legacy; no describirlos como nuevo reporte global integral de tesorería.
9. **Tests actuales:** import `main` crea tablas y overrides compiten por módulo; no ejecutar contra entorno real. Aislar/migrar esa suite y bootstrap productivo antes de pytest o E2E masivos; no se ha retirado su DDL.
10. **División progresiva:** §2 conserva las macroentregas/rangos históricos, sin cantidad/duración global comprometida ni macro-tareas. Paquete monetario ya aprobado/cerrado; continuación retirada. Cualquier detalle posterior y sus tareas requieren nueva aprobación.
11. **DA-11 resuelta / precaución de implementación posterior:** estado terminal autorizado separado de ganadores método/fecha/finanzas, con bases preservadas y controles vigentes antes de aceptar. No fullrecord ni mezclar financieros; no extrapolar convergencia contra actores/datos que cambiaron ni saltar RF40 por prioridad de anulación. No requiere una nueva decisión sobre la regla ya aprobada.
12. **Snapshot/acceso:** cursor materializado S/finalizaciónT y autorización actual cada página son dependencias de cobertura/privacidad. Ni slot/key ni snapshot permiten prometer inmediatez de una revocación remota sin conexión; rechazar páginas revocadas y no publicar suma local incompleta como total.

### Siguiente paso pendiente de aprobación y preguntas diferidas

- **Ahora:** detener la continuación retirada por el usuario. Conservar el módulo monetario y su evidencia T1–T6; no rehacer tareas cerradas ni iniciar nuevas sin aprobación.
- **Gate de negocio previo al adaptador personal:** aclarar `parte_barberia`/compatibilidad/versionado sin resolverlo automáticamente, antes de adaptar contratos personales de registro/historial.
- **Pregunta operativa posterior:** ¿dónde se obtendrá una **copia sanitizada y autorización separada** para validar legado/migración, y cuál será el entorno efímero PostgreSQL/PWA para los gates? No abrir, copiar ni migrar bases reales por conservar este plan.
- **Dato operativo:** ¿se dispone de custodia/proceso de recuperación de legacy ambiguo y de provisión segura de claves de vault antes de rollout? Validarlo en copia; no solicitar secretos en conversación ni configurar MCP.

Se conserva el plan global y el módulo monetario implementado/revisado; la continuación fue retirada por el usuario. Se mantienen el gate de privacidad y las autorizaciones separadas de migración/custodia. El cierre monetario no acredita registro, API, offline ni cumplimiento integral de la spec.
