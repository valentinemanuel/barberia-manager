# Spec 002 — Registro de cortes del barbero

Estado: aprobada

## Contexto y objetivo

El registro de cortes es el flujo central del negocio: registrar el servicio realizado, calcular la parte del profesional, consultar su historial y seguir el dinero que falta cobrar o pagar. Existe un flujo básico, pero no basta con registrar online y enviar pendientes: deben mantenerse la fecha real, la identidad del barbero y la coherencia de las operaciones cuando se trabaja sin conexión.

Esta spec formaliza y amplía ese flujo con edición, anulación, cobros del cliente y pagos de comisión, incluidos pagos parciales. Evita que los reintentos dupliquen cortes o movimientos y que las correcciones del barbero alteren operaciones que ya tienen dinero registrado o pertenecen a un cierre de caja.

La autorización y privacidad de la spec 000 y la experiencia visual de la spec 001 siguen vigentes. Las decisiones de clarificación confirmadas están incorporadas y el usuario aprobó la spec completa y autorizó generar el plan. Las tareas y la implementación requieren aprobación posterior independiente.

## Usuarios

- **Barbero:** registra y consulta sus propios cortes, corrige los que no estén bloqueados y registra los cobros o pagos asociados a sus cortes.
- **Admin:** puede realizar el flujo propio, registrar cortes para cualquier barbero, introducir fechas anteriores y corregir cortes bloqueados con trazabilidad.

## Historias de usuario

- HU-1. Como barbero, quiero elegir un servicio y registrar mi corte para conocer mi comisión.
- HU-2. Como barbero, quiero registrar cortes sin conexión para continuar trabajando y sincronizarlos después.
- HU-3. Como barbero, quiero consultar mi historial y distinguir comisiones estimadas, confirmadas y pendientes de cobro para entender mis ingresos.
- HU-4. Como barbero, quiero editar o anular mis cortes cuando aún no tengan pagos ni pertenezcan a un cierre para corregir errores.
- HU-5. Como barbero, quiero registrar cobros del cliente y pagos de mi comisión, incluso parciales, para conocer ambos saldos pendientes.
- HU-6. Como admin, quiero registrar cortes anteriores para cualquier barbero usando los valores actuales para completar registros omitidos.
- HU-7. Como admin, quiero corregir operaciones bloqueadas conservando el registro y el motivo para mantener trazabilidad del negocio.

## Definiciones

- **Corte:** registro de un servicio realizado, asociado a un barbero, un momento de realización, un precio, un porcentaje y un reparto.
- **Momento real del corte:** fecha y hora en que se realizó el servicio. Es distinto del momento de creación del registro o de su sincronización.
- **Valores actuales:** precio del servicio y porcentaje del barbero vigentes cuando el sistema acepta inicialmente el registro con conexión. Para un registro offline, son los vigentes al aceptar su sincronización; para un registro retroactivo del admin, los vigentes al registrarlo, no los históricos de la fecha elegida.
- **Comisión:** parte del precio del servicio correspondiente al barbero. El porcentaje no se aplica a productos ni consumibles.
- **Pendiente de sincronización:** operación guardada en el dispositivo que todavía no ha sido aceptada por el sistema con conexión. Si la operación es el registro de un corte, su comisión se muestra como estimada porque los valores actuales pueden cambiar antes de aceptarlo. Los movimientos monetarios pendientes conservan su importe real y tienen los estados separados definidos en RF-53.
- **Deuda del cliente:** importe del servicio que el cliente todavía no ha pagado.
- **Comisión pendiente de cobro:** parte del barbero que todavía no se ha registrado como pagada al profesional por la barbería. No equivale a deuda del cliente ni a pendiente de sincronización.
- **Pago parcial:** movimiento que abona una parte del saldo de uno de los dos conceptos, sin saldar necesariamente el otro.
- **Corte bloqueado para el barbero:** corte que tiene al menos un cobro del cliente, al menos un pago de comisión, o que está incluido en un cierre de caja. El bloqueo de edición/anulación comienza desde el primer pago parcial, no desde el pago total.
- **Anulación:** cancelación del corte conservando su existencia y trazabilidad; no es un borrado irreversible.
- **Moneda:** pesos argentinos (ARS), con cien centavos por peso.
- **Redondeo matemático:** redondeo de la comisión al centavo más cercano; para importes no negativos, una fracción de medio centavo redondea hacia arriba. Por ejemplo, 0,024 pesos resulta en 0,02 y 0,025 pesos resulta en 0,03. La parte de la barbería es el resto exacto del precio.
- **Pendiente de revisión administrativa:** operación conservada para decisión del admin, distinta de una operación pendiente de envío, aceptada o rechazada. Su conservación no autoriza aplicar automáticamente una corrección ni reducir el importe monetario realmente registrado.
- **Movimiento compensatorio:** corrección administrativa vinculada al movimiento original, con motivo y trazabilidad, que corrige el registro sin borrarlo. No equivale por sí sola a devolver dinero realmente recibido o pagado.
- **Excedente y devolución:** el dinero realmente abonado de más se registra explícitamente como excedente. Si corresponde devolverlo, se registra una devolución explícita; no se considera devuelto automáticamente al corregir o anular.
- **Sin información de cobro/pago:** estado de cortes históricos sin evidencia suficiente de movimientos, independiente para deuda del cliente y comisión. No significa ni pagado ni pendiente.
- **Jornada real del movimiento:** jornada en que ocurrió el cobro o pago, distinta de la fecha del corte y de la aceptación del movimiento. Si ya está cerrada, su imputación se realiza como ajuste en la jornada abierta actual conservando el momento real y la referencia a la jornada original; si no existe jornada abierta, se aplica el estado pendiente de imputación de RF-50.
- **Jornada de negocio:** día calendario, de 00:00 inclusive a 00:00 del día siguiente exclusiva, en `America/Argentina/Buenos_Aires`. La jornada del servicio se determina por el momento real del corte y la del movimiento por su propio momento real.
- **Pendiente de imputación:** movimiento monetario aceptado cuyo destino contable requiere una jornada abierta que todavía no existe. Sí actualiza su saldo financiero; no equivale a un pago pendiente de envío o revisión y no reabre un cierre.
- **Saldo y excedente conocidos:** por cada concepto, saldo restante es el máximo entre obligación conocida menos dinero neto reconocido y cero; excedente es el máximo entre dinero neto reconocido menos obligación conocida y cero. El dinero neto reconocido conserva abonos, correcciones compensatorias y devoluciones explícitas, sin contar pendientes de envío/revisión ni rechazados. Los conceptos desconocidos permanecen desconocidos hasta completar evidencia.

