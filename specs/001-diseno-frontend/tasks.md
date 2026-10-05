# Tareas 001 — Sistema de diseño del frontend

- [x] **T1. Tokens y base CSS.** RF-5, RF-7
  - Hecho: `styles/tokens.css` + `styles/base.css`; `index.css` importa tokens/base/componentes/shell/login/vistas. Build pasa.
- [x] **T2. Kit de componentes ui.** RF-2, RF-3, RF-4, RF-5
  - Hecho: `components/ui/` (Boton, Tarjeta, Campo, Insignia, Cifra, Tabla, Vacio, Skeleton, Modal, Segmentado, Toast) exportados desde `index.ts`. Compila en strict mode.
- [x] **T3. Utilidades de formato.** RF-5
  - Hecho: `utils/formato.ts` sin `any`; incluye `pluralizar` y parseo local de fechas solo-fecha.
- [x] **T4. Shell Layout + App (rail/barra inferior, topbar, transición de ruta).** RF-1, RF-6, RF-7
  - Hecho: rail desktop ≥1024px, barra inferior móvil con "Más" (hoja modal), píldora de conexión en topbar, transición `animar-pagina`. Build pasa.
- [x] **T5. Login con momento de marca.** RF-5
  - Hecho: pantalla partida con poste barber animado (`franja-desliza`), tokens + kit. Captura `01`.
- [x] **T6. Dashboards admin y barbero.** RF-2, RF-3, RF-5
  - Hecho: ledger con cifra principal, listas de barberos/productos, skeletons, estados vacíos, sin emojis. Capturas `02`/`11`.
- [x] **T7. Registro de cortes.** RF-4, RF-5
  - Hecho: servicios como tarjetas seleccionables, pago con SegmentedControl + iconos, preview de ganancia, toast de éxito, guardado offline en IndexedDB. E2E verde.
- [x] **T8. Páginas de gestión (servicios, productos, usuarios).** RF-4, RF-5
  - Hecho: Modal/Toast/Insignia/Tabla del kit; confirmación de borrado con Modal; error de precio solo tras blur. Capturas `04`-`06`/`09`.
- [x] **T9. Reportes y cierre de caja.** RF-2, RF-4, RF-5
  - Hecho: skeleton en carga, toast al exportar, diferencia de caja con estados de color. Capturas `07`/`08`/`15`.
- [x] **T10. PWA (theme-color, preload) + ErrorBoundary.** RF-5
  - Hecho: `index.html` y `vite.config.ts` con `#17191c`/`#f5f2ec`; ErrorBoundary con kit.
- [x] **T11. Verificación visual con Playwright.** RF-1 a RF-8
  - Hecho: 15 capturas sin errores de consola; verificación programática del modal
    (overlay 1440×900, centrado, Escape cierra); E2E offline
    (encolar → reconectar → `sinc=True`). Scripts en `frontend/tests/visuales/`.

## Hallazgos fuera del alcance registrados durante la implementación
- **Bug sync (corregido, tocado `useSync.ts`)**: `where('sincronizado').equals(0)`
  devolvía siempre `[]` porque los booleanos no son claves válidas en IndexedDB.
  Verificado empíricamente (0 vs 1 con filter). Sin el fix, los cortes offline
  nunca se sincronizaban. Fix: filtro en memoria.
