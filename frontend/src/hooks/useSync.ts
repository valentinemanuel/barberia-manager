import { useEffect, useState } from 'react'
import { useOnlineStatus } from './useOnlineStatus'
import { db } from '../services/db'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'
import { esRespuestaVigente, leerSesionNavegador } from '../services/sesion'
import { centavosAPesosStr } from '../services/operacionesCortes'

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
      // Foto de sesión (T53, RF-33): si cambia la cuenta a mitad del envío,
      // los resultados tardíos se descartan sin tocar la cuenta nueva.
      const actorId = useAuthStore.getState().usuario?.id ?? null
      const sesionCapturada = leerSesionNavegador()
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
              if (!esRespuestaVigente(sesionCapturada, leerSesionNavegador())) {
                console.warn('Sync: cambió la cuenta a mitad del envío; descarto resultados tardíos.')
                break
              }
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
      // Cadena de dependientes (T54, RF-57): abonos encadenados a su corte.
      // Si el corte fue rechazado, el abono queda `dependiente` conservado
      // sin aplicar; si el corte aún no sincronizó, se reintenta después.
      if (actorId !== null) {
        const abonosPendientes = await db.outboxOperaciones
          .where('actorId')
          .equals(actorId)
          .filter((o) => o.estado === 'pendiente' && o.tipo === 'abono')
          .toArray()
        for (const abono of abonosPendientes) {
          if (!esRespuestaVigente(sesionCapturada, leerSesionNavegador())) {
            console.warn('Sync: cambió la cuenta a mitad del envío; descarto resultados tardíos.')
            break
          }
          const corteOp = await db.outboxOperaciones.get(abono.dependeDe ?? '')
          if (!corteOp || corteOp.estado === 'pendiente' || corteOp.estado === 'enviando') {
            continue
          }
          if (corteOp.estado !== 'aceptada' || corteOp.idServidor == null) {
            await db.outboxOperaciones.update(abono.operacionUuid, {
              estado: 'dependiente',
              ultimoError: 'corte_rechazado',
              actualizadoEn: new Date().toISOString(),
            })
            continue
          }
          try {
            await db.outboxOperaciones.update(abono.operacionUuid, {
              estado: 'enviando',
              intento: abono.intento + 1,
            })
            const respuesta = await api.post('/sync/', {
              operaciones: [{
                id: abono.operacionUuid,
                accion: 'registrar_abono_v2',
                datos: {
                  operacion_uuid: abono.operacionUuid,
                  corte_id: corteOp.idServidor,
                  concepto: abono.concepto ?? 'cliente',
                  importe: centavosAPesosStr(abono.importeCentavos ?? 0),
                  metodo_pago: abono.metodoPago,
                  modo_captura: abono.modoCaptura,
                  momento_real: abono.momentoReal,
                },
              }],
            })
            const resultado = (respuesta.data.resultados ?? [])[0]
            if (!resultado) continue
            if (!esRespuestaVigente(sesionCapturada, leerSesionNavegador())) {
              console.warn('Sync: cambió la cuenta a mitad del envío; descarto resultados tardíos.')
              break
            }
            if (resultado.aceptada) {
              await db.outboxOperaciones.update(abono.operacionUuid, {
                estado: 'aceptada',
                actualizadoEn: new Date().toISOString(),
              })
            } else if (resultado.estado === 'revision') {
              await db.outboxOperaciones.update(abono.operacionUuid, {
                estado: 'revision',
                ultimoError: resultado.motivo ?? 'revision',
                actualizadoEn: new Date().toISOString(),
              })
            } else {
              await db.outboxOperaciones.update(abono.operacionUuid, {
                estado: 'dependiente',
                ultimoError: resultado.motivo ?? 'rechazado',
                actualizadoEn: new Date().toISOString(),
              })
            }
          } catch (error) {
            console.error('Error sincronizando abono dependiente:', error)
          }
        }
      }

      // Camino legacy (T53, RF-33): solo pendientes atribuibles a la cuenta
      // actual. Las filas v1 se atribuyen por `barbero_id` (sin autor
      // distinto: limitación documentada); las v2 viajan por outbox (arriba).
      const actorLegacy = useAuthStore.getState().usuario?.id ?? null
      const cortesPendientes = (
        await db.cortes.filter((c) => !c.sincronizado).toArray()
      ).filter((c) => !c.rechazado && (actorLegacy === null || c.barbero_id === actorLegacy))

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
            if (!esRespuestaVigente(sesionCapturada, leerSesionNavegador())) {
              console.warn('Sync: cambió la cuenta a mitad del envío; descarto resultados tardíos.')
              break
            }
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

      // Catálogo (RF-35, T55): reemplazo transaccional solo tras respuesta
      // validada. Un fallo conserva la última copia válida; sin catálogo
      // suficiente el registro informa la limitación sin confirmar nada.
      const [servicios, productos, consumibles] = await Promise.all([
        api.get('/servicios/').catch(() => null),
        api.get('/productos/').catch(() => null),
        api.get('/consumibles/').catch(() => null),
      ])
      const esListaValida = (r: unknown): r is { data: unknown[] } =>
        !!r &&
        typeof r === 'object' &&
        'data' in r &&
        Array.isArray((r as { data: unknown }).data)

      if (esListaValida(servicios) || esListaValida(productos) || esListaValida(consumibles)) {
        await db.transaction('rw', db.servicios, db.productos, db.consumibles, async () => {
          if (esListaValida(servicios)) {
            await db.servicios.clear()
            await db.servicios.bulkPut(servicios.data)
          }
          if (esListaValida(productos)) {
            await db.productos.clear()
            await db.productos.bulkPut(productos.data)
          }
          if (esListaValida(consumibles)) {
            await db.consumibles.clear()
            await db.consumibles.bulkPut(consumibles.data)
          }
        })
      } else {
        console.warn('Sync: sin catálogo del servidor; conservo la última copia válida.')
      }

      setUltimaSync(new Date())
    } catch (error) {
      console.error('Error en sincronización:', error)
    } finally {
      setSincronizando(false)
    }
  }

  return { sincronizando, ultimaSync, sincronizar }
}
