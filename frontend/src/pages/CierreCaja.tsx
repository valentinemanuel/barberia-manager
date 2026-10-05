import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import {
  Boton,
  Tarjeta,
  Campo,
  Cifra,
  SkeletonLineas,
  useToast,
} from '../components/ui'
import { formatearMoneda, formatearFecha, pluralizar } from '../utils/formato'

interface ResumenDia {
  fecha: string
  total_cortes: number
  total_productos: number
  total_consumibles: number
  total_ingresos: number
  total_gastos: number
  ganancia_neta: number
  cantidad_cortes: number
}

export default function CierreCaja() {
  const { mostrar } = useToast()
  const [resumen, setResumen] = useState<ResumenDia | null>(null)
  const [cargando, setCargando] = useState(true)
  const [totalEnCaja, setTotalEnCaja] = useState('')
  const [montoRetirado, setMontoRetirado] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    cargarResumen()
  }, [])

  const cargarResumen = async () => {
    try {
      const response = await api.get('/cierre-caja/resumen/dia')
      setResumen(response.data)
    } catch (error) {
      console.error('Error cargando resumen:', error)
      mostrar('error', 'No se pudo cargar el resumen del día')
    } finally {
      setCargando(false)
    }
  }

  const diferencia = resumen
    ? (parseFloat(totalEnCaja) || 0) -
      (parseFloat(montoRetirado) || 0) -
      resumen.total_ingresos
    : 0

  const hayMontos = totalEnCaja !== '' && montoRetirado !== ''

  const claseDiferencia = !hayMontos
    ? ''
    : diferencia === 0
    ? 'cierre__diferencia--cuadra'
    : diferencia > 0
    ? 'cierre__diferencia--sobra'
    : 'cierre__diferencia--falta'

  const manejarCierre = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resumen) return

    setGuardando(true)
    try {
      await api.post('/cierre-caja/', {
        fecha: resumen.fecha,
        total_cortes: resumen.total_cortes,
        total_productos: resumen.total_productos,
        total_consumibles: resumen.total_consumibles,
        total_ingresos: resumen.total_ingresos,
        total_gastos: resumen.total_gastos,
        total_en_caja: parseFloat(totalEnCaja),
        monto_retirado: parseFloat(montoRetirado),
      })
      mostrar('exito', 'Cierre de caja realizado')
      setTotalEnCaja('')
      setMontoRetirado('')
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo realizar el cierre'))
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) {
    return (
      <div className="contenedor">
        <div className="pagina">
          <div className="ui-tarjeta">
            <SkeletonLineas cantidad={5} />
          </div>
        </div>
      </div>
    )
  }

  if (!resumen) {
    return (
      <div className="contenedor">
        <div className="pagina">
          <h1>Cierre de caja</h1>
          <p className="texto-suave">
            No se pudo cargar el resumen. Revisá la conexión y recargá la pantalla.
          </p>
          <div>
            <Boton variante="secundario" onClick={cargarResumen}>
              Reintentar
            </Boton>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Cierre de caja</h1>
            <p className="pagina__descripcion">{formatearFecha(resumen.fecha)}</p>
          </div>
        </header>

        <Tarjeta titulo="Resumen del día">
          <div className="cierre__resumen">
            <Cifra
              etiqueta="Cortes"
              valor={formatearMoneda(resumen.total_cortes)}
              pie={`${resumen.cantidad_cortes} ${pluralizar(resumen.cantidad_cortes, 'atendido', 'atendidos')}`}
            />
            <Cifra
              etiqueta="Productos"
              valor={formatearMoneda(resumen.total_productos)}
            />
            <Cifra
              etiqueta="Consumibles"
              valor={formatearMoneda(resumen.total_consumibles)}
            />
            <Cifra
              etiqueta="Gastos"
              valor={`-${formatearMoneda(resumen.total_gastos)}`}
              className="texto-peligro"
            />
          </div>
          <div style={{ marginTop: 'var(--sp-5)' }}>
            <Cifra
              etiqueta="En caja según registros"
              valor={formatearMoneda(resumen.total_ingresos)}
              destacada
            />
          </div>
        </Tarjeta>

        <form onSubmit={manejarCierre} className="pagina">
          <Tarjeta titulo="Realizar cierre">
            <div className="pagina">
              <Campo
                etiqueta="Total en caja (físico)"
                id="cierre-total"
                pista="Lo que hay en el cajón ahora mismo"
              >
                <input
                  id="cierre-total"
                  type="number"
                  step="0.01"
                  min="0"
                  className="ui-campo__control"
                  value={totalEnCaja}
                  onChange={(e) => setTotalEnCaja(e.target.value)}
                  required
                  placeholder="0.00"
                />
              </Campo>

              <Campo
                etiqueta="Monto retirado"
                id="cierre-retiro"
                pista="Lo que sacás de la caja"
              >
                <input
                  id="cierre-retiro"
                  type="number"
                  step="0.01"
                  min="0"
                  className="ui-campo__control"
                  value={montoRetirado}
                  onChange={(e) => setMontoRetirado(e.target.value)}
                  required
                  placeholder="0.00"
                />
              </Campo>

              <div className={`cierre__diferencia ${claseDiferencia}`.trim()}>
                <span className="ui-cifra__etiqueta">Diferencia</span>
                <span className="ui-cifra__valor cifra">
                  {hayMontos ? formatearMoneda(diferencia) : '—'}
                </span>
                {hayMontos && diferencia !== 0 && (
                  <span className="cierre__diferencia-nota">
                    {diferencia > 0
                      ? 'Hay más dinero en caja que el registrado. Revisá si faltó cargar ventas.'
                      : 'Hay menos dinero en caja que el registrado. Revisá si faltó cargar gastos.'}
                  </span>
                )}
                {hayMontos && diferencia === 0 && (
                  <span className="cierre__diferencia-nota">
                    La caja cuadra con los registros.
                  </span>
                )}
              </div>

              <Boton type="submit" cargando={guardando} ancho>
                Realizar cierre de caja
              </Boton>
            </div>
          </Tarjeta>
        </form>
      </div>
    </div>
  )
}
