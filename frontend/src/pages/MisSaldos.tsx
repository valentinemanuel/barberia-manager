import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import { Tarjeta, Vacio, SkeletonLineas } from '../components/ui'
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

/**
 * Mis saldos (paquete 9, T64): restante y excedente por concepto, aparte;
 * revisiones con causa e importe; motivos de correctivos propios.
 * Solo datos del titular (endpoints propios); sin totales del negocio.
 */
export default function MisSaldos() {
  const [filas, setFilas] = useState<FilaCorte[]>([])
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
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar los saldos'))
    } finally {
      setCargando(false)
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
          return (
            <Tarjeta key={corte.id} titulo={`Corte #${corte.id} · ${formatearFecha(corte.fecha)}`}>
              {corte.anulado_en && <p>Anulado: obligaciones canceladas, solo ajustes del admin.</p>}
              {saldos && (
                <ul>
                  <li>Deuda del cliente: {formatearMoneda(Number(saldos.cliente.restante))}</li>
                  <li>Mi comisión pendiente: {formatearMoneda(Number(saldos.comision.restante))}</li>
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
            </Tarjeta>
          )
        })}
      </div>
    </div>
  )
}