## Requisitos funcionales

### Registro y cálculo

- RF-1: CUANDO un barbero registre un corte, EL SISTEMA lo asociará al propio barbero y permitirá seleccionar un servicio y un método de pago del conjunto existente: efectivo, tarjeta o transferencia.
- RF-2: CUANDO un admin registre un corte, EL SISTEMA permitirá asociarlo a cualquier barbero o registrar un corte propio.
- RF-3: CUANDO se acepte inicialmente un corte, EL SISTEMA calculará la comisión como precio del servicio multiplicado por el porcentaje del barbero dividido entre cien y calculará la parte de la barbería como precio menos comisión.
- RF-4: EL SISTEMA aplicará el porcentaje exclusivamente al servicio, sin sumar productos ni consumibles a la base del cálculo.
- RF-5: CUANDO se acepte un corte online, retroactivo o sincronizado, EL SISTEMA usará los valores actuales y conservará el precio, porcentaje y reparto aplicados a ese corte.
- RF-6: SI el precio del servicio o el porcentaje del barbero cambian después de aceptar un corte, ENTONCES EL SISTEMA no modificará automáticamente los importes ya registrados en ese corte.
- RF-7: CUANDO el usuario seleccione un servicio, EL SISTEMA mostrará su comisión calculada; MIENTRAS el corte esté pendiente de sincronización, EL SISTEMA identificará esa comisión como estimada y no como confirmada.

### Fecha y registros retroactivos

- RF-8: CUANDO un barbero registre un corte, EL SISTEMA tomará automáticamente el momento del registro como momento real del corte y no permitirá al barbero introducir ni editar manualmente esa fecha y hora.
- RF-9: CUANDO un corte se sincronice después de su realización, EL SISTEMA conservará su momento real aunque corresponda a un día anterior al de sincronización.
- RF-10: CUANDO un admin registre un corte, EL SISTEMA permitirá introducir una fecha y hora anteriores para cualquier barbero y utilizará únicamente los valores actuales; no permitirá introducir manualmente precios ni porcentajes históricos en este flujo.

### Historial y privacidad

- RF-11: CUANDO el barbero consulte su historial, EL SISTEMA mostrará exclusivamente sus cortes con servicio, momento real, método de pago, porcentaje aplicado, comisión, estado de sincronización, estado de anulación y estados de ambos saldos.
- RF-12: CUANDO el barbero consulte su acumulado, EL SISTEMA distinguirá comisión confirmada, comisión estimada pendiente de sincronización, comisión pagada y comisión pendiente de cobro, sin sumar las estimaciones como importes confirmados ni presentar comisiones históricas de pago desconocido como pendientes conocidas; identificará la información desconocida conforme a RF-44.
- RF-13: EL SISTEMA mantendrá separados el importe adeudado por el cliente y la comisión pendiente de pago al barbero, tanto en cada corte como en la consulta de saldos propios.
- RF-14: SI un barbero intenta consultar o modificar un corte o movimiento de otro profesional, ENTONCES EL SISTEMA impedirá la operación sin revelar la existencia del recurso, manteniendo el comportamiento de privacidad de la spec 000.
- RF-15: EL SISTEMA no expondrá al barbero totales brutos del negocio, datos de otros barberos, costos ni márgenes; un admin en una vista personal de barbero verá únicamente lo propio.

### Cobros del cliente y pagos de comisión

