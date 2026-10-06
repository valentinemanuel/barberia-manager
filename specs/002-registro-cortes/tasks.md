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

- [x] **T8-bis. Validar precio en la carga del catálogo (extensión aprobada).** RF-41.
  - El usuario delegó la decisión pendiente de T8: se incluye la extensión mínima (un archivo: `schemas/servicio.py`).
  - Tests primero: `ServicioCrear`/`ServicioActualizar` con `"10.005"` pasaban (rojo `DID NOT RAISE`); válidos `"100.00"`/`"0.05"` conservan representación.
  - Implementar: `field_validator("precio")` en Crear/Actualizar (no en Base/Response): finito y ≤2 decimales, mensajes en español; la positividad sigue en `Field(gt=0)`; el router devuelve 422 automáticamente.
  - Hecho cuando: precisión excesiva rechazada en la entrada del catálogo y el resto de suites sigue verde.

- [x] **T9. Unidad de trabajo única: quitar el commit interno.** RF-32 (una escritura por operación), RNF-3.
  - Dependencias: T7 (mismo archivo).
  - Tests primero: POST `/cortes/` persiste el corte; `sync` con `crear_corte` persiste (hoy depende del commit interno del servicio).
  - Implementar: retirar `db.commit()` de `corte_service.py` (conservar `flush`/`refresh` necesarios); commitean `routers/cortes.py` y `routers/sync.py`. Verificar con grep que `services/corte_service.py` no contiene `commit`.
  - Hecho cuando: ambos caminos persisten con un solo commit por operación y `test_cortes.py` + `test_sync_roles.py` pasan.

- [x] **T10. Validador de porcentaje en el schema de usuario.** RF-41 (parcial).
  - Dependencias: ninguna (archivo distinto); reutiliza `validar_porcentaje` sin duplicar reglas.
  - Tests primero: crear/actualizar usuario con 100.001 o `50.000` → 422; 50.25 y 100 pasan sin normalización.
  - Hecho cuando: el schema rechaza precisión/rango inválidos con mensaje en español y los válidos conservan representación.

- [x] **T11. Snapshot aplicado del registro (RF-5 parcial).** RF-5 (parcial).
  - Dependencias: T7–T8.
  - Tests primero: el corte creado conserva `precio`, `porcentaje_barbero`, `parte_barbero`, `parte_barberia` iguales a los valores validados/aplicados; cambiar después el porcentaje del barbero no altera el corte existente.
  - Hecho cuando: tests verdes sin agregar columnas nuevas (las columnas ya existen) y sin exponer nada nuevo en el DTO personal.

- [x] **T12. Esqueleto Alembic y base solo-inspección.** RNF-3.
  - Dependencias: ninguna (archivos nuevos).
  - Crear `alembic.ini` (sin URL real ni secretos), `env.py` (no importa `app.main`, no abre DB), `script.py.mako` y `versions/001_base_legacy.py` que solo inspecciona el schema existente y se detiene ante diferencias, sin crear ni modificar nada.
  - Hecho cuando: `alembic history` muestra la base sin errores ni conexión a base real; prohibido ejecutar `upgrade` contra cualquier base real en este paquete.

- [x] **T13. Regresión exacta y cierre del paquete.** RF-3/RF-4/RF-5/RF-41 (parciales), RNF-1/RNF-3/RNF-6.
  - Dependencias: T7–T12.
  - Convertir las assertions con `float()` de `test_cortes.py` a comparación Decimal exacta (`"50.00"`); ejecutar por archivo `test_cortes.py`, `test_sync_roles.py`, `test_roles_permisos.py` y la suite aislada del paquete 1, todo en verde, con precaución DB real registrada.
  - Registrar comandos/resultados en la evidencia de abajo y actualizar el estado sin declarar implementada la spec completa. El cierre requiere revisión independiente (`sdd-reviewer`) y no autoriza paquete 3, API nueva, sync ni frontend.
  - Hecho cuando: todo lo anterior en verde, solo los archivos autorizados cambiaron y queda solicitada la revisión de cierre.

### Cierre del paquete 2 (revisión independiente)

`sdd-reviewer`: **APROBADO PAQUETE 2**, sin correcciones bloqueantes. Verificó `tasks.md`, diff `dev...HEAD` y los 12 archivos; reejecutó la suite aislada (`167 passed`). Confirmó "Hecho cuando" T7–T13+T8-bis, cobertura declarada parcial sin overclaim, gates §11 intactos (DTO personal, `create_all`, sin upgrade real, sin sync/frontend/movimientos, `dinero_cortes` intacto) y constitución. Observaciones P2 no bloqueantes para paquetes futuros: falta `db.rollback()` en rutas de error; fallback silencioso preexistente de `metodo_pago` a `EFECTIVO` en `sync.py:119-122`; stub `_DbNula` no reutilizable en caminos exitosos; coerción float→Decimal de Pydantic 2.5.2 no verificada (cubierta por guard T8). El cierre no autoriza paquete 3 ni declara la spec implementada.

