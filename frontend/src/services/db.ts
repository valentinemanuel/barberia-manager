import Dexie, { Table } from 'dexie'

export interface CorteLocal {
  id?: number
  barbero_id: number
  servicio_id: number
  precio: number
  porcentaje_barbero: number
  parte_barbero: number
  parte_barberia: number
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

class BarberiaDB extends Dexie {
  cortes!: Table<CorteLocal>
  servicios!: Table<ServicioLocal>
  productos!: Table<ProductoLocal>
  consumibles!: Table<ConsumibleLocal>

  constructor() {
    super('barberia_db')
    this.version(1).stores({
      cortes: '++id, barbero_id, servicio_id, fecha, sincronizado',
      servicios: 'id, nombre, activo',
      productos: 'id, nombre, activo',
      consumibles: 'id, nombre, activo',
    })
  }
}

export const db = new BarberiaDB()
