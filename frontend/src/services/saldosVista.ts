/**
 * Vista de saldos del titular (paquete 9, T64, RF-12/RF-21 parcial).
 * Helpers puros sin DOM ni red: el excedente va separado del restante,
 * la revisión se muestra aparte con causa e importe (nunca como saldo),
 * y los motivos propios se listan sin datos ajenos.
 */

export interface SaldoVista {
  obligacion: string;
  abonado: string;
  restante: string;
  excedente: string;
  estado: string;
}

export interface MovimientoVista {
  uuid: string;
  concepto: string;
  importe: string;
  estado?: string | null;
  motivo_revision?: string | null;
  tipo?: string | null;
  motivo?: string | null;
}

/** Texto del excedente solo cuando hay sobrante; `null` si es cero. */
export function textoExcedente(saldo: { excedente: string }): string | null {
  const valor = Number(saldo.excedente);
  if (!Number.isFinite(valor) || valor <= 0) return null;
  return `Excedente $${saldo.excedente}`;
}

/** Revisiones visibles: causa e importe, una línea por fila en revisión. */
export function revisionesVisibles(movimientos: MovimientoVista[]): string[] {
  return movimientos
    .filter((m) => m.estado === 'revision')
    .map((m) => `Revisión: $${m.importe} (${m.motivo_revision ?? 'en revisión'})`);
}

/** Movimientos agrupados por concepto, en orden de llegada. */
export function agruparPorConcepto(movimientos: MovimientoVista[]): {
  cliente: MovimientoVista[];
  comision: MovimientoVista[];
} {
  const cliente: MovimientoVista[] = [];
  const comision: MovimientoVista[] = [];
  for (const m of movimientos) {
    if (m.concepto === 'comision') comision.push(m);
    else cliente.push(m);
  }
  return { cliente, comision };
}

/** Motivos no vacíos de las filas visibles al titular. */
export function motivosVisibles(movimientos: MovimientoVista[]): string[] {
  const salida: string[] = [];
  for (const m of movimientos) {
    if (m.motivo && m.motivo.trim().length > 0) salida.push(m.motivo);
  }
  return salida;
}