### Evidencia futura (paquete 2)

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T7 | Rojo real: `1 failed, 2 passed`; `AssertionError: assert '0.02' == '0.03'` en `test_crear_corte_redondeo_matematico_mitad_hacia_arriba` (quantize del contexto HALF_EVEN antes del fix) | Verde: `3 passed` en `tests/test_cortes.py` + `167 passed` suite aislada paquete 1 | Desde `backend`: `python -m pytest tests/test_cortes.py -q` y comando aislado del paquete 1. `barberia.db` hash idéntico antes/después (`3fe8caa6…f924a9`); `git status` solo `corte_service.py` + `test_cortes.py`. Cambio: `crear_corte` importa `dinero_cortes.calcular_partes`, eliminado duplicado local e import Decimal sin uso. |
| T8 | Rojo parcial real: 2 API-tests iniciales devolvían 201 (supuesto falso: el ORM oculta el exceso al leer); reescritos a nivel servicio. Tras reescribir: 5 passed + 1 failed con `TypeError: El precio del servicio debe ser Decimal` (habría sido 500) | Verde: `6 passed` en `tests/test_cortes.py` + `167 passed` aislada | Desde `backend`: `python -m pytest tests/test_cortes.py -q`. Sonda SQLite en TEMP (sin tocar repo): raw conserva 10.005/50.001, ORM devuelve `Decimal('10.01')`/`Decimal('50.00')`. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); solo `corte_service.py` + `test_cortes.py`. Cambio: wrap `(TypeError, ValueError)` → `ValueError` mismo mensaje. Pendiente decisión usuario: validación en carga de catálogo (`schemas/servicio.py`, fuera de autorizados). |
| T9 | Rojo real: la otra conexión SÍ veía el corte (`assert <Corte object> is None` falló) porque el servicio commiteaba | Verde: `10 passed` (`test_cortes.py` + `test_sync_roles.py`) + `167 passed` aislada | Desde `backend`: `python -m pytest tests/test_cortes.py tests/test_sync_roles.py -q`. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); grep confirma cero `db.commit` en `corte_service.py`. Cambio: servicio con `flush`+`refresh` sin commit; commitean `routers/cortes.py` (+refresh) y `routers/sync.py` por operación. Solo archivos autorizados. |
| T10 | Rojo real: `Failed: DID NOT RAISE ValidationError` para `'50.000'`/50.001 (rango válido, precisión excesiva aceptada) | Verde: `39 passed` (`test_cortes.py` + `test_sync_roles.py` + `test_roles_permisos.py` + `test_usuarios_auditoria.py`) + `167 passed` aislada | Desde `backend`: pytest por archivo. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); solo `schemas/usuario.py` + `test_cortes.py`. Cambio: `field_validator` en `UsuarioCrear`/`UsuarioActualizar` reutilizando `validar_porcentaje` (TypeError→ValueError); `UsuarioResponse` intacto. Tests a nivel schema (sin DB). |
| T11 | Verde inicial real: `10 passed` incluyendo el test nuevo (código T7–T8 ya conservaba el snapshot; sin rojo artificial ni cambio de implementación) | Mismo verde, única ejecución | Desde `backend`: `python -m pytest tests/test_cortes.py -q`. Test: corte 100.00/50% conserva `100.00`/`50.00`/`50.00` tras subir el porcentaje a 60. Sin columnas nuevas ni cambios al DTO personal. `barberia.db` sin cambios de contenido; solo `test_cortes.py` + este documento. |
| T12 | Rojo real: `No config file 'alembic.ini' found` y `alembic: command not found` (se usa `python -m alembic`; 1.13.0 instalado) | Verde: `history` muestra `001_base_legacy`; `upgrade head` en TEMP vacía no crea tablas de app (solo `alembic_version`); en TEMP con legacy informa `schema legacy completo (9 tablas)` | `alembic.ini` con placeholder inerte + override `ALEMBIC_SQLALCHEMY_URL`; `env.py` no importa `app.main`. `barberia.db` hash idéntico (`3fe8caa6…f924a9`); prohibido `upgrade` contra base real. Solo 4 archivos nuevos. |
| T8-bis | Rojo real: `DID NOT RAISE ValidationError` para `"10.005"` en Crear/Actualizar | Verde: suite completa por archivo (`42 + 2 + 8 + 10 + 2`) + `167 passed` aislada | `field_validator("precio")` solo en entrada; `barberia.db` hash idéntico; `git status` solo `schemas/servicio.py` + `test_cortes.py` + este documento. |
| T13 | Sin rojo: conversión directa de 2 assertions `float()` a strings exactos en el test legacy | Verde: `36 passed` (`test_cortes.py` + `test_sync_roles.py` + `test_roles_permisos.py`) + `4 passed` extra (`test_usuarios_auditoria.py`) + `167 passed` aislada | Desde `backend`: pytest por archivo (comandos del paquete). `barberia.db` hash idéntico (`3fe8caa6…f924a9`); `git status` solo `test_cortes.py` + este documento. Paquete 2 completo en cobertura parcial, sin declarar spec implementada; cierre pendiente de revisión independiente (`sdd-reviewer`), que no autoriza paquete 3. |

---

## Paquete 3 — Contratos personales sin parte de la barbería (cierre del gate §11.2)

Estado: **tareas redactadas, pendientes de aprobación para implementar**. Paquetes 1 y 2 cerrados, no rehacer.

Aprobación recibida: el usuario aprueba corregir (no documentar excepción) y redactar estas tareas. No se autoriza implementación por esta redacción.

Decisión del gate registrada: se crea el DTO personal `CortePersonal` (= `CorteResponse` sin `parte_barberia`) y lo usan los 3 endpoints personales. El listado global de admin (`GET /cortes/`) y reportes conservan el contrato completo. El detalle compartido `GET /{id}` pasa al DTO personal para ambos roles: el admin conserva listado global + reportes para ver la parte de la barbería. Sin versionado de API: no existen consumidores externos (único cliente: la PWA propia).

### Alcance y límites

- Seis tareas de 20–30 minutos: estimación 2–3 horas.
- Cobertura **parcial**: RF-11 (shape del historial propio), RF-14 (404 ajeno, regresión), RF-15 (sin brutos del negocio), RNF-3 (compat admin intacta), RNF-5, RNF-6. No afirma movimientos, saldos, sync/offline, jornadas ni cumplimiento integral.
- Archivos que podrá tocar este paquete cuando se autorice implementar:
  - M `backend/app/schemas/corte.py` (solo agregar `CortePersonal`; `CorteResponse` intacto).
  - M `backend/app/routers/cortes.py` (solo `response_model` de `/mi/historial`, `/{id}` y `POST /`).
  - M `backend/tests/test_cortes.py` (solo tests nuevos de privacidad).
  - M `frontend/src/services/db.ts` (solo tipo local `CorteLocal`).
  - M `frontend/src/pages/RegistroCortes.tsx` (solo retirar el cálculo local de `parte_barberia` offline; `parte_barbero` se conserva).
- Prohibido: tocar `CorteResponse`, endpoints admin, reportes, modelos, servicios, sync, resto del frontend, migraciones y `create_all`.
- Precaución DB real vigente (igual que paquete 2): `main.py:22` ejecuta `create_all` al importar; registrar hash de `backend/barberia.db` antes/después, pytest solo por archivo, prohibido `pytest tests/` global.
- Verificación frontend: `npm run build` en `frontend/` (tsc + vite).

### Tareas en orden de dependencia

- [x] **T14. Crear el DTO personal sin parte de la barbería.** RF-11/RF-15 (parciales), RNF-3.
  - Dependencias: ninguna dentro del paquete.
  - Tests primero: `CortePersonal` acepta un corte completo y su `.model_dump()` no contiene `parte_barberia`; `CorteResponse` sigue intacto con el campo (compat admin).
  - Implementar: agregar `CortePersonal` en `schemas/corte.py` (mismos campos menos `parte_barberia`); no modificar `CorteResponse`.
  - Hecho cuando: tests schema-level en verde sin DB y el contrato admin no cambia.