- RF-16: CUANDO un barbero opere sobre un corte propio o un admin opere sobre un corte bajo su gestión, EL SISTEMA permitirá registrar cobros del cliente y pagos de comisión al barbero como conceptos independientes.
- RF-17: CUANDO se registre un movimiento de uno de esos conceptos, EL SISTEMA permitirá un abono parcial o el pago del saldo restante y conservará el importe abonado, el concepto, el autor, el método propio del movimiento y su momento real. El método del corte será una propuesta, no prueba de cobro; cada movimiento podrá utilizar efectivo, tarjeta o transferencia independientemente de abonos anteriores.
- RF-18: CUANDO se acepte un cobro del cliente, EL SISTEMA actualizará el saldo de deuda del cliente sin marcar automáticamente la comisión del barbero como pagada.
- RF-19: CUANDO se acepte un pago de comisión al barbero, EL SISTEMA actualizará el saldo de comisión pendiente sin marcar automáticamente la deuda del cliente como cobrada.
- RF-20: CUANDO el usuario indique que un saldo está completamente pagado, EL SISTEMA lo reflejará mediante movimientos que salden el importe correspondiente, no mediante un cambio de estado que pierda el importe o su trazabilidad.
- RF-21: CUANDO se registren abonos sucesivos, EL SISTEMA mostrará el total abonado y el saldo restante por concepto, distinguiendo pendiente, parcialmente pagado y pagado; mostrará por separado información desconocida, movimientos pendientes de revisión y excedentes cuando corresponda, sin confundirlos con un pago confirmado ni con el saldo restante.
- RF-37: CUANDO se registre un corte, EL SISTEMA permitirá elegir cobro del cliente pendiente, parcial o completo; pendiente no creará un abono, parcial registrará el importe realmente abonado y completo registrará el importe correspondiente al precio mostrado al usuario. La elección no marcará automáticamente la comisión como pagada y estará sujeta a RF-38 al sincronizar.
- RF-38: SI un cobro del cliente o pago de comisión registrado offline supera el saldo definitivo al sincronizar, ENTONCES EL SISTEMA conservará el movimiento y su importe real como pendiente de revisión administrativa, sin reducirlo silenciosamente ni sustituir los valores actuales del corte por los valores cacheados.
- RF-41: CUANDO se introduzca un porcentaje o abono ordinario, EL SISTEMA admitirá porcentajes entre 0 y 100 inclusive con hasta dos decimales y abonos positivos con hasta dos decimales; SI la entrada incumple esas condiciones, ENTONCES EL SISTEMA la rechazará sin redondearla ni corregirla silenciosamente. SI un abono online supera el saldo disponible, ENTONCES EL SISTEMA lo rechazará; los excesos offline seguirán RF-38. Los abonos distintos concurrentes no podrán eludir esa validación. Las compensaciones y devoluciones son movimientos correctivos diferenciados, no abonos ordinarios; no se admitirán devoluciones superiores al dinero efectivamente abonado y todavía no devuelto del concepto correspondiente.
- RF-43: CUANDO un admin corrija un movimiento erróneo, EL SISTEMA registrará un movimiento compensatorio con motivo y referencia al original, sin eliminarlo; SI existe dinero realmente abonado de más, ENTONCES EL SISTEMA conservará el excedente y permitirá registrar su devolución explícita cuando corresponda, sin generarla automáticamente. Esta regla se aplicará por separado a cobros del cliente y pagos de comisión.

### Edición, anulación y bloqueo

- RF-22: MIENTRAS un corte propio no tenga cobros del cliente, pagos de comisión ni pertenezca a un cierre de caja, EL SISTEMA permitirá al barbero editar el servicio, método de pago y estado de cobro conforme al registro de movimientos definido anteriormente, o anular el corte.
- RF-23: CUANDO se registre el primer cobro del cliente o pago de comisión, aunque sea parcial, EL SISTEMA bloqueará la edición y anulación del corte para el barbero; el movimiento que inicia el bloqueo será permitido.
- RF-24: SI un corte está incluido en un cierre de caja, ENTONCES EL SISTEMA bloqueará su edición y anulación para el barbero aunque no tenga pagos registrados.
- RF-25: MIENTRAS el corte esté bloqueado para el barbero pero no anulado, EL SISTEMA permitirá registrar abonos adicionales autorizados; el bloqueo de edición/anulación no impedirá completar los pagos. Sobre anulados solo se permitirán ajustes y devoluciones administrativos conforme a RF-46.
- RF-26: CUANDO un admin corrija o anule un corte bloqueado, EL SISTEMA exigirá un motivo y conservará el autor, momento, valores anteriores y valores posteriores, sin eliminar los movimientos anteriores.
- RF-27: CUANDO se anule un corte, EL SISTEMA lo conservará identificado como anulado en el historial y no lo contará como servicio vigente ni como comisión devengada vigente; cancelará sus obligaciones pendientes conocidas y conservará los movimientos monetarios conforme a RF-46.
- RF-39: CUANDO un admin corrija una operación perteneciente a un cierre realizado, EL SISTEMA conservará el cierre original y registrará los ajustes posteriores con referencia a la operación y al cierre afectados; no reabrirá ni reemplazará el cierre original mediante esta corrección.
- RF-42: CUANDO se cambie el servicio de un corte mediante una edición autorizada, EL SISTEMA recalculará precio y porcentaje con los valores actuales y conservará el nuevo reparto; CUANDO solo se cambie el método de pago, EL SISTEMA conservará el precio, porcentaje y reparto anteriores. EL SISTEMA permitirá al admin corregir además el momento real y el barbero asignado, respetando el motivo, trazabilidad y ajustes requeridos para operaciones bloqueadas o cerradas.
- RF-46: CUANDO se anule un corte con información financiera conocida, EL SISTEMA cancelará las obligaciones del servicio y comisión correspondientes, conservará los movimientos y reflejará el dinero neto ya abonado como excedente a regularizar, sin devolución automática. SI la información previa de un concepto es desconocida, ENTONCES EL SISTEMA no inventará importes. Sobre un corte anulado no permitirá nuevos abonos ordinarios ni su reactivación mediante una edición; solo ajustes y devoluciones administrativos trazables.
- RF-47: CUANDO un admin cambie únicamente el barbero asignado, EL SISTEMA conservará el precio y aplicará el porcentaje actual del nuevo profesional; conservará los pagos al profesional anterior como movimientos de ese profesional y excedentes a regularizar, sin trasladarlos ficticiamente al nuevo, cuya comisión tendrá saldo independiente. CUANDO solo cambie la fecha, EL SISTEMA conservará precio, porcentaje y reparto. SI cambia servicio y barbero conjuntamente, ENTONCES EL SISTEMA aplicará el precio actual del servicio y el porcentaje actual del nuevo profesional.
- RF-48: CUANDO se reasigne un corte a otro barbero, EL SISTEMA retirará al anterior el acceso al corte y sus cambios posteriores; conservará únicamente sus justificantes monetarios propios, sin datos del nuevo titular, y aplicará el mismo aislamiento a la información local cuando se actualice la asignación.

