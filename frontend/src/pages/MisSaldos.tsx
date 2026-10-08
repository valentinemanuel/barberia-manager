import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import { useAuthStore } from '../store/authStore'
import { db } from '../services/db'
import {
  crearOperacionAnulacion,
  crearOperacionEdicion,
} from '../services/operacionesCortes'
import { Tarjeta, Vacio, SkeletonLineas, Segmentado, Boton } from '../components/ui'
import { formatearMoneda, formatearFecha } from '../utils/formato'
import {
  motivosVisibles,
  revisionesVisibles,
  textoExcedente,
  type MovimientoVista,
  type SaldoVista,
} from '../services/saldosVista'

interface CortePropio {
  id: number
  servicio_id: number
  precio: number | string
  fecha: string
  metodo_pago: string
  anulado_en?: string | null
}

interface FilaCorte {
  corte: CortePropio
  saldos: { cliente: SaldoVista; comision: SaldoVista } | null
  movimientos: MovimientoVista[]
}

interface Justificante {
  corte_id: number
  uuid: string
  concepto: string
  tipo: string | null
  importe: number | string
  motivo: string | null
}

/**
 * Mis saldos (paquete 9, T64): restante y excedente por concepto, aparte;
 * revisiones con causa e importe; motivos de correctivos propios.
 * Solo datos del titular (endpoints propios); sin totales del negocio.
 */
