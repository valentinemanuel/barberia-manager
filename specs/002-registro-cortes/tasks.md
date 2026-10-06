# Tareas 002 — Paquete 1: reparto y validación monetaria puros

Estado: **paquete monetario implementado y revisión de cierre aprobada (T1–T6)**. Sin autorización de paquetes posteriores ni validación integral de la spec.

## Alcance y límites

- División progresiva aprobada por el usuario. Este archivo contiene únicamente el primer paquete, no todas las tareas de la spec 002.
- Seis tareas de 20–30 minutos: estimación del desglose 2–3 horas, dentro del rango provisional de 2–4 horas del paquete.
- Únicos archivos de código/tests que podrá crear este paquete cuando se autorice implementar:
  - `backend/app/services/dinero_cortes.py`.
  - `backend/tests/test_dinero_cortes_aislado.py`.
- Interfaces y contratos: `plan.md`, sección 2, «Interfaces exactas del primer paquete».
- Cobertura **parcial** de RF-3, RF-4, RF-41 y RNF-1; RNF-6 aporta verificación por tarea. No afirmar cumplimiento integral, aceptación de cortes ni funcionamiento offline por completar este paquete.
- No modificar API, modelos, `corte_service.py`, dependencias, configuración, fixtures globales ni datos; no conectar todavía las funciones al flujo productivo. No migrar ni ejecutar suites que importen la aplicación o abran bases.
- Paquetes posteriores, tareas adicionales y su implementación requieren aprobación independiente. No crear specs hijas por cuenta propia.

## Protocolo de ejecución futura

1. Aprobación recibida: «Comienza» y confirmación posterior «Implementar las seis actuales». No ampliar el alcance.
2. Una tarea cada vez: escribir tests primero, obtener y registrar el fallo pertinente en rojo, implementar lo mínimo, ejecutar en verde y la regresión aislada del paquete, marcar solo esa tarea y parar esa ejecución. El coordinador puede iniciar después la siguiente tarea autorizada; ante bloqueantes, detener la secuencia y consultar.
3. Si un caso ya está cubierto y pasa antes de tocar código, registrar ese hecho; no introducir fallos artificiales ni afirmar un rojo inexistente. Una verificación final no exige romper código correcto.
4. Registrar en la evidencia de cada tarea el comando, resultado inicial/final y casos verificados; no marcar un checkbox por intención o solo por revisión documental.
5. Si aparecen imports/configuración con posibles efectos sobre DB o el alcance excede los dos archivos, detenerse y consultar. No resolverlo ejecutando la suite global ni ampliando el paquete.