- [x] **T15. Historial propio con DTO personal.** RF-11/RF-15 (parciales).
  - Dependencias: T14.
  - Tests primero: `GET /mi/historial` como barbero no incluye `parte_barberia` en ningún ítem y sí incluye `parte_barbero`, servicio, momento real, método y estados; como admin en `/mi/historial` ve solo lo propio.
  - Implementar: `response_model=list[CortePersonal]` en `mis_cortes`.
  - Hecho cuando: tests API en verde y el listado global de admin sigue devolviendo el contrato completo.

- [x] **T16. Detalle y registro con DTO personal.** RF-11/RF-14/RF-15 (parciales).
  - Dependencias: T14.
  - Tests primero: `GET /{id}` propio y `POST /` responden sin `parte_barberia`; `GET /{id}` ajeno como barbero sigue 404 (regresión RF-14); el admin conserva listado global + reportes para la parte de la barbería (decisión registrada arriba).
  - Implementar: `response_model=CortePersonal` en `obtener_corte` y `registrar_corte`.
  - Hecho cuando: tests API en verde, 404 ajeno intacto y ningún endpoint admin modificado.

- [x] **T17. Test de privacidad integral de contratos personales.** RF-15 (parcial), RNF-5/RNF-6.
  - Dependencias: T15–T16.
  - Tests primero (deben fallar si algún campo prohibido aparece): recorrer las respuestas de `/mi/historial`, `/{id}` propio, `POST /` y resúmenes `/mi/resumen/*` y afirmar ausencia de `parte_barberia`, `costo`, `margen`, `bruto`, `total_cortes` globales o datos de otro barbero.
  - Hecho cuando: el test falla ante cualquier filtración futura y pasa con los contratos del paquete; sin cambiar código productivo en esta tarea salvo lo necesario para el test.

- [x] **T18. Limpiar la parte local de la barbería en el frontend.** RF-15 (parcial), RNF-1.
  - Dependencias: T15–T16 (el backend ya no la envía).
  - Verificar primero con grep que nada renderiza `parte_barberia` en vistas de barbero (constatado: solo cálculo local + tipos).
  - Implementar: retirar el cálculo de `parte_barberia` en el guardado offline de `RegistroCortes.tsx` (conservar `parte_barbero` estimada) y el campo en `CorteLocal` (`db.ts`) si nada más lo lee; el tipo de admin (`DashboardAdmin.tsx`) no se toca.
  - Hecho cuando: `npm run build` en verde y ningún código de barbero referencia `parte_barberia`.

- [x] **T19. Regresión y cierre del paquete.** RF-11/RF-14/RF-15 (parciales), RNF-3/RNF-5/RNF-6.
  - Dependencias: T14–T18.
  - Ejecutar por archivo las suites tocadas (`test_cortes.py`, `test_roles_permisos.py`, `test_sync_roles.py`, `test_usuarios_auditoria.py`) + suite aislada del paquete 1, todo en verde, con precaución DB real registrada; `npm run build` en verde.
  - Registrar comandos/resultados en la evidencia de abajo y actualizar el estado sin declarar implementada la spec completa. El cierre requiere revisión independiente (`sdd-reviewer`) y no autoriza paquete 4 ni declara el gate de otros paquetes.
  - Hecho cuando: todo lo anterior en verde, solo los archivos autorizados cambiaron y queda solicitada la revisión de cierre.

### Evidencia futura (paquete 3)

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T14 | Rojo real: `ImportError: cannot import name 'CortePersonal'` | Verde: `14 passed` en `tests/test_cortes.py` | Desde `backend`: `python -m pytest tests/test_cortes.py -q`. Schema-level sin DB; `barberia.db` hash idéntico (`3fe8caa6…f924a9`); solo `schemas/corte.py` + `test_cortes.py`. Cambio: `CortePersonal` agregado, `CorteResponse` intacto. |
| T15 | Rojo real: 2 failed (`"parte_barberia" not in items[0]` con `CorteResponse`) | Verde: `39 passed` (`test_cortes.py` + `test_roles_permisos.py`) | Desde `backend`: pytest por archivo. `barberia.db` hash idéntico; solo `routers/cortes.py` + `test_cortes.py`. Cambio: `response_model=list[CortePersonal]` en `mis_cortes`; listado global admin intacto. |
| T16 | Rojo real: ausencia de `parte_barberia` falló en detalle/registro con `CorteResponse` | Verde: `44 passed` (3 archivos) | Efecto colateral honesto: 4 assertions viejas (T7/T11/legacy) esperaban el campo en la API y se migraron al contrato nuevo (el resto exacto se verifica en fila DB + suite aislada). `barberia.db` hash idéntico; solo `routers/cortes.py` + `test_cortes.py`. Cambio: `response_model=CortePersonal` en detalle y registro; 404 ajeno intacto; admin conserva listado + reportes. |
| T17 | Verde inicial real: contratos ya limpios tras T15–T16 (sin rojo artificial ni cambio productivo) | Mismo verde | Sensibilidad del detector verificada una vez sin commitear: detecta `parte_barberia` en `CorteResponse` (contrato admin). Recorre registro/historial/detalle/3 resúmenes. Solo `test_cortes.py` + este documento. |
| T18 | Rojo: grep hallaba `parte_barberia` en `db.ts` y `RegistroCortes.tsx` (código de barbero) | Verde: `npm run build` (tsc + vite) OK; grep limpio en código de barbero | Retirados cálculo offline y campo `CorteLocal`; tipo de admin intacto; filas Dexie viejas con el campo se ignoran sin migrar (propiedad extra tolerada). Solo `db.ts` + `RegistroCortes.tsx` + este documento. |
| T19 | Sin rojo: solo verificación final, sin cambios productivos nuevos | Verde: `49 + 2 + 8 + 10 + 2` por archivo (toda la suite backend) + `167 passed` aislada + `npm run build` OK | `barberia.db` hash idéntico (`3fe8caa6…f924a9`); `git status` solo este documento. Paquete 3 completo en cobertura parcial, sin declarar spec implementada; cierre pendiente de revisión independiente (`sdd-reviewer`), que no autoriza paquete 4. |

### Cierre del paquete 3 (revisión independiente)

