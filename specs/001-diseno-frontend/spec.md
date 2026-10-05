# Spec 001 — Sistema de diseño del frontend

Estado: aprobada

## Contexto y objetivo
El frontend actual no tiene sistema de diseño: usa clases utilitarias de Tailwind que no existen
en el proyecto (el paquete no está instalado), iconos con emojis, tarjetas sin jerarquía y estados
de carga/datos vacíos pobres. Se busca una plantilla visual única, moderna y cómoda para admin y
barbero, con animaciones discretas que respondan a la acción del usuario.

## Usuarios
- Dueño/admin: gestiona el negocio desde escritorio y móvil, prioriza cifras claras y tablas.
- Barbero: registra cortes desde el móvil con una mano, prioriza rapidez y ver su ganancia.

## Historias de usuario
- HU-1. Como admin, quiero ver el resumen del día jerarquizado, para entender el negocio de un vistazo.
- HU-2. Como barbero, quiero registrar un corte en pocos toques desde el móvil, para no perder tiempo en la silla.
- HU-3. Como usuario, quiero animaciones suaves al cambiar de pantalla, para que la app se sienta fluida.
- HU-4. Como usuario, quiero indicadores claros de carga y estado offline, para saber en qué estado está la app.

## Requisitos funcionales
- RF-1: CUANDO el usuario cambie de pantalla, EL SISTEMA transicionará con fade+desplazamiento de 220ms.
- RF-2: CUANDO una pantalla esté cargando datos, EL SISTEMA mostrará skeletons en lugar de texto plano.
- RF-3: CUANDO una lista esté vacía, EL SISTEMA mostrará un estado vacío con acción sugerida.
- RF-4: CUANDO el usuario realice una acción (guardar, eliminar, cerrar caja), EL SISTEMA mostrará un toast con el resultado.
- RF-5: EL SISTEMA usará una paleta, escala tipográfica y componentes únicos en todas las pantallas.
- RF-6: CUANDO el dispositivo esté offline o sincronizando, EL SISTEMA mostrará un indicador en la barra superior.
- RF-7: SI la animación está deshabilitada por el sistema operativo, ENTONCES EL SISTEMA respetará prefers-reduced-motion.
- RF-8: EL SISTEMA usará iconos SVG (lucide) en lugar de emojis.

## Requisitos no funcionales
- RNF-1: Sin nuevas dependencias pesadas; PWA debe seguir funcionando offline (fuentes auto-hospedadas).
- RNF-2: TypeScript estricto; sin `any`.
- RNF-3: Contraste AA en texto; foco de teclado visible.
- RNF-4: El barbero no ve totales brutos ni datos de otros (se mantiene la regla de privacidad).

## Casos límite
- Pantalla muy angosta (360px): el nav pasa a barra inferior con iconos.
- Listas largas de servicios/productos: scroll propio con tarjetas compactas.
- Error de red al registrar corte: se guarda localmente (IndexedDB) y se informa en el toast.

## Fuera de alcance
- Nuevos endpoints o cambios de API.
- Modo oscuro.
- Cambios en reglas de negocio de porcentajes.

## Criterios de finalización
- Todas las pantallas usan el kit de componentes (`src/components/ui`) y los tokens (`src/styles/`).
- `npm run build` (tsc + vite) pasa sin errores.
- Sin emojis como iconografía; sin clases muertas de Tailwind.

## Dudas abiertas
- Formato de moneda: se mantiene estilo `$1,234.56` (agrupación de miles, 2 decimales) por cercanía
  al comportamiento actual; ajustable por locale cuando se defina el país.