Comando aislado, desde `backend` en bash, a verificar antes de ejecutar según las precauciones de `plan.md` §2:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q
```

Este comando y los tests **no se han ejecutado** al redactar las tareas. Verificar primero la cadena de imports y la configuración; no asumir que las opciones protegen de código externo desconocido.

## Tareas en orden de dependencia

- [x] **T1. Validar porcentajes Decimal sin normalización.** RF-41 (rango/precisión parcial), RNF-1, RNF-6. **20–30 min.**
  - Dependencias: ninguna; revisar aislamiento de imports antes de cualquier ejecución.
  - Escribir tests de `validar_porcentaje(valor: Decimal) -> Decimal` y después crear la función pura: límites 0 y 100, `50.25`, notación `1E+2` y cero negativo; retornar el mismo objeto Decimal, sin cambiar escala/signo.
  - Cubrir fuera de rango, precisión representada superior a dos decimales —incluido `50.000`—, NaN/sNaN/infinidades y tipos no Decimal, con orden de validación y errores en español establecidos en el plan.
  - Hecho cuando: los casos válidos e inválidos pasan por ejecución aislada, se rechazan sin conversión/redondeo silencioso y queda registrada evidencia rojo/verde del nuevo validador, sin importar aplicación ni DB.

- [x] **T2. Validar importes de abono positivos y exactos.** RF-41 (validación de entrada parcial), RNF-1, RNF-6. **20–30 min.**
  - Dependencias: T1, por el módulo y harness aislados; no introducir acoplamiento entre porcentaje y abono.
  - Escribir tests y crear `validar_importe_abono(importe: Decimal) -> Decimal`: importes positivos con hasta dos decimales conservan identidad/representación; cero —incluido signo negativo—, negativos, precisión excesiva, no finitos y tipos no Decimal se rechazan conforme al plan.
  - La función no recibe ni consulta saldo, método, usuario, origen online/offline o DB; no afirma que un pago sea aceptable financieramente.
  - Hecho cuando: matriz de validación y tests de T1 pasan con el comando aislado, se registra evidencia del nuevo contrato y no hay aceptación financiera ni conversiones desde float/cadenas.

- [x] **T3. Calcular reparto nominal y validar el precio canónico.** RF-3/RF-4 (aritmética y base de servicio parciales), RF-41 (porcentaje reutilizado), RNF-1, RNF-6. **20–30 min.**
  - Dependencias: T1 y T2.
  - Escribir tests y crear `calcular_partes(precio: Decimal, porcentaje_barbero: Decimal) -> tuple[Decimal, Decimal]`, usando exclusivamente el precio del servicio y el validador de porcentaje.
  - Cubrir 100 pesos al 50 % → 50/50, porcentajes 0/100, precio cero y retornos Decimal al centavo. Validar precio finito, no negativo y escala máxima de dos decimales; rechazar tipos/precisión inválidos sin corregirlos.
  - No agregar productos/consumibles a la firma ni importar sus modelos; no conectar al servicio de registro actual ni imponer un máximo comercial nuevo.
  - Hecho cuando: casos nominales, precio inválido y validadores anteriores pasan; ambos importes son Decimal y suman el precio exacto; evidencia registrada y solo los dos archivos permitidos contienen cambios de código/tests.

- [x] **T4. Verificar redondeo matemático y resto exacto.** RF-3/RF-4 (parciales), RNF-1, RNF-6. **20–30 min.**
  - Dependencias: T3.
  - Añadir vectores parametrizados: precio `0.08` al 30 % → `0.02/0.06`; `0.05` al 50 % → `0.03/0.02`; `1.01` al 50 % → `0.51/0.50`; `0.03` al 50 % → `0.02/0.01`.
  - Verificar `ROUND_HALF_UP` explícito para comisión y barbería como resto exacto, sin redondear ambas partes de forma independiente. Los valores intermedios con tres decimales no se usan como precios/abonos válidos.
  - Hecho cuando: vectores y regresión T1–T3 pasan con suma exacta y formato al centavo; documentar si los casos revelaron un fallo o ya estaban cubiertos, sin fabricar un rojo. Ningún resultado depende del redondeo predeterminado del llamador.

- [x] **T5. Aislar la aritmética del contexto Decimal del llamador.** RF-3/RF-41 (parciales), RNF-1, RNF-6. **20–30 min.**
  - Dependencias: T4.
  - Escribir casos con precisión llamadora baja, redondeo distinto y traps `Inexact`/`Rounded` activos, además de un precio exacto grande como `1000000000000.01`, sin usar float.
  - Garantizar contexto privado suficiente para producto/división/redondeo/resta y salida al centavo; el contexto llamador completo —precisión, redondeo, `Emin`, `Emax`, `capitals`, `clamp`, traps y flags— se conserva antes/después, también ante excepción.
  - No llamar `setcontext` ni convertir el rango persistente de un modelo en límite comercial de esta función; un límite técnico no representable se informa conforme al contrato del plan, nunca se trunca.
  - Hecho cuando: resultados exactos coinciden bajo los contextos probados, el contexto original queda intacto y regresión T1–T4 pasa; se registra evidencia sin introducir estado global ni efectos externos.

- [x] **T6. Verificar aislamiento y cerrar evidencia del paquete.** RF-3/RF-4/RF-41 y RNF-1 (cobertura parcial), RNF-6. **20–30 min.**
  - Dependencias: T1–T5.
  - Revisar y comprobar que el test importa solo stdlib, pytest y el módulo puro, sin `app.main`, database, routers, modelos o tests ajenos; verificar cadena de `__init__`/configuración antes de ejecutar y parar si dejó de ser segura.
  - Ejecutar únicamente la suite aislada completa; revisar type hints, errores en español, ausencia de conversiones float, conservación de entradas y límites de alcance. No ejecutar pytest global, coverage de toda app, migraciones ni instalar dependencias.
  - Registrar comandos/resultados y pruebas relevantes en la evidencia y actualizar el estado del paquete al finalizar, sin marcar la spec completa como implementada.
  - Hecho cuando: suite aislada completa en verde con evidencia reproducible, solo los dos archivos autorizados cambiaron productivamente y no se tocaron API/DB/configuración; revisión del paquete confirma su cobertura parcial y queda solicitado el siguiente paso al usuario. Esta tarea es de verificación, no autoriza código adicional ni requiere un fallo artificial.

## Evidencia futura

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T1 | Rojo real: 1 error de colección en 0.13s, salida 2; `ModuleNotFoundError: No module named 'app.services.dinero_cortes'` antes de crear el módulo | Verde: `33 passed in 0.03s`, salida 0 | Desde `backend`, ambas ejecuciones: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q`. Python 3.11.9, pytest 7.4.3 existentes; `python` resolvió a `C:\Users\TiendaOP\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe` (sin venv ni instalación). Tres `__init__` vacíos revisados; no encontrados conftest/config pytest de proyecto ni ascendientes revisados. Casos: identidad/escala/signo, 0/100, 50.25, 1E+2, -0.00; no finitos, precisión antes de rango y tipos sin convertir; mensajes exactos en español. Imports solo Decimal/pytest/módulo puro; sin aplicación, DB, suite global ni caches generadas. |
| T2 | Rojo real: 1 error de colección en 0.08s, salida 2; `ImportError: cannot import name 'validar_importe_abono'` antes de crear la función | Verde: `75 passed in 0.05s`, salida 0; 42 casos nuevos y 33 de regresión T1 | Desde `backend`, ambas ejecuciones: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q`. Python 3.11.9/pytest 7.4.3 existentes, ejecutable vuelto a comprobar: `C:\Users\TiendaOP\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`. Tres `__init__` vacíos e imports seguros revisados; sin config pytest/conftest de proyecto ni ascendientes revisados. Verificados identidad/escala, positivos, ceros de ambos signos, negativos, no finitos, precisión antes de positividad, tipos sin convertir, mensajes exactos y contexto Decimal intacto ante éxito/error. Solo validador puro y tests, sin saldo/origen/aceptación financiera ni reparto; sin DB, instalaciones, suite global ni caches generadas. |
| T3 | Rojo real: 1 error de colección en 0.09s, salida 2; `ImportError: cannot import name 'calcular_partes'` antes de crear la función | Verde: `117 passed in 0.08s`, salida 0; 42 casos nuevos y 75 de regresión T1–T2 | Desde `backend`, ambas ejecuciones: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q`. Python 3.11.9/pytest 7.4.3 existentes, ejecutable vuelto a comprobar: `C:\Users\TiendaOP\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`. Imports y tres `__init__` vacíos revisados; sin config pytest/conftest de proyecto ni ascendientes revisados. Casos nominales 100/50, porcentajes 0/100/-0.00, precio cero/-0.00 y notación exponencial; tupla Decimal al centavo, suma exacta y entradas intactas. Precio: tipo/finitud/precisión/no negativo con mensajes exactos; porcentaje reutiliza su validador. ROUND_HALF_UP explícito y barbería como resto; localcontext básico, sin tope comercial. Vectores T4 y robustez del contexto T5 pendientes, sin adelantar sus tests. Solo dos archivos productivos; sin DB/API/instalaciones/configuración/suite global ni caches generadas. |
| T4 | Verde inicial real tras añadir tests: `125 passed in 0.09s`, salida 0; código T3 ya satisfacía los vectores, sin rojo artificial | Mismo verde, única ejecución; 8 casos nuevos (4 vectores × 2 redondeos) y 117 de regresión T1–T3; sin cambio de implementación | Desde `backend`: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q`. Python 3.11.9/pytest 7.4.3 existentes, ejecutable vuelto a comprobar: `C:\Users\TiendaOP\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`. Imports y tres `__init__` vacíos revisados; sin config pytest/conftest de proyecto ni ascendientes revisados. Vectores 0.08/30→0.02/0.06, 0.05/50→0.03/0.02, 1.01/50→0.51/0.50 y 0.03/50→0.02/0.01 bajo ROUND_DOWN y ROUND_HALF_EVEN del llamador. Verificados Decimal al centavo, comisión matemática, barbería como resto y suma exacta; redondeo llamador conservado. Solo test y evidencia T4 modificados en esta ejecución; sin pruebas de precisión baja/traps de T5, DB/API/dependencias/configuración/suite global ni caches generadas. |
| T5 | Rojo real: `24 failed, 143 passed in 0.33s`, salida 1; contexto heredado provocaba Rounded/Inexact/Overflow y límites técnicos sin ValueError contractual | Verde: `167 passed in 0.13s`, salida 0; 42 casos nuevos y 125 de regresión T1–T4 (18 nuevos ya pasaban inicialmente, sin rojo artificial) | Desde `backend`, ambas ejecuciones: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q`. Python 3.11.9/pytest 7.4.3 existentes, ejecutable vuelto a comprobar: `C:\Users\TiendaOP\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`. Imports y tres `__init__` vacíos revisados; sin config pytest/conftest de proyecto ni ascendientes revisados. Contexto llamador prec=2, ROUND_DOWN/HALF_EVEN, Emin=-2/Emax=2, capitals=0/clamp=1, traps y flags preestablecidos: resultados exactos incluidos precio 1000000000000.01 y vectores T4; todos los parámetros/traps/flags e identidad del contexto intactos ante éxito/errores de precio/porcentaje/límite técnico. Context privado completo con precisión derivada del producto y precio al centavo, MIN_EMIN/MAX_EMAX, flags propios y traps de exactitud; solo comisión admite ROUND_HALF_UP. MAX_PREC se verifica antes de aritmética/asignación gigante; DecimalException→ValueError español contractual, sin máximo comercial ni setcontext. Ceros con exponente MAX_EMAX siguen representables sin cambiar entradas. Solo dos archivos productivos y evidencia T5; sin DB/API/dependencias/configuración/suite global ni caches generadas. T6 pendiente. |
| T6 | Verificación final; sin rojo artificial ni tests/código adicionales. AST y aislamiento: OK, salida 0 | Suite completa aislada: `167 passed in 0.12s`, salida 0; 0 casos nuevos, 167 de regresión | Desde `backend`: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q`. Python 3.11.9, ejecutable existente `C:\Users\TiendaOP\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`. Script inline `PYTHONDONTWRITEBYTECODE=1 python -` con ast/pathlib/hashlib/sys: tres __init__ vacíos; ninguna config pytest/conftest en backend ni ascendientes hasta raíz; producto importa solo decimal, test solo decimal/pytest/módulo puro; tres firmas públicas exactas, 3 funciones de producto y 25 de test con type hints, 13 mensajes contractuales españoles. Sin float/conversiones/estado global/efectos de módulo; cuatro literales float exclusivamente en casos de rechazo no-Decimal (líneas 67/116/195/249), no aritmética de negocio. Revisión de pureza, preservación de entradas/contexto, precisión derivada y resto exacto coherente con tests. SHA256 antes/después de ejecución iguales: producto `a25b1e7856b3de4b7c272360fbfe386990c39a5aa3eec5ab7de91ec8ed624648`, test `ee660625ba657fd2c27fddc491052ddc74d81f064e40c648050e33001f94edc3`. `git status --short`, `git diff --name-only`, `git ls-files --others --exclude-standard backend` y `git diff --check`: solo dos archivos productivos nuevos del paquete; cambios ajenos en coordinator/MEMORY/constitution y spec/plan preservados. Advertencias Git LF→CRLF, sin errores de whitespace. T6 modifica únicamente este documento; sin DB/API/dependencias/configuración/suite global ni caches generadas. |

## Criterio de cierre y continuidad

Revisión de cierre independiente por `sdd-reviewer`: **APROBADO PAQUETE 1**, sin bloqueantes dentro del alcance. Verificó imports/configuración y ejecutó el comando aislado: `167 passed in 0.13s`. Los rojos previos constan como evidencia registrada durante implementación, no como fallos reproducidos por la revisión final. No se accedió a DB ni se ejecutó la suite global.

Completar este paquete aporta funciones puras comprobadas, **no** registro de cortes mejorado, pagos, API, offline, migración ni sincronización. Mantener el contrato global de 57 RF/6 RNF como pendiente de implementación integral. La siguiente división se propone después de medir este paquete y necesita aprobación; no añadir tareas posteriores por iniciativa del implementador.

Cierre T6: paquete monetario en verde, con cobertura parcial RF-3/RF-4/RF-41/RNF-1 y verificación RNF-6; no se declara implementada la spec completa. Se solicita al coordinador la validación independiente con reviewer y la decisión del usuario sobre el siguiente paso. Ejecución detenida, sin redactar ni implementar paquetes adicionales.

---

## Paquete 2 — Fundaciones de registro (dinero conectado + UoW única)

Estado: **tareas redactadas, pendientes de aprobación para implementar**. Paquete 1 (T1–T6) cerrado, no rehacer.

Aprobación recibida: revisión de simplificación aprobada por el usuario y alcance del paquete 2 aprobado para redactar tareas. No se autoriza implementación por esta redacción.

### Alcance y límites

- Siete tareas de 20–30 minutos: estimación 3–4 horas. Si una tarea excede, reducir/reproponer antes de continuar.
- Cobertura **parcial**: RF-3/RF-4/RF-5 (registro con dinero exacto y snapshot aplicado), RF-41 (validación de entrada de precio/porcentaje), RF-32 (una sola escritura por operación), RNF-1 (redondeo real) y RNF-3 (compatibilidad legacy + esqueleto Alembic). No afirma movimientos, saldos, edición/anulación, sync/offline ni cumplimiento integral.
- Archivos que podrá tocar este paquete cuando se autorice implementar:
  - M `backend/app/services/corte_service.py`.
  - M `backend/app/routers/cortes.py` (solo commit de la UoW en registro).
  - M `backend/app/routers/sync.py` (solo commit de la UoW en `crear_corte`; hoy persiste gracias al commit interno del servicio).
  - M `backend/app/schemas/usuario.py` (solo validador de porcentaje).
  - C `backend/alembic.ini`, C `backend/alembic/env.py`, C `backend/alembic/script.py.mako`, C `backend/alembic/versions/001_base_legacy.py` (base solo-inspección, sin secretos ni URL real).
  - M `backend/tests/test_cortes.py` (solo assertions a Decimal exacto, sin cambiar fixtures).
- Prohibido en este paquete: modificar `dinero_cortes.py` y su test (cerrados, solo reutilizar); tocar el DTO personal `CorteResponse` (gate `parte_barberia`/privacidad de plan §11.2, detenido hasta aclaración); tocar `create_all`/`main.py`/`database.py` (gate 9, suite actual dependiente); frontend, movimientos, cierres, outbox, cifrado, barrera global y escritura dual.
- Colisión de nombres conocida: `corte_service.calcular_partes` (redondeo del contexto, ambas partes quantizadas) vs `dinero_cortes.calcular_partes` (contrato del paquete 1). T7 la resuelve importando el puro y eliminando el duplicado.
- Precaución DB real: `app/main.py:22` ejecuta `create_all` sobre `backend/barberia.db` al importar, y los tests por archivo importan la app. Antes de cada ejecución registrar hash/tamaño de `backend/barberia.db`; al terminar verificar que no cambió su contenido (solo `create_all` idempotente sobre tablas existentes) y que `git status` no muestra más que los archivos autorizados (`*.db` está ignorado). Prohibido `pytest tests/` global y prohibido cualquier `upgrade` Alembic contra base real.

Comandos desde `backend` en bash:

```bash
# Regresión del paquete 1 (aislado, sin app ni DB)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS='' PYTEST_PLUGINS='' python -m pytest --confcutdir=tests --noconftest -p no:cacheprovider -o addopts= tests/test_dinero_cortes_aislado.py -q
# Tests por archivo del paquete 2 (importan la app; ver precaución DB real arriba)
python -m pytest tests/test_cortes.py -q
python -m pytest tests/test_sync_roles.py tests/test_roles_permisos.py -q
```

### Tareas en orden de dependencia

- [x] **T7. Conectar el reparto puro al registro y eliminar el duplicado.** RF-3/RF-4 (parciales), RNF-1.
  - Dependencias: ninguna dentro del paquete; reutiliza `dinero_cortes` cerrado sin modificarlo.
  - Tests primero: POST `/cortes/` con servicio 100.00 y barbero 50% responde `"50.00"`/`"50.00"` exactos; caso servicio 0.05 al 50% → `0.03`/`0.02` (ROUND_HALF_UP y resto exacto, no HALF_EVEN ni doble quantize).
  - Implementar: `crear_corte` usa `dinero_cortes.calcular_partes`; eliminar el `calcular_partes` local de `corte_service.py`.
  - Hecho cuando: tests nuevos en verde, suite aislada del paquete 1 sigue en 167 verdes y el registro real usa el contrato puro.

- [x] **T8. Validar precio canónico y porcentaje a la entrada del registro.** RF-41 (parcial).
  - Dependencias: T7.
  - Tests primero: servicio con precio/porcentaje de precisión excesiva se rechaza con `ValueError` en español (el router lo vuelve 400); un float infiltrado también se rechaza como `ValueError`, nunca `TypeError` (500). Hallazgo: a nivel API con filas persistidas no se puede provocar, porque el ORM redondea a escala 2 al leer `Numeric` (verificado: raw 10.005 → ORM `Decimal('10.01')`); por eso la prueba es a nivel servicio con objetos transient. El rechazo en la carga del catálogo (`schemas/servicio.py`) excede los archivos autorizados y queda como decisión pendiente del usuario.
  - Implementar: `crear_corte` envuelve `(TypeError, ValueError)` de `calcular_partes` en `ValueError` con el mismo mensaje (el router ya mapea a 400); el guard de precisión lo aporta T7.
  - Hecho cuando: entradas inválidas rechazadas con mensaje exacto y las válidas conservan identidad/escala.

- [x] **T9. Unidad de trabajo única: quitar el commit interno.** RF-32 (una escritura por operación), RNF-3.
  - Dependencias: T7 (mismo archivo).
  - Tests primero: POST `/cortes/` persiste el corte; `sync` con `crear_corte` persiste (hoy depende del commit interno del servicio).
  - Implementar: retirar `db.commit()` de `corte_service.py` (conservar `flush`/`refresh` necesarios); commitean `routers/cortes.py` y `routers/sync.py`. Verificar con grep que `services/corte_service.py` no contiene `commit`.
  - Hecho cuando: ambos caminos persisten con un solo commit por operación y `test_cortes.py` + `test_sync_roles.py` pasan.

- [x] **T10. Validador de porcentaje en el schema de usuario.** RF-41 (parcial).
  - Dependencias: ninguna (archivo distinto); reutiliza `validar_porcentaje` sin duplicar reglas.
  - Tests primero: crear/actualizar usuario con 100.001 o `50.000` → 422; 50.25 y 100 pasan sin normalización.
  - Hecho cuando: el schema rechaza precisión/rango inválidos con mensaje en español y los válidos conservan representación.

- [ ] **T11. Snapshot aplicado del registro (RF-5 parcial).** RF-5 (parcial).
  - Dependencias: T7–T8.
  - Tests primero: el corte creado conserva `precio`, `porcentaje_barbero`, `parte_barbero`, `parte_barberia` iguales a los valores validados/aplicados; cambiar después el porcentaje del barbero no altera el corte existente.
  - Hecho cuando: tests verdes sin agregar columnas nuevas (las columnas ya existen) y sin exponer nada nuevo en el DTO personal.

- [ ] **T12. Esqueleto Alembic y base solo-inspección.** RNF-3.
  - Dependencias: ninguna (archivos nuevos).
  - Crear `alembic.ini` (sin URL real ni secretos), `env.py` (no importa `app.main`, no abre DB), `script.py.mako` y `versions/001_base_legacy.py` que solo inspecciona el schema existente y se detiene ante diferencias, sin crear ni modificar nada.
  - Hecho cuando: `alembic history` muestra la base sin errores ni conexión a base real; prohibido ejecutar `upgrade` contra cualquier base real en este paquete.

- [ ] **T13. Regresión exacta y cierre del paquete.** RF-3/RF-4/RF-5/RF-41 (parciales), RNF-1/RNF-3/RNF-6.
  - Dependencias: T7–T12.
  - Convertir las assertions con `float()` de `test_cortes.py` a comparación Decimal exacta (`"50.00"`); ejecutar por archivo `test_cortes.py`, `test_sync_roles.py`, `test_roles_permisos.py` y la suite aislada del paquete 1, todo en verde, con precaución DB real registrada.
  - Registrar comandos/resultados en la evidencia de abajo y actualizar el estado sin declarar implementada la spec completa. El cierre requiere revisión independiente (`sdd-reviewer`) y no autoriza paquete 3, API nueva, sync ni frontend.
  - Hecho cuando: todo lo anterior en verde, solo los archivos autorizados cambiaron y queda solicitada la revisión de cierre.

### Evidencia futura (paquete 2)

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T7 | Rojo real: `1 failed, 2 passed`; `AssertionError: assert '0.02' == '0.03'` en `test_crear_corte_redondeo_matematico_mitad_hacia_arriba` (quantize del contexto HALF_EVEN antes del fix) | Verde: `3 passed` en `tests/test_cortes.py` + `167 passed` suite aislada paquete 1 | Desde `backend`: `python -m pytest tests/test_cortes.py -q` y comando aislado del paquete 1. `barberia.db` hash idéntico antes/después (`3fe8caa6…f924a9`); `git status` solo `corte_service.py` + `test_cortes.py`. Cambio: `crear_corte` importa `dinero_cortes.calcular_partes`, eliminado duplicado local e import Decimal sin uso. |
| T8 | Rojo parcial real: 2 API-tests iniciales devolvían 201 (supuesto falso: el ORM oculta el exceso al leer); reescritos a nivel servicio. Tras reescribir: 5 passed + 1 failed con `TypeError: El precio del servicio debe ser Decimal` (habría sido 500) | Verde: `6 passed` en `tests/test_cortes.py` + `167 passed` aislada | Desde `backend`: `python -m pytest tests/test_cortes.py -q`. Sonda SQLite en TEMP (sin tocar repo): raw conserva 10.005/50.001, ORM devuelve `Decimal('10.01')`/`Decimal('50.00')`. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); solo `corte_service.py` + `test_cortes.py`. Cambio: wrap `(TypeError, ValueError)` → `ValueError` mismo mensaje. Pendiente decisión usuario: validación en carga de catálogo (`schemas/servicio.py`, fuera de autorizados). |
| T9 | Rojo real: la otra conexión SÍ veía el corte (`assert <Corte object> is None` falló) porque el servicio commiteaba | Verde: `10 passed` (`test_cortes.py` + `test_sync_roles.py`) + `167 passed` aislada | Desde `backend`: `python -m pytest tests/test_cortes.py tests/test_sync_roles.py -q`. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); grep confirma cero `db.commit` en `corte_service.py`. Cambio: servicio con `flush`+`refresh` sin commit; commitean `routers/cortes.py` (+refresh) y `routers/sync.py` por operación. Solo archivos autorizados. |
| T10 | Rojo real: `Failed: DID NOT RAISE ValidationError` para `'50.000'`/50.001 (rango válido, precisión excesiva aceptada) | Verde: `39 passed` (`test_cortes.py` + `test_sync_roles.py` + `test_roles_permisos.py` + `test_usuarios_auditoria.py`) + `167 passed` aislada | Desde `backend`: pytest por archivo. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); solo `schemas/usuario.py` + `test_cortes.py`. Cambio: `field_validator` en `UsuarioCrear`/`UsuarioActualizar` reutilizando `validar_porcentaje` (TypeError→ValueError); `UsuarioResponse` intacto. Tests a nivel schema (sin DB). |
| T11 |  |  |  |
| T12 |  |  |  |
| T13 |  |  | |
