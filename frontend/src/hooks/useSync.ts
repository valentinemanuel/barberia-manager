import { useEffect, useState } from 'react'
import { useOnlineStatus } from './useOnlineStatus'
import { db } from '../services/db'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'

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
      // Camino v2 (paquete 8, T51): outbox por cuenta con UUID obligatoria.
      // La cuenta propietaria es el actor actual; solo se envían sus
      // pendientes (el aislamiento total A/B llega en T53).
      const actorId = useAuthStore.getState().usuario?.id ?? null
      if (actorId !== null) {
        const pendientesV2 = await db.outboxOperaciones
          .where('actorId')
          .equals(actorId)
          .filter((o) => o.estado === 'pendiente')
          .toArray()
        if (pendientesV2.length > 0) {
          try {
            for (const op of pendientesV2) {
              await db.outboxOperaciones.update(op.operacionUuid, {
                estado: 'enviando',
                intento: op.intento + 1,
              })
            }
            const respuesta = await api.post('/sync/', {
              operaciones: pendientesV2.map((op) => ({
                id: op.operacionUuid,
                accion: 'crear_corte_v2',
                datos: {
                  operacion_uuid: op.operacionUuid,
                  servicio_id: op.servicioId,
                  metodo_pago: op.metodoPago,
                  modo_captura: op.modoCaptura,
                  instante_cambio: op.instanteCambio,
                  momento_real: op.momentoReal,
                },
              })),
            })
            for (const resultado of respuesta.data.resultados ?? []) {
              if (resultado.aceptada) {
                await db.outboxOperaciones.update(resultado.id, {
                  estado: 'aceptada',
                  idServidor: resultado.corte_id,
                  actualizadoEn: new Date().toISOString(),
                })
                if (resultado.corte_id !== undefined && resultado.corte_id !== null) {
                  await db.mapeoOperaciones.put({
                    operacionUuid: resultado.id,
                    corteIdServidor: resultado.corte_id,
                  })
                }
              } else {
                await db.outboxOperaciones.update(resultado.id, {
                  estado: 'rechazada',
                  ultimoError: resultado.motivo ?? 'rechazada',
                  actualizadoEn: new Date().toISOString(),
                })
              }
            }
          } catch (error) {
            console.error('Error sincronizando outbox v2:', error)
          }
        }
      }

      // Sincronizar operaciones pendientes (cortes encolados mientras offline).
      // MIENTRAS offline, el rol usado es el último rol conocido cacheado
      // (authStore persistido); al sincronizar, el servidor revalida cada
      // operación contra el rol/activo vigente en DB (RF-17/18).
      // Los cortes pendientes se filtran en memoria: `sincronizado` se guarda
      // como boolean, y en IndexedDB los booleanos NO son claves válidas, así
      // que no entran al índice y where('sincronizado').equals(0) devuelve
      // siempre [] (verificado: 0 vs 1 con filter). Sin este filtro, los cortes
      // encolados offline nunca se sincronizan.
      const cortesPendientes = (
        await db.cortes.filter((c) => !c.sincronizado).toArray()
      ).filter((c) => !c.rechazado)

      if (cortesPendientes.length > 0) {
        try {
          const respuesta = await api.post('/sync/', {
            operaciones: cortesPendientes.map((corte) => ({
              id: String(corte.id),
              accion: 'crear_corte',
              datos: {
                servicio_id: corte.servicio_id,
                metodo_pago: corte.metodo_pago,
              },
            })),
          })
          const resultados = respuesta.data.resultados ?? []
          const rechazadas: string[] = []
          for (const resultado of resultados) {
            const corteLocal = cortesPendientes.find(
              (c) => String(c.id) === String(resultado.id)
            )
            if (!corteLocal) continue
            if (resultado.aceptada) {
              await db.cortes.update(corteLocal.id!, { sincronizado: true })
            } else {
              await db.cortes.update(corteLocal.id!, {
                rechazado: true,
                error_sync: resultado.motivo ?? 'rechazado',
              })
              rechazadas.push(resultado.notificacion ?? `Corte ${corteLocal.id} rechazado (409)`)
            }
          }
          if (rechazadas.length > 0) {
            window.alert(
              '⚠️ Algunas operaciones no se pudieron sincronizar:\n\n' +
                rechazadas.join('\n')
            )
          }
        } catch (error) {
          console.error('Error sincronizando cortes:', error)
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