`sdd-reviewer`: **APROBADO PAQUETE 3**, sin correcciones (ningún P1; no tocó archivos). Verificó "Hecho cuando" T14–T19, cobertura parcial sin overclaim, gate §11.2 cerrado respetando la decisión registrada (detalle compartido a DTO personal; admin conserva listado + reportes; sin versionado por no haber consumidores externos), constitución (Decimal, % solo servicios, privacidad, compat admin) y legitimidad de la migración de assertions viejas (resto exacto en fila DB + suite aislada). Reejecutó: `test_cortes.py` 19 passed, resto 30 passed, aislada 167 passed, `npm run build` OK, hash DB idéntico. P2 informativos para futuro: T17 no asserts explícitos de totales globales; `Math.round` float preexistente en estimada offline (`RegistroCortes.tsx:81`, corresponde a paquete frontend); P2 del paquete 2 vigentes. El cierre no autoriza paquete 4 ni declara la spec implementada.

---

## Paquete 4 — Registro online: destino y momento real

Estado: **tareas redactadas, pendientes de aprobación para implementar**. Paquetes 1–3 cerrados, no rehacer.

Aprobación recibida: alcance aprobado por el usuario (RF-1/RF-2/RF-8/RF-10 online). No se autoriza implementación por esta redacción.

### Alcance y límites

- Seis tareas de 20–30 minutos: estimación 2–3 horas.
- Cobertura **parcial**: RF-1 (registro propio con servicio/método), RF-2 (destino admin), RF-8 (momento automático barbero), RF-10 (retroactivo admin con valores actuales), RF-56 (destino inactivo permitido si existe con porcentaje). No afirma offline/sync, momentos al sincronizar (RF-9), comisión estimada (RF-7), ni cumplimiento integral.
- Decisiones registradas:
  - `barbero_id` opcional en el body, **solo admin**; si lo envía un barbero → 403 (no silencioso). Destino inexistente → 404. Destino inactivo permitido si existe con porcentaje (RF-56); sin porcentaje recuperable → 400.
  - `momento_real` opcional, **solo admin**; pasado sin límite, futuro → 400. Si lo envía un barbero → 400 (RF-8: sin fecha manual). Nunca precio/porcentaje manual en este flujo (fuera de alcance de la spec).
  - El momento se guarda en `Corte.fecha` (UTC naive, contrato existente; RNF-2 pleno con zona/jornadas corresponde a paquete de jornadas).
- Archivos que podrá tocar este paquete cuando se autorice implementar:
  - M `backend/app/schemas/corte.py` (solo campos `barbero_id`/`momento_real` opcionales en `CorteCrear`).
  - M `backend/app/services/corte_service.py` (solo destino + momento en `crear_corte`).
  - M `backend/app/routers/cortes.py` (solo autorización destino/momento en `registrar_corte`).
  - M `backend/tests/test_cortes.py` (solo tests nuevos).
- Prohibido: DTOs de respuesta, endpoints admin existentes, sync, frontend, modelos nuevos, migraciones, `create_all`.
- Precaución DB real vigente: hash de `backend/barberia.db` antes/después, pytest solo por archivo, prohibido `pytest tests/` global.

### Tareas en orden de dependencia

- [x] **T20. Destino admin en el registro.** RF-1/RF-2 (parciales), RF-56 (parcial).
  - Dependencias: ninguna dentro del paquete.
  - Tests primero: admin registra con `barbero_id` de otro → 201 asociado al destino con su porcentaje; `barbero_id` inexistente → 404; barbero que envía `barbero_id` (incluso propio) → 403; destino inactivo con porcentaje → 201.
  - Implementar: `barbero_id: Optional[int]` en `CorteCrear`; `crear_corte` resuelve destinatario (propio por defecto); router exige rol admin si viene destino.
  - Hecho cuando: tests API en verde y el registro propio del barbero no cambia de comportamiento.

- [x] **T21. Momento retroactivo solo admin.** RF-8/RF-10 (parciales).
  - Dependencias: T20 (mismo flujo de registro).
  - Tests primero: admin registra con `momento_real` pasado → 201 con esa `fecha`; futuro → 400; barbero que envía `momento_real` → 400; sin momento → `fecha` automática (≈ ahora UTC).
  - Implementar: `momento_real: Optional[datetime]` en `CorteCrear`; validación pasado/futuro; el servicio usa el momento o el automático.
  - Hecho cuando: tests API en verde, sin precio/porcentaje manual en ningún caso.

- [x] **T22. Snapshot con valores actuales del destinatario.** RF-5 (parcial), RF-6.
  - Dependencias: T20–T21.
  - Tests primero: admin registra retroactivo para barbero con % distinto → reparto con el porcentaje **actual del destinatario**, no del admin; cambio posterior de catálogo/porcentaje no altera el corte (ya probado en T11, regresión).
  - Implementar: verificar que el reparto usa precio actual del servicio + porcentaje actual del destinatario (el código ya lo hace; ajustar solo si un test revela lo contrario, sin rojo artificial).
  - Hecho cuando: tests verdes que fijan destinatario-valores-actuales para propio, admin-propio y admin-tercero.

- [x] **T23. Errores exactos y sin filtraciones.** RF-14 (regresión), RNF-5.
  - Dependencias: T20–T21.
  - Tests primero: destino inexistente → 404 idéntico a corte inexistente (sin revelar existencia); `barbero_id` de barbero por barbero → 403; `momento_real` futuro por admin → 400 con mensaje en español; cuerpo con tipos inválidos → 422.
  - Hecho cuando: cada rechazo con su código exacto y sin datos ajenos en mensajes.

- [x] **T24. Regresión de contratos personales.** RF-11/RF-15 (regresión).
  - Dependencias: T20–T23.
  - Tests: historial/detalle/registro con destino y momento responden sin `parte_barberia` (reutilizar detector T17); listado global admin intacto con contrato completo.
  - Hecho cuando: verdes sin cambios productivos nuevos salvo ajustes exigidos por un rojo real.

- [x] **T25. Regresión total y cierre del paquete.** RF-1/RF-2/RF-8/RF-10/RF-56 (parciales), RNF-3/RNF-6.
  - Dependencias: T20–T24.
  - Ejecutar por archivo las suites tocadas + suite aislada del paquete 1, todo en verde, con precaución DB real registrada.
  - Registrar comandos/resultados en la evidencia de abajo y actualizar el estado sin declarar implementada la spec completa. El cierre requiere revisión independiente (`sdd-reviewer`) y no autoriza paquete 5.
  - Hecho cuando: todo lo anterior en verde, solo los archivos autorizados cambiaron y queda solicitada la revisión de cierre.

