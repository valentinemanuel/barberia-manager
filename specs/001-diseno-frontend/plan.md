# Plan 001 — Sistema de diseño del frontend

## Archivos a crear/Modificar

### Base (tokens y estilos)
- `frontend/src/styles/tokens.css` (nuevo): paleta Tinta & hueso, escala tipográfica Archivo,
  espaciado, radios, sombras, duraciones de animación, breakpoints.
- `frontend/src/styles/base.css` (nuevo): reset, tipografía base, foco visible, utilidades de
  layout reemplazando las clases muertas de Tailwind, prefers-reduced-motion.
- `frontend/src/index.css` (modificar): importa tokens + base y conserva las clases legacy que
  aún usan páginas no migradas.

### Kit de componentes (`frontend/src/components/ui/`)
- `Button.tsx`: variantes primary/secondary/success/danger/ghost, tamaños, estado cargando con spinner.
- `Card.tsx`: contenedor con encabezado opcional.
- `Field.tsx`: label + error + children (inputs/select heredan).
- `Badge.tsx`: variantes por semántica (rol, estado, stock).
- `Stat.tsx`: cifra con etiqueta y pie — formato tabular.
- `Table.tsx`: wrapper semántico con estilos.
- `EmptyState.tsx`: icono + título + texto + acción.
- `Skeleton.tsx`: líneas/bloques pulsantes.
- `Toast.tsx`: contexto + hook `useToast` (éxito/error/info), animación de entrada.
- `Modal.tsx`: overlay con focus trap básico, cierra con Escape.
- `SegmentedControl.tsx`: selector tipo radio con iconos (método de pago, filtros).
- `index.ts`: barril de exportaciones.

### Utilidades
- `frontend/src/utils/formato.ts` (nuevo): `formatearMoneda`, `formatearFecha`, `formatearHora`
  (fechas UTC→local). Funciones puras sin estado.

### Shell
- `frontend/src/components/Layout.tsx` (modificar): rail lateral (desktop ≥1024px) / barra
  inferior con iconos (móvil), topbar con usuario + indicador offline, transición de página.
- `frontend/src/components/OfflineIndicator.tsx` (modificar): píldora discreta en la topbar.
- `frontend/src/App.tsx` (modificar): envolver rutas con transición fade+slide y página 404.

### Páginas (migración al kit)
- `Login.tsx`: pantalla partida, momento de marca con la franja barber animada.
- `DashboardAdmin.tsx`: ledger del día (cifra principal + cortes), filas de top barberos y productos.
- `DashboardBarbero.tsx`: cifras propias, CTA principal a registrar corte.
- `RegistroCortes.tsx`: selector de servicios como tarjetas, SegmentedControl de pago, toast de éxito.
- `GestionServicios.tsx`, `GestionProductos.tsx`, `GestionUsuarios.tsx`: kit + Modal + toasts.
- `Reportes.tsx`: kit + skeleton.
- `CierreCaja.tsx`: kit + toast.
- `ErrorBoundary.tsx`: kit.

### PWA
- `frontend/index.html`: theme-color nuevo + preload de fuente.
- `frontend/vite.config.ts`: theme_color/background_color nuevos.

## Decisiones
- CSS plano con tokens (no Tailwind): ya elegido con el usuario; cero dependencias, offline-safe.
- Lucide React para iconos: tree-shakeable, SVG inline, no rompe PWA.
- Archivo Variable auto-hospedada vía @fontsource: sin CDN, funciona offline.
- Transiciones con CSS + keyframes (no framer-motion): peso mínimo; la animación responde a
  acción del usuario (cambio de ruta, apertura de modal, toast).

## Estrategia de tests
- Verificación con `npm run build` (tsc estricto + vite).
- Revisión visual con Playwright (webapp-testing) sobre login y dashboards.
