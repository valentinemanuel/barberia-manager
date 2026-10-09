/**
 * Formateo compartido por todas las pantallas.
 * Funciones puras: sin estado, sin acceso a DOM.
 *
 * Convención de moneda (spec 001): `$1,234.56` — agrupación de miles
 * con coma y dos decimales, cercano al formato actual de la app.
 */

const formateadorMoneda = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const formateadorEntero = new Intl.NumberFormat('en-US')

/**
 * Convierte una fecha recibida del backend a Date local.
 * Clave: los strings de solo fecha (`'2026-10-05'`) son días de calendario,
 * no instantes — si se parsean como UTC, en América retrocede un día.
 */
function aFechaLocal(fechaUtc: string | Date): Date {
  if (fechaUtc instanceof Date) return fechaUtc

  const soloFecha = /^\d{4}-\d{2}-\d{2}$/.test(fechaUtc)
  if (soloFecha) {
    const [anio, mes, dia] = fechaUtc.split('-').map(Number)
    return new Date(anio, mes - 1, dia)
  }
  return new Date(fechaUtc)
}

/** `1 corte` / `2 cortes` — evita "1 cortes". */
export function pluralizar(
  cantidad: number,
  singular: string,
  plural: string
): string {
  return cantidad === 1 ? singular : plural
}

/** Formatea un monto como `$1,234.56`. */
export function formatearMoneda(monto: number): string {
  return `$${formateadorMoneda.format(monto)}`
}

/**
 * Formatea un string exacto del API como `$1,234.56` (paquete 12, T82).
 * Sin pasar por binario: agrupa miles por dígitos y conserva 2 decimales.
 */
export function formatearMonedaExacta(pesos: string): string {
  const limpio = pesos.trim()
  const partes = limpio.split('.')
  if (partes.length > 2 || !/^\d+$/.test(partes[0]) || (partes[1] !== undefined && !/^\d{1,2}$/.test(partes[1]))) {
    throw new Error('El importe exacto debe ser dígitos con dos decimales como máximo')
  }
  const enteros = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const dec = (partes[1] ?? '').padEnd(2, '0')
  return `$${enteros}.${dec}`
}

/** Formatea un entero con separador de miles: `1,250`. */
export function formatearEntero(valor: number): string {
  return formateadorEntero.format(valor)
}

/**
 * Convierte una fecha UTC (string ISO o Date del backend) a fecha local legible.
 * Regla de la constitución: UTC en backend, local en frontend.
 */
export function formatearFecha(fechaUtc: string | Date): string {
  const fecha = aFechaLocal(fechaUtc)
  return fecha.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

/** Hora local en formato 24h: `14:30`. */
export function formatearHora(fechaUtc: string | Date): string {
  const fecha = aFechaLocal(fechaUtc)
  return fecha.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Fecha corta para listas: `4 oct` (sin año si es el actual). */
export function formatearFechaCorta(fechaUtc: string | Date): string {
  const fecha = aFechaLocal(fechaUtc)
  const anioActual = new Date().getFullYear()
  return fecha.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    ...(fecha.getFullYear() === anioActual ? {} : { year: 'numeric' }),
  })
}
