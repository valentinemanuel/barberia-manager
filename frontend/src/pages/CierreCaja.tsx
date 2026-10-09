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
import { formatearFecha, pluralizar } from '../utils/formato'
import {
  etiquetaEstadoJornada,
  lineaMetodo,
  textoBalance,
  textoPendientes,
} from '../services/cajaVista'

interface ResumenCaja {
  fecha: string
  estado: string
  devengado: { cortes: number; total: string }
  cobros: { total: string; por_metodo: Record<string, string> }
  pagos: { total: string }
  ajustes: number
  desconocidos: number
  pendientes: number
}

/**
 * Caja del admin (paquete 11, T79): apertura/cierre explícitos de jornada,
 * resumen nuevo (devengado separado de cobros/pagos por método) y
 * pendientes de imputación. Sin conteo físico con float: el flujo legacy
 * de snapshot aportado queda fuera de esta pantalla (endpoint intacto).
 */
export default function CierreCaja() {
  const { mostrar } = useToast()
  const hoyLocal = () => {
    const ahora = new Date()
    const mes = String(ahora.getMonth() + 1).padStart(2, '0')
    const dia = String(ahora.getDate()).padStart(2, '0')
    return `${ahora.getFullYear()}-${mes}-${dia}`
  }
  const [fecha, setFecha] = useState(hoyLocal())
  const [resumen, setResumen] = useState<ResumenCaja | null>(null)
  const [cargando, setCargando] = useState(true)
  const [operando, setOperando] = useState(false)

  useEffect(() => {
    cargarResumen()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fecha])

  const cargarResumen = async () => {
    setCargando(true)
    try {
      const response = await api.get(`/jornadas/resumen?fecha=${fecha}`)
      setResumen(response.data)
    } catch (error: unknown) {
      if ((error as { response?: { status?: number } }).response?.status === 404) {
        setResumen(null)
      } else {
        console.error('Error cargando resumen:', error)
        mostrar('error', 'No se pudo cargar el resumen de la jornada')
      }
    } finally {
      setCargando(false)
    }
  }

  const operar = async (accion: 'abrir' | 'cerrar') => {
    setOperando(true)
    try {
      await api.post(`/jornadas/${accion}`, { fecha })
      mostrar('exito', accion === 'abrir' ? 'Jornada abierta' : 'Jornada cerrada')
      await cargarResumen()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, `No se pudo ${accion} la jornada`))
    } finally {
      setOperando(false)
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

  const pendientes = resumen ? textoPendientes(resumen.pendientes) : null

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Caja por jornada</h1>
            <p className="pagina__descripcion">{formatearFecha(fecha)}</p>
          </div>
        </header>

        <Campo etiqueta="Jornada" id="jornada-fecha">
          <input
            id="jornada-fecha"
            type="date"
            className="ui-campo__control"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
        </Campo>

        {!resumen ? (
          <Tarjeta titulo="Sin jornada registrada">
            <p className="pagina__descripcion">
              Esta fecha no tiene jornada. La apertura es explícita del admin.
            </p>
            <Boton cargando={operando} onClick={() => operar('abrir')}>
              Abrir jornada
            </Boton>
          </Tarjeta>
        ) : (
          <>
            <Tarjeta
              titulo={`Jornada ${etiquetaEstadoJornada(resumen.estado)}`}
              acciones={
                resumen.estado === 'abierta' ? (
                  <Boton variante="secundario" cargando={operando} onClick={() => operar('cerrar')}>
                    Cerrar jornada
                  </Boton>
                ) : undefined
              }
            >
              <div className="cierre__resumen">
                <Cifra
                  etiqueta="Servicios devengados"
                  valor={`$${resumen.devengado.total}`}
                  pie={`${resumen.devengado.cortes} ${pluralizar(resumen.devengado.cortes, 'corte', 'cortes')}`}
                />
                <Cifra
                  etiqueta="Cobrado"
                  valor={`$${resumen.cobros.total}`}
                  pie={textoBalance(resumen.cobros.total, resumen.pagos.total)}
                />
              </div>
              <ul>
                {Object.entries(resumen.cobros.por_metodo).map(([metodo, total]) => (
                  <li key={metodo}>{lineaMetodo(metodo, total)}</li>
                ))}
              </ul>
              {pendientes && <p>{pendientes}: se solicita apertura administrativa.</p>}
              {resumen.ajustes > 0 && (
                <p>
                  {resumen.ajustes} {pluralizar(resumen.ajustes, 'ajuste', 'ajustes')} posterior(es) sin mutar el cierre.
                </p>
              )}
              {resumen.desconocidos > 0 && (
                <p>{resumen.desconocidos} con información histórica incompleta.</p>
              )}
            </Tarjeta>
          </>
        )}
      </div>
    </div>
  )
}