### Evidencia futura (paquete 4)

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T20 | Rojo real: 4 failed (el body ignoraba `barbero_id`; sin 403/404) | Verde: `26 passed` (`test_cortes.py` + `test_sync_roles.py`) | Desde `backend`: pytest por archivo. `barberia.db` hash idéntico; solo `schemas/corte.py` + `corte_service.py` + `routers/cortes.py` + `test_cortes.py`. Cambio: `barbero_id` opcional solo admin (403 barbero, 404 inexistente, inactivo con % permitido); reparto con valores del destinatario; registro propio intacto; sync sin destino sigue propio. Seguimiento P2-1 (decisión del usuario: restringir a barberos): admin→otro admin → 400, propio explícito → 201; rama `fix/destino-solo-barberos`. |
| T21 | Rojo real: 3 failed (momento ignorado: 201 con fecha automática en vez de 2020; sin 400 a futuro ni a barbero) | Verde: `30 passed` (`test_cortes.py` + `test_sync_roles.py`) | Desde `backend`: pytest por archivo. `barberia.db` hash idéntico; solo `schemas/corte.py` + `corte_service.py` + `routers/cortes.py` + `test_cortes.py`. Cambio: `momento_real` opcional solo admin (pasado sin límite, futuro 400, barbero 400, tz normalizada a UTC naive); servicio lo guarda en `fecha`. |
| T22 | Verde inicial real (cubierto por implementación T20; sin rojo artificial ni cambio productivo) | Mismo verde | Test: admin retroactivo 2021 para barbero 30% sobre 200.00 → `60.00` + fecha conservada (no el 0% del admin). Solo `test_cortes.py` + este documento. |
| T23 | Verde inicial real (cubierto por T20–T21; sin rojo artificial ni cambio productivo) | Mismo verde | Test: 404 `Barbero no encontrado`, 403 con `admin`, 400 con `futuro`, 422 en tipos inválidos; sin datos ajenos. Solo `test_cortes.py` + este documento. |
| T24 | Verde inicial real (detector T17 + listado admin intactos; sin rojo artificial ni cambio productivo) | Mismo verde | Test nuevo: listado global admin conserva `parte_barberia`. Solo `test_cortes.py` + este documento. |
| T25 | Sin rojo: solo verificación final, sin cambios productivos nuevos | Verde: `60 + 2 + 8 + 10 + 2` por archivo (toda la suite backend) + `167 passed` aislada | `barberia.db` hash idéntico (`3fe8caa6…f924a9`); `git status` solo este documento. Paquete 4 completo en cobertura parcial, sin declarar spec implementada; cierre pendiente de revisión independiente (`sdd-reviewer`), que no autoriza paquete 5. |

### Cierre del paquete 4 (revisión independiente)

`sdd-reviewer`: **APROBADO PAQUETE 4**, sin P1 ni archivos tocados. Verificó "Hecho cuando" T20–T25, cobertura parcial sin overclaim, constitución (Decimal, % solo servicios, privacidad, compat: sync y DTOs intactos) y legitimidad de verdes iniciales. Reejecutó: 30 + 30 + 22 + 167 verdes, hash DB idéntico. P2 para futuro: (1) no se valida `destino.rol` — un admin podría atribuir un corte a otro admin; RF-2 dice "cualquier barbero", requiere decisión de spec, no corrección unilateral; (2) sin `rollback()` en rutas de error (heredado); (3) imprecisión menor de redacción en evidencia T23. El cierre no autoriza paquete 5 ni declara la spec implementada.

---

## Paquete 5 — Idempotencia y reintentos seguros

Estado: **implementado (T26–T33 en verde) y aprobado por `sdd-reviewer`; pendiente integración a `dev` vía PR**. Paquetes 1–4 cerrados, no rehacer.

Aprobación recibida: alcance aprobado por el usuario (RF-32 + base RF-30). No se autoriza implementación por esta redacción.

### Alcance y límites

- Ocho tareas de 20–30 minutos: estimación 3–4 horas.
- Cobertura **parcial**: RF-32 (sin duplicados ante reintento), RF-30 (resultado individual por operación), RF-57 (resultado conservado por operación, parcial). No afirma offline/outbox frontend, revisión/dependientes, movimientos, jornadas ni cumplimiento integral.
- Decisiones registradas:
  - Clave idempotente = `(actor_id, namespace_cliente, operacion_id)`; `operacion_id` es UUID cliente obligatoria solo cuando se usa el camino idempotente.
  - `operacion_uuid` opcional en `CorteCrear`; sin UUID → camino legacy intacto (RNF-3). Namespace por defecto `"web"` en POST directo; sync aportará el suyo (paquete de sync).
  - Misma clave + mismo hash → acuse guardado sin reejecutar. Misma clave + hash distinto → 409 conflicto de identidad, sin efecto.
  - Solo estado terminal en este paquete (`aceptada`/`rechazada`); revisión/dependientes corresponden a paquetes posteriores.
- Archivos que podrá tocar este paquete cuando se autorice implementar:
  - C `backend/app/models/operacion_corte.py` (solo tabla mínima de journal idempotente).
  - M `backend/app/models/__init__.py` (solo registro del modelo).
  - C `backend/app/services/operacion_corte_service.py` (solo ejecutor get-or-create + hash).
  - M `backend/app/services/corte_service.py` (solo delegar en el ejecutor cuando hay UUID; camino sin UUID intacto).
  - M `backend/app/routers/cortes.py` (solo pasar UUID/namespace al servicio).
  - M `backend/app/routers/sync.py` (solo aceptar `operacion_uuid` opcional en datos de `crear_corte`; sin él, comportamiento legacy documentado sin promesa de deduplicación retroactiva).
  - C `backend/alembic/versions/002_operaciones_corte.py` (solo crea la tabla nueva; idempotente; sin tocar legacy).
  - M `backend/tests/test_cortes.py` (solo tests nuevos).
- Prohibido: modificar tablas/columnas legacy, DTOs de respuesta, otros routers/servicios, frontend, `create_all`, estados no terminales.
- **Gate de migración real**: el archivo de migración es código (seguro commitear); APLICAR `upgrade` contra `barberia.db` u otra base real exige aprobación explícita + backup verificado/restaurable + validación previa en copia temporal (plan §4). Durante el paquete, `upgrade` solo contra DBs temporales (`ALEMBIC_SQLALCHEMY_URL`); los tests usan sus DBs locales como siempre. Hash de `barberia.db` antes/después de cada ejecución.

### Tareas en orden de dependencia