### Históricos y jornadas

- RF-44: SI un corte anterior a esta funcionalidad no tiene información suficiente de cobro del cliente o pago de comisión, ENTONCES EL SISTEMA mostrará el concepto correspondiente como sin información, conservará la comisión registrada y no inventará movimientos ni lo tratará automáticamente como una deuda. Los acumulados identificarán los conceptos desconocidos sin presentarlos como saldos conocidos.
- RF-45: CUANDO se consulten o cierren jornadas, EL SISTEMA distinguirá servicios realizados de dinero efectivamente cobrado o pagado e imputará cada movimiento a su jornada real; SI esa jornada ya está cerrada, ENTONCES EL SISTEMA registrará el ajuste en la jornada abierta actual, manteniendo el cierre original, el momento real y la referencia a la jornada afectada. La recepción tardía de un corte no cambiará su momento real.
- RF-49: CUANDO se acepte un cierre de jornada, EL SISTEMA vinculará y bloqueará para el barbero los cortes incorporados de esa jornada conforme a su momento real. CUANDO acepte posteriormente un corte de esa jornada ya cerrada, EL SISTEMA también lo bloqueará y vinculará mediante un ajuste posterior, sin modificar el cierre original.
- RF-50: SI un movimiento aceptado requiere ajuste a una jornada abierta y no existe una, ENTONCES EL SISTEMA lo conservará como pendiente de imputación, mantendrá su dinero reconocido y saldo financiero, solicitará apertura administrativa y no reabrirá cierres automáticamente. CUANDO exista jornada abierta, EL SISTEMA permitirá imputar el ajuste conservando las referencias originales.
- RF-51: CUANDO el admin registre o corrija el momento real de un corte o movimiento, EL SISTEMA permitirá fechas anteriores sin límite de antigüedad y rechazará fechas futuras. CUANDO el barbero registre un movimiento, EL SISTEMA tomará automáticamente su momento, sin permitirle edición manual. SI un momento automático del dispositivo supera en más de cinco minutos el momento del servidor al sincronizar, ENTONCES EL SISTEMA conservará el original y la operación para revisión administrativa; el retraso de sincronización por sí solo no invalidará un momento pasado.
- RF-52: CUANDO se consulten acumulados, EL SISTEMA ofrecerá día, semana de lunes a domingo, mes y total, usando la jornada de negocio; agrupará comisiones por el momento del servicio y cobros/pagos por el momento del movimiento, mostrando por separado su imputación a cierres si difiere. No presentará un conjunto local incompleto como total definitivo.
- RF-53: CUANDO un movimiento esté pendiente de envío, revisión o rechazado, EL SISTEMA lo mostrará aparte con estado, causa e importe, sin reducir saldos aceptados. CUANDO un admin resuelva un exceso offline de dinero realmente abonado, EL SISTEMA reconocerá íntegramente su importe, aplicará hasta el saldo correspondiente y conservará el resto como excedente; SI el registro era erróneo, ENTONCES EL SISTEMA exigirá una corrección compensatoria con motivo. Un pendiente únicamente de imputación actualizará el saldo financiero conforme a RF-50.
- RF-54: CUANDO se complete información financiera histórica desconocida, EL SISTEMA permitirá hacerlo únicamente al admin con evidencia, autor y trazabilidad, sin sustituir una fecha histórica desconocida por la fecha actual.

### Operación offline y sincronización

