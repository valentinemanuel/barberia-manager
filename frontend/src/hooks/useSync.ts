import { useEffect, useState } from 'react'
import { useOnlineStatus } from './useOnlineStatus'
import { db } from '../services/db'
import api from '../services/api'

export function useSync() {
  const online = useOnlineStatus()
  const [sincronizando, setSincronizando] = useState(false)
  const [ultimaSync, setUltimaSync] = useState<Date | null>(null)

  useEffect(() => {
    if (online) {
      sincronizar()
    }
  }, [online])

  const sincronizar = async () => {
    setSincronizando(true)
    try {
      // Sincronizar cortes pendientes
      const cortesPendientes = await db.cortes
        .where('sincronizado')
        .equals(0)
        .toArray()

      for (const corte of cortesPendientes) {
        try {
          await api.post('/cortes/', {
            servicio_id: corte.servicio_id,
            metodo_pago: corte.metodo_pago,
          })
          await db.cortes.update(corte.id!, { sincronizado: true })
        } catch (error) {
          console.error('Error sincronizando corte:', error)
        }
      }

      // Actualizar datos locales desde el servidor
      const [servicios, productos, consumibles] = await Promise.all([
        api.get('/servicios/').catch(() => ({ data: [] })),
        api.get('/productos/').catch(() => ({ data: [] })),
        api.get('/consumibles/').catch(() => ({ data: [] })),
      ])

      await db.servicios.clear()
      await db.servicios.bulkPut(servicios.data)

      await db.productos.clear()
      await db.productos.bulkPut(productos.data)

      await db.consumibles.clear()
      await db.consumibles.bulkPut(consumibles.data)

      setUltimaSync(new Date())
    } catch (error) {
      console.error('Error en sincronización:', error)
    } finally {
      setSincronizando(false)
    }
  }

  return { sincronizando, ultimaSync, sincronizar }
}