- [x] **T26. Tabla mínima de journal idempotente + migración 002.** RF-32 (base), RNF-3.
  - Dependencias: ninguna dentro del paquete.
  - Tests primero: `alembic history` muestra `002` tras `001`; `upgrade head` en TEMP vacía crea solo `operaciones_corte` (+ `alembic_version`); en TEMP con legacy no toca tablas existentes; repetir `upgrade` es no-op.
  - Implementar: modelo `OperacionCorte` (actor_id, namespace_cliente, operacion_id UUID, accion, hash, modo_captura, estado, resultado JSON, recibida_en UTC; única la tupla clave) + revisión `002_operaciones_corte.py` solo-creación.
  - Hecho cuando: ambos escenarios TEMP verificados y prohibido aplicar contra base real en este paquete.

- [x] **T27. Ejecutor idempotente (get-or-create + hash).** RF-32 (parcial).
  - Dependencias: T26.
  - Tests primero: primera ejecución con clave+hash crea y devuelve resultado; segunda con misma clave + mismo hash devuelve el acuse guardado sin reejecutar (el efecto ocurre una sola vez: un solo corte en DB).
  - Implementar: `operacion_corte_service.ejecutar` (lookup por clave; si existe y hash coincide → acuse; si no → ejecuta callback en la misma UoW, guarda resultado, un commit).
  - Hecho cuando: doble llamada secuencial deja un solo efecto y el mismo acuse; tests con DBs locales (la concurrencia real con hilos la cubre T31).

- [x] **T28. Camino idempotente en POST /cortes.** RF-30/RF-32 (parciales), RNF-3.
  - Dependencias: T27.
  - Tests primero: POST con `operacion_uuid` dos veces → 201 ambas con el mismo `id` de corte y un solo corte en DB; POST sin UUID → comportamiento legacy intacto (regression de paquetes 2–4).
  - Implementar: `operacion_uuid: Optional[UUID]` en `CorteCrear`; el router usa el ejecutor solo si viene UUID (namespace `"web"`).
  - Hecho cuando: tests API en verde y el camino sin UUID no cambia ni un byte de comportamiento.

- [x] **T29. Conflicto de identidad.** RF-32 (parcial).
  - Dependencias: T27.
  - Tests primero: misma clave + hash distinto (mismo UUID, distinto servicio/monto) → 409, sin crear corte ni mutar el resultado guardado; el acuse original sigue devolviéndose en replays del hash original.
  - Implementar: comparación de hash canónico en el ejecutor; 409 con mensaje en español.
  - Hecho cuando: tests en verde y ningún efecto secundario del intento conflictivo.

- [x] **T30. Replay terminal sin recalcular.** RF-32/RF-57 (parciales).
  - Dependencias: T27–T28.
  - Tests primero: replay con catálogo cambiado entremedio (precio/porcentaje distintos) devuelve el acuse original con el snapshot aplicado original, sin recalcular ni crear otro corte.
  - Hecho cuando: el replay no toca `corte_service` (verificable por snapshot idéntico) y pasa el test.

- [x] **T31. Doble envío simultáneo.** RF-32 (parcial), RNF-6.
  - Dependencias: T27–T28.
  - Tests primero: dos hilos con misma UUID contra TestClient → un solo corte en DB y ambos acuses con el mismo `id` (reintentar hasta 3 veces si hay contención SQLite; si la contención es sistemática, documentar y usar secuencial + constraint única como red).
  - Hecho cuando: unicidad garantizada por constraint + manejo, no por suerte de timing.

- [x] **T32. UUID opcional en el camino sync.** RF-30/RF-32 (parciales), RNF-3.
  - Dependencias: T27.
  - Tests primero: op `crear_corte` con `operacion_uuid` en datos → reenvío del lote no duplica; sin UUID → comportamiento legacy intacto (documentar la limitación de deduplicación retroactiva del plan §4, sin prometerla).
  - Implementar: leer `operacion_uuid` opcional de `op.datos` y pasarlo al ejecutor con namespace `"sync"`.
  - Hecho cuando: tests del envelope en verde y el resto del protocolo sync intacto.

- [x] **T33. Regresión total y cierre del paquete.** RF-30/RF-32/RF-57 (parciales), RNF-3/RNF-6.
  - Dependencias: T26–T32.
  - Ejecutar por archivo las suites tocadas + suite aislada del paquete 1, todo en verde, con precaución DB real + gate de migración registrados (ningún `upgrade` contra base real ejecutado).
  - Registrar comandos/resultados en la evidencia de abajo y actualizar el estado sin declarar implementada la spec completa. El cierre requiere revisión independiente (`sdd-reviewer`) y no autoriza paquete 6.
  - Hecho cuando: todo lo anterior en verde, solo los archivos autorizados cambiaron y queda solicitada la revisión de cierre.