- RF-28: MIENTRAS no haya conexión y exista información local suficiente, EL SISTEMA permitirá registrar cortes, consultar el historial disponible, realizar correcciones permitidas y registrar cobros y pagos, utilizando el último rol conocido y los datos disponibles.
- RF-29: CUANDO se confirme una operación offline, EL SISTEMA la conservará ante recarga o reapertura de la aplicación y mostrará que está pendiente de sincronización; no anunciará una aceptación definitiva que todavía no ha ocurrido.
- RF-30: CUANDO se recupere la conexión, EL SISTEMA sincronizará las operaciones pendientes y distinguirá las aceptadas con sus importes definitivos, las rechazadas con su motivo y las pendientes de revisión administrativa con su causa.
- RF-31: SI un servicio utilizado en un corte offline fue desactivado antes de sincronizar, ENTONCES EL SISTEMA aceptará ese corte usando los valores actuales del servicio y del barbero; la desactivación posterior no invalidará por sí sola el registro previo.
- RF-32: SI se reintenta una misma operación por pérdida de respuesta, reconexión o envío simultáneo, ENTONCES EL SISTEMA no creará cortes ni movimientos monetarios duplicados, ni recalculará como nuevo un corte ya aceptado.
- RF-33: CUANDO se cambie de cuenta en un dispositivo, EL SISTEMA mantendrá aislados el historial y los pendientes de cada usuario y no atribuirá ni enviará operaciones de una cuenta como si pertenecieran a otra; una respuesta tardía de una operación iniciada por la cuenta anterior no expondrá sus datos ni actualizará el historial o los saldos personales de la cuenta nueva.
- RF-34: CUANDO se sincronice una operación, EL SISTEMA revalidará el rol y estado activo del actor y las restricciones de pago/cierre vigentes; SI el rol o estado del actor ya no autorizan la operación, ENTONCES EL SISTEMA la rechazará y notificará al usuario conforme a la spec 000. La inactividad del barbero destinatario se tratará de forma distinta conforme a RF-56. Las ediciones/anulaciones de un barbero autorizado bloqueadas por un pago o cierre posterior se tratarán conforme a RF-40, sin ejecutarlas automáticamente.
- RF-35: SI no hay catálogo local suficiente para registrar un corte sin conexión, ENTONCES EL SISTEMA informará esa limitación sin confirmar un registro inexistente; SI una actualización de catálogo falla, ENTONCES EL SISTEMA conservará la última información local válida.
- RF-36: CUANDO existan ediciones concurrentes permitidas del mismo corte, EL SISTEMA resolverá mediante last-write-wins con timestamp cada unidad de conflicto: método de pago y momento real por separado, y servicio/barbero/precio/porcentaje/reparto como un grupo financiero coherente. No sobrescribirá cambios independientes ni combinará partes financieras de candidatos distintos; conservará autorización, bloqueos y movimientos monetarios distintos. Una anulación autorizada será terminal y prevalecerá sobre ediciones concurrentes, aunque tenga timestamp anterior; las ediciones no reactivarán el corte.
- RF-40: SI una edición o anulación realizada offline por el barbero llega después de que el corte quede bloqueado por un cobro del cliente, pago de comisión o cierre aceptado, ENTONCES EL SISTEMA conservará la operación pendiente de intervención administrativa, notificará el motivo y no la aplicará automáticamente, aunque su momento sea anterior al bloqueo. La anulación terminal de RF-36 solo se aplicará si está autorizada; no permitirá eludir el bloqueo de pagos/cierre ni otros permisos.
- RF-55: MIENTRAS se consulte el historial offline, EL SISTEMA mantendrá disponibles los últimos 90 días propios y, adicionalmente, cortes anteriores con saldos conocidos abiertos y todas las operaciones pendientes; mostrará la cobertura disponible y última actualización, sin presentar una suma local incompleta como total confirmado.
- RF-56: CUANDO se seleccione un servicio para un nuevo registro, EL SISTEMA permitirá servicios conocidos como activos; conservará la excepción de desactivación posterior de RF-31. CUANDO un admin registre retroactivos o corrija asignaciones, EL SISTEMA permitirá barberos inactivos si existe su información y porcentaje actual. SI un servicio o profesional no existe o carece de valores recuperables, ENTONCES EL SISTEMA conservará la operación y sus pagos dependientes para revisión administrativa, sin inventar valores ni identidad, aceptarla automáticamente o aplicar sus pagos a otro corte.
- RF-57: CUANDO se registre un corte y su cobro inicial o se envíen operaciones dependientes, EL SISTEMA mostrará el resultado del corte y de cada movimiento sin anunciar éxito completo si solo se aceptó parte; conservará identidades e importes para recuperar o reintentar sin duplicar. SI el corte es rechazado, ENTONCES EL SISTEMA conservará los dependientes sin aplicar e informará qué requiere subsanación; si un movimiento requiere revisión según RF-38, mostrará ese estado distinto de la aceptación del corte.

## Requisitos no funcionales

- RNF-1: EL SISTEMA calculará y conservará dinero en pesos argentinos con exactitud de centavos, sin errores de aritmética binaria fraccionaria; aplicará redondeo matemático a la comisión y calculará la parte de la barbería como resto exacto para que el reparto sume el precio del servicio.
- RNF-2: EL SISTEMA conservará los instantes en UTC y los mostrará en hora local, distinguiendo momento real del corte y momento de cada operación.
- RNF-3: EL SISTEMA mantendrá los contratos existentes compatibles; las capacidades nuevas no eliminarán las operaciones actuales de registro y consulta.
- RNF-4: EL SISTEMA conservará la experiencia visual unificada de la spec 001, con estados de carga, vacío, éxito, error, bloqueo y conexión identificables.
- RNF-5: EL SISTEMA mantendrá la privacidad tanto con conexión como sin ella; ocultar datos solo en pantalla no será suficiente para permitir su acceso a otra cuenta.
- RNF-6: EL SISTEMA permitirá verificar cada requisito mediante pruebas, incluyendo cálculo, permisos, pagos parciales, bloqueos, fecha real, reintentos y cambios de cuenta.

## Casos límite

