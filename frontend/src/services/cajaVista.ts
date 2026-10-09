/**
 * Vista de caja del admin (paquete 11, T79, RF-45 parcial).
 * Helpers puros sin DOM ni red: solo texto a partir de strings exactos
 * del API (sin `parseFloat` ni `Number`, sin aritmética binaria).
 */

export type EstadoJornadaVista = 'abierta' | 'cerrada';

/** Etiqueta legible del estado de la jornada. */
export function etiquetaEstadoJornada(estado: string): string {
  if (estado === 'cerrada') return 'Cerrada';
  return 'Abierta';
}

/** Aviso de pendientes solo cuando hay; `null` si cero. */
export function textoPendientes(cantidad: number): string | null {
  if (!Number.isSafeInteger(cantidad) || cantidad <= 0) return null;
  if (cantidad === 1) return '1 pendiente de imputación';
  return `${cantidad} pendientes de imputación`;
}

/** Línea de método con total exacto del API. */
export function lineaMetodo(metodo: string, total: string): string {
  return `${metodo}: $${total}`;
}

/** Balance cobrado vs pagado con textos exactos del API. */
export function textoBalance(cobros: string, pagos: string): string {
  return `Cobrado $${cobros} · Pagado $${pagos}`;
}