### Evidencia futura (paquete 5)

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T26 | Rojo real: `history` mostraba solo `001` | Verde: `history` con `002`; TEMP vacía crea solo `operaciones_corte` (+`alembic_version`); TEMP legacy intacta + tabla nueva; repetir no-op | `upgrade` solo en TEMP (`ALEMBIC_SQLALCHEMY_URL`); `barberia.db` hash idéntico (`3fe8caa6…f924a9`); prohibido aplicar contra base real. Modelo + `__init__` + revisión `002`. |
| T27 | Rojo real: `ModuleNotFoundError: app.services.operacion_corte_service` | Verde: replay mismo hash → mismo acuse + 1 solo corte | Ejecutor con hash canónico, replay sin reejecutar, sin commit (UoW del llamador). DIVULGACIÓN: el hash de `barberia.db` cambió una vez (`3fe8caa6…` → `b691f8c5…`) porque el `create_all` histórico (gate 9) creó la tabla vacía `operaciones_corte` al importar la app en tests; verificado: 0 filas nuevas, legacy intacto (1 admin, resto vacío), `create_all` no escribe filas por construcción. Robustez añadida: `002` salta creación si la tabla existe (verificado en TEMP con `create_all` previo). |
| T28 | Rojo real: doble POST con misma UUID creó 2 cortes (`assert 1 == 2`) | Verde: `38 passed` (2 archivos) | Desde `backend`: pytest por archivo. DB estable en baseline T27 (`b691f8c5…`, tabla vacía por `create_all` histórico); solo `schemas/corte.py` + `routers/cortes.py` + `test_cortes.py`. Cambio: `operacion_uuid` opcional (UUID→422 automático), ejecutor con namespace `web` y payload de strings; sin UUID el camino no cambia ni un byte (misma llamada). Solo se guarda estado aceptado; registrar rechazos queda para paquete 6. |
| T29 | Rojo real: conflicto devolvía 400 en vez de 409 | Verde: `39 passed` (2 archivos) | DB estable en baseline T27; solo `operacion_corte_service.py` + `routers/cortes.py` + `test_cortes.py`. Cambio: `ConflictoIdentidad(ValueError)` + 409 en router (orden de except preservado); acuse original intacto y 1 solo corte. |
| T30 | Verde inicial real (el ejecutor jamás reejecuta por diseño T27; sin rojo artificial ni cambio productivo) | Mismo verde | Test: catálogo cambiado (200.00/60%) + replay → mismo id, `50.00`/`100.00` originales. Solo `test_cortes.py` + este documento. |
| T31 | Rojo real y flaky: 2/5 corridas con un solo resultado (el perdedor moría con 500 por contención) | Verde estable: 6/6 corridas + `64 passed` (3 archivos) + `167` aislada | DB estable en baseline T27; solo `operacion_corte_service.py` + `routers/cortes.py` + `test_cortes.py`. Cambio: reintento acotado (3) con rollback en flush (ejecutor) y en commit (router); el constraint único decide el ganador y el resto converge a su acuse. |
| T32 | Rojo real: reenvío del lote duplicaba (2 cortes) | Verde: `42 passed` (2 archivos) | DB estable en baseline T27; solo `routers/sync.py` + `test_cortes.py`. Cambio: `operacion_uuid` opcional en datos → ejecutor con namespace `sync` y modo `offline`; sin UUID el camino no cambia (limitación retroactiva documentada, sin promesa). Conflicto cae en 409 existente vía `ValueError`. |
| T33 | Sin rojo: solo verificación final, sin cambios productivos nuevos | Verde: `69 + 2 + 8 + 10 + 2` por archivo (toda la suite backend) + `167 passed` aislada | DB estable en baseline T27 (`b691f8c5…`, ver divulgación T27); ningún `upgrade` contra base real ejecutado; `git status` solo este documento. Paquete 5 completo en cobertura parcial, sin declarar spec implementada; cierre pendiente de revisión independiente (`sdd-reviewer`), que no autoriza paquete 6. |

### Cierre del paquete 5 (revisión independiente)

`sdd-reviewer`: **APROBADO PAQUETE 5**, sin P1. Reejecutó todo (91 + 167, T31 6/6, upgrades en TEMP, hash DB idéntico). Aplicados sus P2 correspondientes: `ReintentosAgotados` → 500 en POST y sync (test determinista), header/tasks y MEMORY al día, redacción T27. Integrado a `dev` vía PR #27. El cierre no autoriza paquete 6 ni declara la spec implementada.

---

## Paquete 6 — Abonos y saldos independientes

Estado: **tareas redactadas, pendientes de aprobación para implementar**. Paquetes 1–5 cerrados, no rehacer.

Aprobación recibida: alcance aprobado por el usuario (RF-16–21, RF-37, bloqueo base RF-23/25). No se autoriza implementación por esta redacción.

### Alcance y límites

- Ocho tareas de 20–30 minutos: estimación 3–4 horas.
- Cobertura **parcial**: RF-16/RF-17 (movimientos por concepto), RF-18/RF-19 (independencia), RF-20 (saldar vía movimientos), RF-21 (totales/restante/estados, sin unknown/excedentes/revisión), RF-37 (cobro inicial), RF-41 (exceso online rechazado), RF-23/25 (bloqueo calculado desde primer pago). No afirma compensaciones/devoluciones (RF-43), revisión offline (RF-38/53), unknown (RF-44), edición/anulación ni cumplimiento integral.
- Decisiones registradas:
  - `MovimientoCorte`: UUID estable, corte, concepto (`cliente`/`comision`), tipo `abono`, importe canónico, autor, método propio, momento real (automático; admin puede indicarlo), registrado UTC. Append-only. Sin `Numeric` nuevo ambiguo: `Numeric(10,2)` con validación canónica en frontera (igual que `Corte`).
  - Obligación cliente = `precio` del corte; obligación comisión = `parte_barbero`. Saldo = obligación − neto (abonos aceptados); `max(..., 0)` con estados pendiente/parcial/pagado. Sin excedentes en este paquete: online el exceso se rechaza (RF-41); offline queda para sync.
  - Cobro inicial al registrar: `pendiente` (sin abono) / `parcial` (importe real obligatorio) / `completo` (importe = precio mostrado). No marca comisión como pagada.
  - Bloqueo: propiedad calculada `tiene_pagos` (existe movimiento) → helper `corte_bloqueado()`; la edición no existe aún (paquete 7).
  - Abono cero o negativo → 400 (RF-41 + sin movimiento de importe 0). Abono > saldo (online) → 400.
- Archivos que podrá tocar este paquete cuando se autorice implementar:
  - C `backend/app/models/finanzas_corte.py` (solo `MovimientoCorte` + enums).
  - M `backend/app/models/__init__.py` (solo registro).
  - C `backend/alembic/versions/003_movimientos_corte.py` (solo crea la tabla; idempotente; con guard ante tabla existente como `002`).
  - C `backend/app/services/movimiento_corte_service.py` (solo abonos + saldos + bloqueo).
  - M `backend/app/routers/cortes.py` (solo cobro inicial en registro).
  - C `backend/app/routers/movimientos_corte.py` (solo POST/GET movimientos por corte).
  - M `backend/app/main.py` (solo registro del router; sin tocar `create_all`).
  - M `backend/tests/test_cortes.py` (solo tests nuevos).
- Prohibido: compensaciones/devoluciones, revisión/dependientes, unknown, edición/anulación, jornadas, frontend, DTO personal (intacto), sync typed.
- **Gate de migración real** (igual que paquete 5): archivo commiteable; APLICAR `upgrade` contra base real exige aprobación + backup verificado + copia temporal primero. Durante el paquete, `upgrade` solo en TEMP; tests en DBs locales. Hash de `barberia.db` antes/después (baseline vigente `b691f8c5…`).

### Tareas en orden de dependencia

- [x] **T34. Tabla de movimientos + migración 003.** RF-16/RF-17 (base), RNF-3.
  - Dependencias: ninguna dentro del paquete.
  - Tests primero: `history` muestra `003`; `upgrade` en TEMP vacía crea solo `movimientos_corte`; en TEMP con legacy + `create_all` previo no toca nada (guard); repetir no-op.
  - Implementar: modelo + revisión solo-creación con guard de existencia.
  - Hecho cuando: escenarios TEMP verificados y prohibido aplicar contra base real.

