/**
 * Outbox de cortes (paquete 8, T50): helpers puros sin DOM ni red.
 * Dinero en centavos enteros y porcentaje en centésimas de punto,
 * conversión por dígitos (nunca `parseFloat`, `Number()` ni `*100` float).
 */

export type ModoCaptura = 'online' | 'offline';

export interface OperacionCorteNueva {
  operacionUuid: string;
  corteUuid: string;
  actorId: number;
  servicioId: number;
  metodoPago: string;
  precioCentavos: number;
  porcentajeCentesimas: number;
  modoCaptura: ModoCaptura;
  instanteCambioUtc: string;
  momentoRealUtc: string;
  estado: 'pendiente';
}

/** UUID v4: `crypto.randomUUID` con fallback sin dependencias. */
export function generarUuid(): string {
  const cripto = globalThis.crypto as unknown as
    | { randomUUID?: () => string; getRandomValues?: (a: Uint8Array) => void }
    | undefined;
  if (cripto?.randomUUID) return cripto.randomUUID();
  const bytes = new Uint8Array(16);
  if (cripto?.getRandomValues) {
    cripto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex: string[] = [];
  for (let i = 0; i < 16; i++) {
    const h = bytes[i].toString(16);
    hex.push(h.length === 1 ? '0' + h : h);
  }
  const s = hex.join('');
  return (
    s.slice(0, 8) + '-' + s.slice(8, 12) + '-' + s.slice(12, 16) +
    '-' + s.slice(16, 20) + '-' + s.slice(20)
  );
}

/**
 * `"100.00"` → `10000` centavos. Solo dígitos, 1–2 decimales.
 * Rechaza sin redondear ni corregir silenciosamente.
 */
export function pesosStrACentavos(pesos: string): number {
  if (typeof pesos !== 'string' || !/^\d+(\.\d{1,2})?$/.test(pesos)) {
    if (typeof pesos === 'string' && /^\d+\.\d{3,}$/.test(pesos)) {
      throw new Error('El importe debe tener como máximo dos decimales');
    }
    throw new Error('El importe tiene un formato inválido');
  }
  const [enteros, dec = ''] = pesos.split('.');
  const centavosStr = enteros + (dec + '00').slice(0, 2);
  // Suma dígito a dígito para no pasar por binario.
  let total = 0;
  for (let i = 0; i < centavosStr.length; i++) {
    total = total * 10 + (centavosStr.charCodeAt(i) - 48);
  }
  if (!Number.isSafeInteger(total)) {
    throw new Error('El importe excede el rango representable');
  }
  return total;
}

/** `3` → `"0.03"`. */
export function centavosAPesosStr(centavos: number): string {
  if (!Number.isSafeInteger(centavos) || centavos < 0) {
    throw new Error('Los centavos deben ser un entero no negativo');
  }
  const enteros = Math.floor(centavos / 100);
  const resto = centavos - enteros * 100;
  return enteros.toString() + '.' + (resto < 10 ? '0' : '') + resto.toString();
}

/**
 * Comisión estimada en centavos con mitad hacia arriba, solo enteros.
 * `porcentajeCentesimas`: 50.25% → `5025`. Usa BigInt para no exceder
 * el entero seguro en la multiplicación intermedia.
 */
export function estimarComisionCentavos(
  precioCentavos: number,
  porcentajeCentesimas: number,
): number {
  if (!Number.isSafeInteger(precioCentavos) || precioCentavos < 0) {
    throw new Error('El precio debe ser centavos enteros no negativos');
  }
  if (
    !Number.isSafeInteger(porcentajeCentesimas) ||
    porcentajeCentesimas < 0 ||
    porcentajeCentesimas > 10000
  ) {
    throw new Error('El porcentaje debe estar entre 0 y 100');
  }
  const resultado =
    (BigInt(precioCentavos) * BigInt(porcentajeCentesimas) + 5000n) / 10000n;
  if (resultado > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error('La comisión excede el rango representable');
  }
  return Number(resultado);
}

/** Crea la operación con un único instante capturado por el llamador. */
export function crearOperacionCorte(args: {
  actorId: number;
  servicioId: number;
  metodoPago: string;
  precioCentavos: number;
  porcentajeCentesimas: number;
  modoCaptura: ModoCaptura;
  ahora: Date;
}): OperacionCorteNueva {
  if (!Number.isSafeInteger(args.actorId) || args.actorId <= 0) {
    throw new Error('El actor debe ser un id válido');
  }
  if (!Number.isSafeInteger(args.servicioId) || args.servicioId <= 0) {
    throw new Error('El servicio debe ser un id válido');
  }
  if (!(args.ahora instanceof Date) || Number.isNaN(args.ahora.getTime())) {
    throw new Error('El instante de captura debe ser una fecha válida');
  }
  // Valida importes sin calcular de más: reutiliza los guards exactos.
  centavosAPesosStr(args.precioCentavos);
  estimarComisionCentavos(args.precioCentavos, args.porcentajeCentesimas);
  const instante = args.ahora.toISOString();
  return {
    operacionUuid: generarUuid(),
    corteUuid: generarUuid(),
    actorId: args.actorId,
    servicioId: args.servicioId,
    metodoPago: args.metodoPago,
    precioCentavos: args.precioCentavos,
    porcentajeCentesimas: args.porcentajeCentesimas,
    modoCaptura: args.modoCaptura,
    instanteCambioUtc: instante,
    momentoRealUtc: instante,
    estado: 'pendiente',
  };
}

export type ConceptoAbono = 'cliente' | 'comision';

export interface OperacionAbonoNueva {
  operacionUuid: string;
  actorId: number;
  /** UUID del corte original (no un id reasignable): cadena de dependencia. */
  dependeDe: string;
  concepto: ConceptoAbono;
  importeCentavos: number;
  modoCaptura: ModoCaptura;
  instanteCambioUtc: string;
  momentoRealUtc: string;
  estado: 'pendiente';
}

/**
 * Crea un abono encadenado a su corte (RF-37/RF-57, T54). El importe es el
 * realmente indicado (para `completo`, el precio mostrado al usuario, no un
 * recálculo posterior); nunca se genera un abono de importe cero.
 */
export function crearOperacionAbono(args: {
  actorId: number;
  corteUuid: string;
  concepto: string;
  importeCentavos: number;
  modoCaptura: ModoCaptura;
  ahora: Date;
}): OperacionAbonoNueva {
  if (!Number.isSafeInteger(args.actorId) || args.actorId <= 0) {
    throw new Error('El actor debe ser un id válido');
  }
  if (typeof args.corteUuid !== 'string' || args.corteUuid.length === 0) {
    throw new Error('El abono debe referenciar su corte original');
  }
  if (args.concepto !== 'cliente' && args.concepto !== 'comision') {
    throw new Error('El concepto debe ser cliente o comision');
  }
  if (!Number.isSafeInteger(args.importeCentavos) || args.importeCentavos <= 0) {
    throw new Error('Los centavos deben ser un entero positivo');
  }
  if (!(args.ahora instanceof Date) || Number.isNaN(args.ahora.getTime())) {
    throw new Error('El instante de captura debe ser una fecha válida');
  }
  const instante = args.ahora.toISOString();
  return {
    operacionUuid: generarUuid(),
    actorId: args.actorId,
    dependeDe: args.corteUuid,
    concepto: args.concepto,
    importeCentavos: args.importeCentavos,
    modoCaptura: args.modoCaptura,
    instanteCambioUtc: instante,
    momentoRealUtc: instante,
    estado: 'pendiente',
  };
}
