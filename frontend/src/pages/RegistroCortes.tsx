import { useEffect, useState } from 'react'
import { CheckCircle2, CreditCard, Landmark, Banknote } from 'lucide-react'
import { useLiveQuery } from 'dexie-react-hooks'
import api from '../services/api'
import { mensajeError } from '../services/error'
import { useAuthStore } from '../store/authStore'
import { db } from '../services/db'
import {
  centavosAPesosStr,
  crearOperacionAbono,
  crearOperacionCorte,
  estimarComisionCentavos,
  pesosStrACentavos,
} from '../services/operacionesCortes'
import { Boton, Campo, Segmentado, Vacio, useToast } from '../components/ui'
import { formatearMoneda } from '../utils/formato'

interface Servicio {
  id: number
  nombre: string
  descripcion: string
  precio: number
  duracion_minutos: number
}

type MetodoPago = 'efectivo' | 'tarjeta' | 'transferencia'

/**
 * Registrar un corte: los servicios se eligen como tarjetas (un toque,
 * sin dropdown) y el método de pago con control segmentado.
 * Si la red falla, el corte se guarda en el dispositivo y se sincroniza después.
 */
export default function RegistroCortes() {
  const { usuario } = useAuthStore()
  const { mostrar } = useToast()
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [servicioSeleccionado, setServicioSeleccionado] = useState<number | null>(null)
  const [metodoPago, setMetodoPago] = useState<MetodoPago>('efectivo')
  // Cobro inicial del cliente (RF-37, T54): sin elección obligatoria,
  // pendiente no crea abono; parcial/completo registran dinero real.
  const [cobro, setCobro] = useState<'pendiente' | 'parcial' | 'completo'>('pendiente')
  const [importeCobro, setImporteCobro] = useState('')
  const [cargando, setCargando] = useState(false)
  const [ultimoExito, setUltimoExito] = useState<string | null>(null)
  const [sinServicios, setSinServicios] = useState(false)

  useEffect(() => {
    cargarServicios()
  }, [])

  const cargarServicios = async () => {
    try {
      const response = await api.get('/servicios/')
      setServicios(response.data)
      setSinServicios(response.data.length === 0)
    } catch (error) {
      console.error('Error cargando servicios, pruebo los locales:', error)
      // Fallback offline: servicios cacheados en IndexedDB.
      // `activo` es boolean y en IndexedDB los booleanos NO son claves
      // válidas (mismo patrón que el fix de `sincronizado` en useSync):
      // se filtra en memoria en vez de where('activo').equals(1).
      const locales = await db.servicios.filter((s) => s.activo).toArray()
      setServicios(locales as Servicio[])
      setSinServicios(locales.length === 0)
    }
  }

  const servicio = servicios.find((s) => s.id === servicioSeleccionado) ?? null
  // Estimada exacta en centavos enteros (paquete 8, T50): sin `*100` float.
  // Si el precio/porcentaje no son recuperables, no se muestra estimada.
  let gananciaCentavos: number | null = null
  if (servicio && usuario) {
    try {
      const precioCentavos = pesosStrACentavos(servicio.precio.toFixed(2))
      const porcentajeCentesimas = Math.round(usuario.porcentaje_ganancia * 100)
      gananciaCentavos = estimarComisionCentavos(precioCentavos, porcentajeCentesimas)
    } catch {
      gananciaCentavos = null
    }
  }
  const ganancia = gananciaCentavos === null ? 0 : gananciaCentavos / 100
  // Pendientes visibles de la cuenta actual (RF-29): sobrevive a recarga
  // porque la outbox es durable en IndexedDB.
  const pendientes = useLiveQuery(
    () =>
      usuario
        ? db.outboxOperaciones
            .where('actorId')
            .equals(usuario.id)
            .filter((o) => o.estado === 'pendiente' || o.estado === 'enviando')
            .count()
        : Promise.resolve(0),
    [usuario?.id],
    0,
  )

  const registrar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!servicio) return

    setCargando(true)
    setUltimoExito(null)

    // Persist-first (paquete 8, T50): instante único capturado aquí y
    // guardado en la outbox ANTES de intentar red. Si falla la
    // persistencia, no se anuncia ningún guardado.
    if (!usuario) {
      mostrar('error', 'Sesión no disponible')
      setCargando(false)
      return
    }
    const ahora = new Date()
    let operacionUuid = ''
    let corteUuid = ''
    // Importe del cobro inicial en centavos exactos (null = pendiente).
    // `completo` usa el precio MOSTRADO (snapshot), no un recálculo posterior.
    let cobroCentavos: number | null = null
    try {
      const precioCentavos = pesosStrACentavos(servicio.precio.toFixed(2))
      if (cobro === 'parcial') {
        cobroCentavos = pesosStrACentavos(importeCobro.trim())
      } else if (cobro === 'completo') {
        cobroCentavos = precioCentavos
      }
    } catch {
      mostrar('error', 'El importe del cobro debe ser positivo con dos decimales como máximo')
      setCargando(false)
      return
    }
    try {
      const precioCentavos = pesosStrACentavos(servicio.precio.toFixed(2))
      const porcentajeCentesimas = Math.round(usuario.porcentaje_ganancia * 100)
      const operacion = crearOperacionCorte({
        actorId: usuario.id,
        servicioId: servicio.id,
        metodoPago,
        precioCentavos,
        porcentajeCentesimas,
        modoCaptura: navigator.onLine ? 'online' : 'offline',
        ahora,
      })
      operacionUuid = operacion.operacionUuid
      corteUuid = operacion.corteUuid
      const abono =
        cobroCentavos === null
          ? null
          : crearOperacionAbono({
              actorId: usuario.id,
              corteUuid: operacion.corteUuid,
              concepto: 'cliente',
              importeCentavos: cobroCentavos,
              modoCaptura: navigator.onLine ? 'online' : 'offline',
              ahora,
            })
      // Una transacción: corte + abono dependiente (misma suerte durable).
      await db.transaction('rw', db.outboxOperaciones, async () => {
        await db.outboxOperaciones.add({
          operacionUuid: operacion.operacionUuid,
          corteUuid: operacion.corteUuid,
          actorId: operacion.actorId,
          servicioId: operacion.servicioId,
          metodoPago: operacion.metodoPago,
          precioCentavos: operacion.precioCentavos,
          porcentajeCentesimas: operacion.porcentajeCentesimas,
          modoCaptura: operacion.modoCaptura,
          instanteCambio: operacion.instanteCambioUtc,
          momentoReal: operacion.momentoRealUtc,
          estado: 'pendiente',
          intento: 0,
          actualizadoEn: operacion.instanteCambioUtc,
          tipo: 'corte',
        })
        if (abono) {
          await db.outboxOperaciones.add({
            operacionUuid: abono.operacionUuid,
            corteUuid: abono.dependeDe,
            actorId: abono.actorId,
            servicioId: operacion.servicioId,
            metodoPago: operacion.metodoPago,
            precioCentavos: operacion.precioCentavos,
            porcentajeCentesimas: operacion.porcentajeCentesimas,
            modoCaptura: abono.modoCaptura,
            instanteCambio: abono.instanteCambioUtc,
            momentoReal: abono.momentoRealUtc,
            estado: 'pendiente',
            intento: 0,
            actualizadoEn: abono.instanteCambioUtc,
            tipo: 'abono',
            concepto: abono.concepto,
            importeCentavos: abono.importeCentavos,
            dependeDe: abono.dependeDe,
          })
        }
      })
    } catch (error) {
      mostrar('error', mensajeError(error, 'No se pudo guardar la operación'))
      setCargando(false)
      return
    }

    try {
      const creado = await api.post('/cortes/', {
        servicio_id: servicio.id,
        metodo_pago: metodoPago,
      })
      await db.outboxOperaciones.update(operacionUuid, {
        estado: 'aceptada',
        idServidor: creado.data.id,
        actualizadoEn: new Date().toISOString(),
      })
      if (cobroCentavos !== null) {
        // Resultado individual (RF-57): el cobro puede quedar en revisión
        // aunque el corte se acepte; se informa cada resultado.
        try {
          await api.post(`/cortes/${creado.data.id}/movimientos`, {
            concepto: 'cliente',
            importe: centavosAPesosStr(cobroCentavos),
            metodo_pago: metodoPago,
          })
          const abonoOp = await db.outboxOperaciones
            .filter((o) => o.dependeDe === corteUuid)
            .first()
          if (abonoOp) {
            await db.outboxOperaciones.update(abonoOp.operacionUuid, {
              estado: 'aceptada',
              idServidor: creado.data.id,
              actualizadoEn: new Date().toISOString(),
            })
          }
        } catch (errorAbono: unknown) {
          mostrar('info', mensajeError(errorAbono, 'Corte aceptado; el cobro quedó pendiente de revisión'))
        }
      }
      setUltimoExito(servicio.nombre)
      mostrar('exito', `Corte registrado: ${servicio.nombre}`)
      setServicioSeleccionado(null)
      setCobro('pendiente')
      setImporteCobro('')
    } catch (error: unknown) {
      const huboRespuesta = Boolean(
        (error as { response?: unknown }).response
      )

      if (!huboRespuesta && usuario) {
        // Sin red: la operación YA quedó durable en la outbox (pendiente
        // visible, corte + abono encadenado); useSync la enviará al
        // reconectar con la misma UUID (T51/T54). Sin fila legacy duplicada:
        // el sender v2 es el único que crea el corte en el servidor (RF-32).
        mostrar('info', 'Sin conexión: el corte quedó guardado en el dispositivo y se sincronizará solo.')
        setServicioSeleccionado(null)
        setCobro('pendiente')
        setImporteCobro('')
      } else {
        await db.outboxOperaciones.update(operacionUuid, {
          estado: 'rechazada',
          ultimoError: mensajeError(error, 'rechazado'),
          actualizadoEn: new Date().toISOString(),
        })
        mostrar('error', mensajeError(error, 'No se pudo registrar el corte'))
      }
    } finally {
      setCargando(false)
    }
  }

  if (sinServicios) {
    return (
      <div className="contenedor">
        <Vacio
          titulo="No hay servicios cargados"
          texto="Tocá “Servicios” para dar de alta el primero, o esperá a que sincronice si recién entraste en la barbería."
        />
      </div>
    )
  }

  return (
    <div className="contenedor">
      <div className="registro">
        <header className="pagina__cabecera">
          <div>
            <h1>Registrar corte</h1>
            <p className="pagina__descripcion">
              Elegí el servicio, cobrá como te paguen y listo.
            </p>
          </div>
        </header>

        {ultimoExito && (
          <div className="registro__exito" role="status">
            <CheckCircle2 size={18} aria-hidden="true" />
            {ultimoExito} registrado. ¿Seguimos con el próximo?
          </div>
        )}
        {(pendientes ?? 0) > 0 && (
          <div className="registro__pendiente" role="status">
            {(pendientes ?? 0) === 1
              ? '1 operación pendiente de sincronización.'
              : `${pendientes} operaciones pendientes de sincronización.`}
          </div>
        )}

        <form onSubmit={registrar} className="pagina">
          <fieldset className="ui-campo" style={{ border: 'none', padding: 0, margin: 0 }}>
            <legend className="ui-campo__etiqueta" style={{ padding: 0 }}>
              Servicio
            </legend>
            <div className="ui-tarjetas-seleccion">
              {servicios.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className="ui-tarjeta-seleccion"
                  role="radio"
                  aria-checked={s.id === servicioSeleccionado}
                  onClick={() => setServicioSeleccionado(s.id)}
                >
                  <span>
                    <span className="ui-tarjeta-seleccion__nombre">{s.nombre}</span>
                    <span className="ui-tarjeta-seleccion__meta" style={{ display: 'block' }}>
                      {s.duracion_minutos} min
                    </span>
                  </span>
                  <span className="ui-tarjeta-seleccion__precio">
                    {formatearMoneda(s.precio)}
                  </span>
                </button>
              ))}
            </div>
          </fieldset>

          <Campo etiqueta="Método de pago" id="metodo-pago">
            <Segmentado
              etiqueta="Método de pago"
              valor={metodoPago}
              onCambio={setMetodoPago}
              opciones={[
                { valor: 'efectivo', etiqueta: 'Efectivo', icono: <Banknote size={16} /> },
                { valor: 'tarjeta', etiqueta: 'Tarjeta', icono: <CreditCard size={16} /> },
                { valor: 'transferencia', etiqueta: 'Transferencia', icono: <Landmark size={16} /> },
              ]}
            />
          </Campo>

          {servicio && (
            <div className="registro__preview">
              <span className="registro__preview-etiqueta">
                Tu ganancia ({usuario?.porcentaje_ganancia}%)
              </span>
              <span className="registro__preview-valor cifra">
                {gananciaCentavos === null ? '—' : formatearMoneda(ganancia)}
              </span>
            </div>
          )}

          <Campo etiqueta="Cobro del cliente" id="cobro-inicial">
            <Segmentado
              etiqueta="Cobro del cliente"
              valor={cobro}
              onCambio={setCobro}
              opciones={[
                { valor: 'pendiente', etiqueta: 'Pendiente' },
                { valor: 'parcial', etiqueta: 'Parcial' },
                { valor: 'completo', etiqueta: 'Completo' },
              ]}
            />
          </Campo>

          {cobro === 'parcial' && (
            <Campo etiqueta="Importe cobrado" id="importe-cobro">
              <input
                id="importe-cobro"
                className="ui-campo__control"
                inputMode="decimal"
                placeholder="0.00"
                value={importeCobro}
                onChange={(e) => setImporteCobro(e.target.value)}
              />
            </Campo>
          )}

          <Boton
            type="submit"
            cargando={cargando}
            disabled={!servicio}
            ancho
          >
            Registrar corte
          </Boton>
        </form>
      </div>
    </div>
  )
}
