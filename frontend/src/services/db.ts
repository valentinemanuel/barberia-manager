import Dexie, { Table } from 'dexie'

export interface CorteLocal {
  id?: number
  barbero_id: number
  servicio_id: number
  precio: number
  porcentaje_barbero: number
  parte_barbero: number
  metodo_pago: string
  fecha: string
  sincronizado: boolean
  rechazado?: boolean
  error_sync?: string
}

export interface ServicioLocal {
  id: number
  nombre: string
  descripcion: string
  precio: number
  duracion_minutos: number
  activo: boolean
}

export interface ProductoLocal {
  id: number
  nombre: string
  descripcion: string
  precio: number
  stock: number
  stock_minimo: number
  activo: boolean
}

export interface ConsumibleLocal {
  id: number
  nombre: string
  descripcion: string
  precio: number
  stock: number
  stock_minimo: number
  activo: boolean
}

export type EstadoOperacionLocal =
  | 'pendiente'
  | 'enviando'
  | 'aceptada'
  | 'rechazada'
  | 'revision'
  | 'dependiente'

export interface OperacionCorteLocal {
  operacionUuid: string
  corteUuid: string
  actorId: number
  servicioId: number
  metodoPago: string
  precioCentavos: number
  porcentajeCentesimas: number
  modoCaptura: 'online' | 'offline'
  instanteCambio: string
  momentoReal: string
  estado: EstadoOperacionLocal
  intento: number
  ultimoError?: string
  idServidor?: number
  actualizadoEn: string
  // Abono encadenado (T54, RF-37/RF-57): solo en filas tipo abono.
  // Campos opcionales: sin cambio de índices ni versión Dexie.
  tipo?: 'corte' | 'abono'
  concepto?: 'cliente' | 'comision'
  importeCentavos?: number
  dependeDe?: string
}

export interface MapeoOperacionLocal {
  operacionUuid: string
  corteIdServidor: number
}

class BarberiaDB extends Dexie {
  cortes!: Table<CorteLocal>
  servicios!: Table<ServicioLocal>
  productos!: Table<ProductoLocal>
  consumibles!: Table<ConsumibleLocal>
  outboxOperaciones!: Table<OperacionCorteLocal, string>
  mapeoOperaciones!: Table<MapeoOperacionLocal, string>

  constructor() {
    super('barberia_db')
    this.version(1).stores({
      cortes: '++id, barbero_id, servicio_id, fecha, sincronizado',
      servicios: 'id, nombre, activo',
      productos: 'id, nombre, activo',
      consumibles: 'id, nombre, activo',
    })
    // v2 aditiva (paquete 8, T50): conserva v1 y agrega outbox + mapeo
    // por cuenta. Índices string/number, nunca boolean como clave.
    this.version(2).stores({
      cortes: '++id, barbero_id, servicio_id, fecha, sincronizado',
      servicios: 'id, nombre, activo',
      productos: 'id, nombre, activo',
      consumibles: 'id, nombre, activo',
      outboxOperaciones: 'operacionUuid, actorId, estado, instanteCambio',
      mapeoOperaciones: 'operacionUuid',
    })
  }
}

export const db = new BarberiaDB()