- [x] **T35. Registrar abono parcial por concepto.** RF-16/RF-17 (parciales), RF-41.
  - Dependencias: T34.
  - Tests primero: POST abono cliente 30 sobre 100 → 201 con importe/metodo/momento propios; abono 0/negativo/3 decimales → 400; UUID de movimiento duplicado en reintento → un solo movimiento (reutilizar patrón idempotente: clave única por UUID).
  - Implementar: `POST /cortes/{id}/movimientos` (concepto, importe, método; momento automático, admin puede indicarlo) con validación canónica y titularidad (propio o admin gestión; ajeno 404).
  - Hecho cuando: tests API en verde y el abono conserva importe real sin normalizar.

- [x] **T36. Independencia de conceptos y saldado vía movimientos.** RF-18/RF-19/RF-20 (parciales).
  - Dependencias: T35.
  - Tests primero: abono cliente no mueve saldo comisión y viceversa; saldar el restante exacto cambia estado a pagado; no existe endpoint ni flag de "marcar pagado" (solo movimientos).
  - Implementar: saldos por concepto desde movimientos aceptados; endpoint separado `GET /cortes/{id}/saldos` con DTO personal (sin `parte_barberia`); el detalle no se toca.
  - Hecho cuando: tests en verde con ambos conceptos evolucionando por separado.

- [x] **T37. Totales, restante y estados.** RF-21 (parcial, sin unknown/excedentes/revisión).
  - Dependencias: T35–T36.
  - Tests primero: dos abonos 30+70 sobre 100 → total 100, restante 0, estado pagado; un abono 30 → parcial con restante 70; sin abonos → pendiente.
  - Implementar: cálculo puro de saldos (función testeable) + exposición en lectura.
  - Hecho cuando: matriz de estados en verde y unknown/excedentes explícitamente fuera (documentado, sin inventar).

- [ ] **T38. Cobro inicial al registrar.** RF-37 (parcial), RF-41.
  - Dependencias: T35.
  - Tests primero: `pendiente` no crea abono; `parcial` con importe 40 crea abono real de 40; `completo` crea abono por el precio mostrado; parcial sin importe → 400; completo no marca comisión como pagada.
  - Implementar: campos `cobro_inicial` + `importe_cobro` opcionales en el registro (propio y admin); el abono se crea en la misma UoW.
  - Hecho cuando: tests API en verde para las tres elecciones sin default.

- [ ] **T39. Exceso online rechazado + bloqueo calculado.** RF-41/RF-23/RF-25 (parciales).
  - Dependencias: T35–T38.
  - Tests primero: abono mayor al restante (online) → 400 sin crear movimiento; tras el primer abono `corte_bloqueado()` es verdadero y antes es falso.
  - Implementar: validación contra saldo en la UoW + helper de bloqueo (sin enforcement de edición aún: no existe edición).
  - Hecho cuando: tests en verde y ningún movimiento inválido persiste.

- [ ] **T40. Compatibilidad y privacidad de movimientos.** RF-14/RF-15 (regresión), RNF-3/RNF-5.
  - Dependencias: T35–T39.
  - Tests primero: barbero no opera sobre corte ajeno (404 idéntico); respuestas de movimientos/saldos sin `parte_barberia`/costos/márgenes (reutilizar detector T17); admin gestión conserva acceso.
  - Hecho cuando: verdes sin cambios productivos nuevos salvo ajustes exigidos por un rojo real.

- [ ] **T41. Regresión total y cierre del paquete.** RF-16–21/RF-37/RF-41/RF-23/25 (parciales), RNF-3/RNF-6.
  - Dependencias: T34–T40.
  - Ejecutar por archivo las suites tocadas + suite aislada del paquete 1, todo en verde, con precaución DB real + gate de migración registrados (ningún `upgrade` contra base real ejecutado).
  - Registrar comandos/resultados en la evidencia de abajo y actualizar el estado sin declarar implementada la spec completa. El cierre requiere revisión independiente (`sdd-reviewer`) y no autoriza paquete 7.
  - Hecho cuando: todo lo anterior en verde, solo los archivos autorizados cambiaron y queda solicitada la revisión de cierre.

### Evidencia futura (paquete 6)

| Tarea | Resultado inicial / causa | Resultado final | Comando / observaciones |
|---|---|---|---|
| T34 | Rojo real: `history` mostraba solo hasta `002` | Verde: `history` con `003`; TEMP vacía crea las 2 tablas nuevas; TEMP legacy + `create_all` dispara ambos guards sin tocar nada; repetir no-op | `upgrade` solo en TEMP; `barberia.db` hash estable en baseline T27 (`b691f8c5…`); prohibido aplicar contra base real. Modelo `finanzas_corte.py` (UUID única, concepto/tipo, importe, autor, método, momento nullable, registrado UTC) + `__init__` + revisión `003` con guard. |
| T35 | Rojo real: 4 failed (rutas inexistentes → 404) | Verde: `5 passed` nuevos | Desde `backend`: pytest por archivo. DIVULGACIÓN (mismo mecanismo T27): `barberia.db` ganó la tabla vacía `movimientos_corte` por `create_all` histórico (nuevo baseline `4c7f1b19…`; 0 filas, legacy y datos intactos: 1 admin, resto vacío). Solo `movimiento_corte_service.py` + `movimientos_corte.py` (router) + `main.py` (registro) + `test_cortes.py`. Modelos Pydantic en el router (sin archivo schema nuevo, dentro del alcance). |
| T36 | Rojo real: 2 failed (sin endpoint `/saldos`) + 1 ajuste cosmético (`'0'` vs `'0.00'`) | Verde: `73 passed` (3 archivos) | DB estable en baseline T35; solo `movimiento_corte_service.py` + `movimientos_corte.py` + `test_cortes.py`. Cambio: `calcular_saldo`/`saldos_corte` puros + `GET /{id}/saldos` personal (obligación = precio/parte_barbero, sin `parte_barberia`); presentación quantizada al centavo (valores exactos por construcción); sin endpoint de "marcar pagado" (404/405 verificado). |
| T37 | Verde inicial real (cubierto por T36; sin rojo artificial ni cambio productivo) | Mismo verde | Matriz 0/30/30+70 → pendiente/parcial-70/pagado-0. Unknown/excedentes explícitamente fuera. Solo `test_cortes.py` + este documento. |
| T38 |  |  |  |
| T39 |  |  |  |
| T40 |  |  |  |
| T41 |  |  |  |