- Precio o porcentaje cambian durante la desconexión: la comisión estimada puede diferir de la definitiva; el corte conserva su momento real.
- Un corte realizado ayer se sincroniza hoy: no constituye una introducción manual de fecha anterior por el barbero y conserva su fecha original.
- Admin registra hoy un corte de días anteriores: se aplica el precio y porcentaje actuales, no valores históricos.
- Servicio desactivado después de registrar offline: se acepta el corte. Servicio o profesional inexistente/sin información recuperable: conservar operación y pagos dependientes para revisión administrativa.
- Primer pago parcial, de cualquiera de los dos conceptos: bloquea edición/anulación del barbero desde ese movimiento.
- Cliente ha pagado todo y el barbero nada, o viceversa: los saldos no se confunden ni se completan automáticamente.
- Corte incluido en un cierre sin pagos: también bloqueado para el barbero.
- Pago/cierre y edición/anulación ocurren en distintos dispositivos: se revalida el bloqueo al sincronizar; correcciones del barbero bloqueadas quedan para intervención, sin ejecución automática.
- Se cobran 100 pesos offline y el saldo definitivo resulta en 80: se conservan los 100 en revisión; al reconocerlos el admin, 80 saldan el concepto y 20 quedan como excedente, sin devolución automática.
- Se cobran 100 pesos offline como pago completo y el precio definitivo aumenta a 120: el pago real permanece en 100 y el saldo restante queda en 20.
- Una edición offline del barbero llega después del primer pago aceptado: queda pendiente de intervención administrativa, sin eludir el bloqueo mediante su timestamp anterior.
- Se pierde la respuesta después de aceptar un corte o pago: el reintento no duplica la operación.
- Se cierra sesión y entra otro usuario con pendientes en el dispositivo: esos pendientes no se muestran ni sincronizan como propios del nuevo usuario.
- Usuario desactivado mientras opera offline: se revalidan y rechazan las acciones no permitidas al reconectar.
- Admin anula un corte con abonos o perteneciente a un cierre: conserva motivo, movimientos y cierre original; cancela obligaciones conocidas y refleja excedentes y ajustes posteriores, sin devolución automática ni nuevos abonos ordinarios al anulado.
- Comisión exacta de 0,025 pesos: se registra en 0,03 pesos y la barbería recibe el resto del precio, sin redondear ambas partes por separado.
- Porcentaje fuera de 0–100 o con más de dos decimales y abono no positivo o con más de dos decimales: rechazados, no normalizados silenciosamente.
- Cambio de servicio autorizado: se recalculan precio y porcentaje actuales. Cambio exclusivo de método de pago: conserva los importes.
- Corte histórico sin evidencia de pagos: estado sin información; conserva su comisión y no genera deudas ficticias.
- Movimiento erróneo corregido: compensación trazable, no borrado. Dinero abonado realmente de más: excedente y eventual devolución explícita.
- Abono adicional a un corte de una jornada cerrada: conserva su instante real; si la jornada del abono está abierta, se imputa a ella; si ya cerró, genera ajuste en la jornada abierta actual sin modificar cierres anteriores.
- No existe jornada abierta para un ajuste: el movimiento aceptado mantiene saldo financiero, queda pendiente de imputación y requiere apertura administrativa.
- Fecha futura introducida por admin: rechazada. Reloj automático más de cinco minutos adelantado: conservar original y operación para revisión, no sustituir por el momento de recepción.
- Reasignación con comisión abonada: conservar pagos propios del profesional anterior como excedente a regularizar; calcular comisión del nuevo sin transferirle ficticiamente esos pagos y sin revelar su identidad al anterior.
- Porcentaje 0 % o saldo restante cero: no generar abono ordinario de importe cero; un saldo conocido nulo no exige pago adicional.
- Anulación A(timestamp10) y edición E(timestamp11) concurrentes sobre una base activa, ambas autorizadas y sin bloqueo de pagos/cierre: el resultado queda anulado tanto en orden A→E como E→A; E no reactiva. Si la anulación no está autorizada, no se fuerza ese resultado ni se elude RF-40.
- Edición de método y edición de servicio concurrentes: ambas pueden conservarse por pertenecer a unidades distintas. Dos cambios del grupo financiero: se conserva íntegramente el candidato ganador por timestamp, no precio de uno y porcentaje de otro.

## Fuera de alcance

- Nuevos roles y cambios a la gestión de usuarios de la spec 000.
- Venta de productos, consumibles y comisiones sobre ellos.
- Gestión de clientes como módulo independiente; los saldos de esta spec pertenecen al corte.
- Liquidaciones agrupadas de varios cortes, nómina y transferencias bancarias automáticas.
- Introducción manual de precio o porcentaje histórico en cortes retroactivos.
- Borrado definitivo de cortes y movimientos como mecanismo de anulación.
- Rediseño general de la aplicación, nuevos reportes globales o exportaciones avanzadas.
- Cambios ajenos a este flujo detectados durante la investigación.
- Reactivación de cortes anulados, reapertura de cierres originales y conversión entre monedas.

## Criterios de finalización

- Todas las dudas que afectan comportamiento monetario, autorización o sincronización están resueltas y la spec está aprobada antes de implementar.
- Cada RF y RNF tiene evidencia de cumplimiento y las pruebas asociadas pasan.
- Un barbero registra un corte online y otro offline; ambos aparecen exclusivamente en su historial con el momento real, el reparto correspondiente y el estado correcto.
- Un admin registra un corte retroactivo para otro barbero con valores actuales, sin habilitar esa capacidad al barbero.
- Dos abonos del cliente y dos pagos de comisión actualizan de forma independiente sus saldos y distinguen estados parcial/total.
- El primer abono de cualquier concepto y la inclusión en un cierre bloquean edición/anulación para el barbero; un admin realiza correcciones con motivo y trazabilidad.
- El usuario puede elegir pendiente, parcial o completo al registrar, sin confundir el cobro del cliente con el pago de comisión.
- Un exceso monetario offline y una edición offline bloqueada por un pago posterior quedan conservados para revisión administrativa, no aplicados silenciosamente ni perdidos.
- Una corrección administrativa conserva el cierre original y registra ajustes posteriores trazables.
- Se rechazan entradas monetarias/porcentajes inválidos y excesos online, se verifican casos concurrentes y no se altera el importe real de un pago offline pendiente de revisión.
- Cambiar el servicio recalcula con valores actuales; cambiar solo el método de pago no modifica el reparto.
- Históricos sin evidencia de cobro/pago se presentan como sin información, no como pagos o deudas inventadas.
- Correcciones monetarias conservan originales y compensaciones; excedentes y devoluciones se identifican por separado y los cierres distinguen servicios de dinero efectivamente recibido/pagado.
- Reconexión, recarga, pérdida de respuesta y cambio de cuenta no provocan pérdida de operaciones confirmadas localmente, duplicación ni atribución cruzada.
- La aceptación de registros offline refleja cambios de precio/porcentaje y admite servicios desactivados posteriormente, sin trasladar el corte al día de sincronización.
- Se verifica la apertura o recarga sin conexión con datos previamente disponibles, no solo desconectar una pantalla ya abierta.
- No se exponen datos ajenos, costos, márgenes ni totales brutos del negocio al barbero.
- Anulación y reasignación conservan dinero, justificantes y límites de devoluciones, sin atribuir pagos a un profesional diferente ni permitir nuevos abonos al anulado.
- Cortes tardíos de una jornada cerrada quedan bloqueados; ajustes sin jornada abierta mantienen saldo financiero y quedan pendientes de imputación hasta apertura administrativa.
- Se verifica la zona de jornada, límites temporales y cobertura offline de 90 días más saldos abiertos y pendientes, identificando acumulados incompletos.