export default function MisSaldos() {
  const { usuario } = useAuthStore()
  const [filas, setFilas] = useState<FilaCorte[]>([])
  const [justificantes, setJustificantes] = useState<Justificante[]>([])
  const [metodoEdit, setMetodoEdit] = useState<Record<number, string>>({})
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    cargar()
  }, [])

  const cargar = async () => {
    try {
      const historial = await api.get('/cortes/mi/historial')
      const cortes: CortePropio[] = historial.data ?? []
      const detalle = await Promise.all(
        cortes.map(async (corte) => {
          const [saldos, movimientos] = await Promise.all([
            api.get(`/cortes/${corte.id}/saldos`).catch(() => ({ data: null })),
            api.get(`/cortes/${corte.id}/movimientos`).catch(() => ({ data: [] })),
          ])
          return { corte, saldos: saldos.data, movimientos: movimientos.data ?? [] }
        }),
      )
      setFilas(detalle)
      const just = await api.get('/cortes/mi/justificantes').catch(() => ({ data: [] }))
      setJustificantes(just.data ?? [])
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar los saldos'))
    } finally {
      setCargando(false)
    }
  }

  /** Corrección persist-first (T72): outbox antes que red; el sync la envía con la misma UUID. */
  const corregirMetodo = async (corteId: number, metodo: string) => {
    if (!usuario) return
    const ahora = new Date()
    try {
      const op = crearOperacionEdicion({
        actorId: usuario.id,
        corteUuid: `corte-${corteId}`,
        cambios: { metodo_pago: metodo },
        modoCaptura: navigator.onLine ? 'online' : 'offline',
        ahora,
      })
      await db.outboxOperaciones.add({
        operacionUuid: op.operacionUuid,
        corteUuid: op.dependeDe,
        actorId: op.actorId,
        servicioId: 0,
        metodoPago: metodo,
        precioCentavos: 0,
        porcentajeCentesimas: 0,
        modoCaptura: op.modoCaptura,
        instanteCambio: op.instanteCambioUtc,
        momentoReal: op.instanteCambioUtc,
        estado: 'pendiente',
        intento: 0,
        actualizadoEn: op.instanteCambioUtc,
        tipo: 'edicion',
        accion: 'editar',
        cambios: op.cambios,
        dependeDe: op.dependeDe,
        corteIdServidor: corteId,
      })
      await api.patch(`/cortes/${corteId}`, { metodo_pago: metodo })
      await db.outboxOperaciones.update(op.operacionUuid, { estado: 'aceptada', actualizadoEn: new Date().toISOString() })
      cargar()
    } catch {
      // Sin red: queda pendiente visible; el sync la encadena (T72).
    }
  }

  const anularCorte = async (corteId: number) => {
    if (!usuario) return
    if (!window.confirm('¿Anular este corte? Queda conservado como anulado.')) return
    const ahora = new Date()
    try {
      const op = crearOperacionAnulacion({
        actorId: usuario.id,
        corteUuid: `corte-${corteId}`,
        modoCaptura: navigator.onLine ? 'online' : 'offline',
        ahora,
      })
      await db.outboxOperaciones.add({
        operacionUuid: op.operacionUuid,
        corteUuid: op.dependeDe,
        actorId: op.actorId,
        servicioId: 0,
        metodoPago: '',
        precioCentavos: 0,
        porcentajeCentesimas: 0,
        modoCaptura: op.modoCaptura,
        instanteCambio: op.instanteCambioUtc,
        momentoReal: op.instanteCambioUtc,
        estado: 'pendiente',
        intento: 0,
        actualizadoEn: op.instanteCambioUtc,
        tipo: 'anulacion',
        accion: 'anular',
        cambios: {},
        dependeDe: op.dependeDe,
        corteIdServidor: corteId,
      })
      await api.post(`/cortes/${corteId}/anular`, {})
      await db.outboxOperaciones.update(op.operacionUuid, { estado: 'aceptada', actualizadoEn: new Date().toISOString() })
      cargar()
    } catch {
      // Sin red: queda pendiente visible.
    }
  }

  if (cargando) {
    return (
      <div className="contenedor">
        <div className="pagina">
          <div className="ui-tarjeta">
            <SkeletonLineas cantidad={4} />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="contenedor">
        <Vacio titulo="No se pudieron cargar los saldos" texto={error} />
      </div>
    )
  }

  if (filas.length === 0) {
    return (
      <div className="contenedor">
        <Vacio
          titulo="Sin cortes"
          texto="Todavía no tenés cortes registrados para mostrar saldos."
        />
      </div>
    )
  }

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Mis saldos</h1>
            <p className="pagina__descripcion">
              Lo que falta cobrar, excedentes y operaciones en revisión.
            </p>
          </div>
        </header>

        {filas.map(({ corte, saldos, movimientos }) => {
          const revisiones = revisionesVisibles(movimientos)
          const motivos = motivosVisibles(movimientos)
          const excedenteCliente = saldos ? textoExcedente({ excedente: String(saldos.cliente.excedente) }) : null
          const excedenteComision = saldos ? textoExcedente({ excedente: String(saldos.comision.excedente) }) : null
          const desconocidoCliente = saldos && (saldos.cliente.estado === 'desconocido')
          const desconocidoComision = saldos && (saldos.comision.estado === 'desconocido')
          const metodoActual = String(corte.metodo_pago ?? 'efectivo')
          return (
            <Tarjeta key={corte.id} titulo={`Corte #${corte.id} · ${formatearFecha(corte.fecha)}`}>
              {corte.anulado_en && <p>Anulado: obligaciones canceladas, solo ajustes del admin.</p>}
              {saldos && (
                <ul>
                  <li>
                    Deuda del cliente:{' '}
                    {desconocidoCliente ? 'Sin información' : formatearMoneda(Number(saldos.cliente.restante))}
                  </li>
                  <li>
                    Mi comisión pendiente:{' '}
                    {desconocidoComision ? 'Sin información' : formatearMoneda(Number(saldos.comision.restante))}
                  </li>
                  {excedenteCliente && <li>{excedenteCliente}</li>}
                  {excedenteComision && <li>Comisión: {excedenteComision}</li>}
                </ul>
              )}
              {revisiones.length > 0 && (
                <ul>
                  {revisiones.map((texto, i) => (
                    <li key={i}>{texto}</li>
                  ))}
                </ul>
              )}
              {motivos.length > 0 && (
                <ul>
                  {motivos.map((motivo, i) => (
                    <li key={i}>Ajuste: {motivo}</li>
                  ))}
                </ul>
              )}
              {!corte.anulado_en && (
                <div>
                  <Segmentado
                    etiqueta="Corregir método"
                    valor={metodoEdit[corte.id] ?? metodoActual}
                    onCambio={(v) => setMetodoEdit((m) => ({ ...m, [corte.id]: v }))}
                    opciones={[
                      { valor: 'efectivo', etiqueta: 'Efectivo' },
                      { valor: 'tarjeta', etiqueta: 'Tarjeta' },
                      { valor: 'transferencia', etiqueta: 'Transferencia' },
                    ]}
                  />
                  <Boton
                    type="button"
                    disabled={(metodoEdit[corte.id] ?? metodoActual) === metodoActual}
                    onClick={() => corregirMetodo(corte.id, metodoEdit[corte.id] ?? metodoActual)}
                  >
                    Guardar corrección
                  </Boton>{' '}
                  <Boton type="button" onClick={() => anularCorte(corte.id)}>
                    Anular
                  </Boton>
                </div>
              )}
            </Tarjeta>
          )
        })}

        {justificantes.length > 0 && (
          <Tarjeta titulo="Mis justificantes">
            <p className="pagina__descripcion">
              Comprobantes de comisiones de cortes reasignados.
            </p>
            <ul>
              {justificantes.map((j) => (
                <li key={j.uuid}>
                  Corte #{j.corte_id}: {formatearMoneda(Number(j.importe))}
                  {j.motivo ? ` — ${j.motivo}` : ''}
                </li>
              ))}
            </ul>
          </Tarjeta>
        )}
      </div>
    </div>
  )
}