## Dudas abiertas

- Ninguna. DA-11 resuelta por aprobación explícita del usuario: anulación autorizada terminal y LWW por unidades independientes/grupo financiero coherente conforme a RF-36/RF-40. El usuario también autorizó división progresiva y creación de tareas solo para el primer paquete monetario puro; la implementación aún requiere aprobación independiente.

### Trazabilidad de dudas resueltas

- DA-1: ARS, redondeo matemático, precisión y validaciones (RNF-1/RF-41).
- DA-2: importes reales, saldo restante, revisión de excesos y estados financieros separados (RF-38/RF-41/RF-50/RF-53).
- DA-3: cancelación de obligaciones, excedentes, compensaciones, devoluciones limitadas y reasignación sin traslado ficticio de pagos (RF-26/RF-27/RF-43/RF-46/RF-47/RF-48).
- DA-4: método/momento propio, resultado por operación y recuperación de dependientes (RF-17/RF-37/RF-51/RF-57).
- DA-5: bloqueo prevalece, intervención administrativa y LWW solo para cambios permitidos, sin reactivación (RF-32/RF-34/RF-36/RF-40/RF-46).
- DA-6: recálculo por servicio/barbero y conservación por método/fecha (RF-42/RF-47).
- DA-7: actor activo, excepciones para destinatarios inactivos y revisión de información inexistente (RF-31/RF-34/RF-56).
- DA-8: zona de jornada, retroactivos sin límite, futuros rechazados y revisión de reloj adelantado más de cinco minutos (RF-8/RF-9/RF-10/RF-51).
- DA-9: históricos con evidencia administrativa, acumulados separados y cobertura offline (RF-12/RF-44/RF-52/RF-53/RF-54/RF-55).
- DA-10: pertenencia/bloqueo por cierre, cortes tardíos, ajustes posteriores y pendientes de imputación (RF-24/RF-39/RF-45/RF-49/RF-50).
- DA-11: anulación autorizada terminal; método/fecha independientes y servicio/barbero/reparto como grupo financiero coherente, con LWW entre ediciones permitidas y sin eludir bloqueos (RF-36/RF-40/RF-46).

## Decisiones confirmadas por el usuario

- Se aplican valores nuevos al aceptar la sincronización, no los cacheados al registrar offline.
- Un corte offline se acepta aunque su servicio haya sido desactivado antes de sincronizar.
- Se conserva el momento real del corte; solo el admin introduce manualmente registros de días anteriores.
- El admin puede registrar cortes para cualquier barbero usando exclusivamente valores actuales.
- El barbero puede editar y anular sus cortes conforme a los límites definidos.
- Se incluye historial propio, deuda del cliente y comisión pendiente del barbero, con pagos parciales en ambos conceptos.
- Admin y barbero pueden registrar cobros/pagos; el barbero actúa únicamente sobre sus propios cortes.
- El bloqueo de edición/anulación del barbero comienza desde el primer pago parcial de cualquiera de los conceptos o desde la inclusión en un cierre de caja.
- Las correcciones de cortes bloqueados corresponden al admin y conservan registro y motivo.
- Moneda ARS y redondeo matemático al centavo; mitad de centavo hacia arriba para importes no negativos.
- Al registrar se elige cobro del cliente pendiente, parcial o completo; no se eligió un valor predeterminado.
- Movimientos offline superiores al saldo definitivo: conservarlos pendientes de revisión administrativa.
- Correcciones sobre operaciones cerradas: conservar el cierre original y registrar ajustes posteriores.
- Edición offline recibida después del primer pago aceptado: conservarla pendiente de intervención administrativa.
- Porcentajes 0–100 inclusive con hasta dos decimales, abonos positivos con hasta dos decimales; entradas inválidas y excesos online rechazados.
- Cambiar servicio recalcula precio y porcentaje actuales; cambiar solo método de pago no recalcula. El admin puede corregir fecha y barbero.
- Históricos sin evidencia de pagos: sin información, conservando comisiones y sin inventar pagos/deudas.
- Correcciones monetarias mediante movimientos compensatorios con motivo; dinero realmente abonado de más como excedente y eventual devolución explícita, nunca automática.
- Separar servicios realizados de dinero efectivamente cobrado/pagado; movimientos en su jornada real y, si está cerrada, ajustes en la abierta actual, conservando la referencia original.
- Tercera ronda: aprobados los cinco paquetes sobre anulación/reasignación, jornadas/fechas, entidades inactivas/inexistentes, movimientos/conflictos y saldos/historial offline; reflejados en RF-46 a RF-57 y en las reglas anteriores actualizadas.
- El usuario aprobó la spec completa, la aclaración adicional de conflictos, la división progresiva y la creación de tareas del primer paquete monetario puro. La implementación y los paquetes posteriores aún requieren aprobación independiente.

## Registro de clarificación (2026-10-05)

- Primera revisión realizada por `sdd-clarifier`: resultado **requiere iteración**. La spec continúa en borrador y ninguna recomendación de negocio se considera aprobada sin respuesta del usuario.
- Bloqueantes: política monetaria y redondeo (DA-1); importes reales offline y abonos concurrentes que exceden saldo (DA-2); estado inicial y movimientos de pago (DA-4); correcciones con pagos y efecto sobre cierres (DA-3/DA-10); límites de last-write-wins frente a movimientos financieros y bloqueos (DA-5); recálculo en edición (DA-6); históricos sin evidencia de pago (DA-9); validación separada del actor y destinatario y entidades inexistentes (DA-7).
- También requieren precisión: jornada y límites temporales (DA-8), acumulados de movimientos pendientes/rechazados, alcance del historial offline, aislamiento de respuestas tardías tras cambiar de cuenta y recuperación de operaciones rechazadas y sus dependientes.
- Primera ronda de decisiones propuesta: redondeo/unidad monetaria, cobro inicial, dinero offline superior al saldo definitivo, correcciones sobre cierres realizados y edición offline recibida después del primer pago aceptado.
- Diferible al plan: mecanismos de persistencia, interfaces compatibles, identificadores idempotentes, transacciones e índices. Los efectos monetarios, los permisos y los resultados de conflictos deben resolverse antes.
- Alcance transversal: evaluar una división si el plan exige más de diez tareas, sin retirar funcionalidades acordadas ni avanzar de fase sin aprobación.
- Respuestas de primera ronda incorporadas: ARS/redondeo matemático, elección de cobro inicial, revisión de excesos offline, ajustes posteriores sin alterar cierre original e intervención administrativa para ediciones bloqueadas recibidas offline. RF-37 a RF-40 y RNF-1 reflejan estas decisiones; DA-1 a DA-5 conservan únicamente aspectos todavía no resueltos. La spec sigue en borrador.
- Respuestas de segunda ronda incorporadas en RF-41 a RF-45: precisión/validación, recálculo al editar servicio, corrección administrativa de fecha/barbero, históricos sin información, compensaciones/devoluciones y criterio de jornadas/ajustes. DA-1 resuelta; restantes dudas acotadas sin decidir permisos o efectos económicos adicionales por cuenta propia.
- Segunda revisión realizada por `sdd-clarifier`: **requiere iteración**. Cinco bloques de negocio restantes: anulación/reasignación con dinero y privacidad; pertenencia a cierre/fechas/jornada no abierta; entidades inactivas o inexistentes; datos de movimientos/conflictos/dependencias; saldos/revisión/históricos/cobertura offline. No se detectaron contradicciones nuevas inequívocas; las recomendaciones de estos bloques aún requieren aprobación.
- Correcciones editoriales incorporadas sin nuevas decisiones: RF-12/RF-21 reflejan información desconocida, revisión y excedentes ya aprobados; RF-41 distingue abonos ordinarios de movimientos correctivos; RF-33 cubre respuestas tardías tras cambiar de cuenta. No se cambian las reglas acordadas ni se inicia el plan.
- Usuario acepta íntegramente los cinco paquetes restantes. Incorporadas las políticas aprobadas y cerradas DA-1 a DA-10 con trazabilidad a RF. Revisión final pendiente; la spec completa continúa en borrador hasta aprobación explícita. No se ha iniciado ninguna fase posterior.
- Revisión final solicitada por el usuario y realizada por `sdd-clarifier`: **LISTA PARA PLAN**, sin contradicciones auténticas ni bloqueantes de negocio restantes. Ajustes editoriales incorporados: diferenciar comisión estimada del corte y estado de movimientos, y referencia expresa a falta de jornada abierta. No se exige atomicidad todo-o-nada del registro corte+pago; RF-57 conserva resultados individuales conforme a lo aprobado.
- Notas para el plan: persistencia e interfaces compatibles, idempotencia, desempate de timestamps, protección concurrente de saldos/devoluciones y pruebas combinadas. El plan deberá cumplir la representación monetaria constitucional y evaluar división del alcance antes de superar diez tareas. El dictamen técnico no sustituye la aprobación explícita de fases posteriores.
- Aprobación explícita del usuario: spec completa aprobada y generación de `plan.md` autorizada. Se inicia únicamente planificación con `sdd-planner`, sin tareas ni implementación.
- Auditoría del plan con `sdd-reviewer` solicitada antes de tareas: correcciones técnicas realizadas y DA-11 abierta por un caso concreto de anulación/edición concurrente y unidad LWW. Las decisiones previas siguen aprobadas; el nuevo caso requiere respuesta del usuario, no una política técnica inventada. La división del alcance en paquetes pequeños también está pendiente de aprobación. No se creó `tasks.md`.
- Respuesta posterior del usuario: aprueba regla recomendada (anulación autorizada terminal y LWW por método/fecha/grupo financiero) y división progresiva, con primer paquete de cálculo/validaciones puras y tests aislados, sin API/DB/sync. DA-11 cerrada; actualizar plan antes de crear tareas y verificar coherencia. No se autoriza implementación por esta aprobación documental.
