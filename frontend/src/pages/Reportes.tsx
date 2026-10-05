import { useEffect, useState } from 'react'
import { Download, CalendarDays } from 'lucide-react'
import api from '../services/api'
import {
  Boton,
  Tarjeta,
  Campo,
  Cifra,
  SkeletonLineas,
  useToast,
} from '../components/ui'
import { formatearMoneda, formatearEntero, formatearFecha } from '../utils/formato'

interface ReporteDia {
  fecha: string
  total_cortes: number
  total_productos: number
  total_consumibles: number
  total_ingresos: number
  total_gastos: number
  ganancia_neta: number
  cantidad_cortes: number
}

export default function Reportes() {
  const { mostrar } = useToast()
  const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0])
  const [reporte, setReporte] = useState<ReporteDia | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    cargarReporte()
  }, [fecha])

  const cargarReporte = async () => {
    setCargando(true)
    try {
      const response = await api.get(`/reportes/dia/${fecha}`)
      setReporte(response.data)
    } catch (error) {
      console.error('Error cargando reporte:', error)
      mostrar('error', 'No se pudo cargar el reporte de ese día')
    } finally {
      setCargando(false)
    }
  }

  const exportarCSV = () => {
    if (!reporte) return
    const csv = [
      ['Concepto', 'Monto'],
      ['Total Cortes', reporte.total_cortes],
      ['Total Productos', reporte.total_productos],
      ['Total Consumibles', reporte.total_consumibles],
      ['Total Ingresos', reporte.total_ingresos],
      ['Total Gastos', reporte.total_gastos],
      ['Ganancia Neta', reporte.ganancia_neta],
    ]
      .map((fila) => fila.join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reporte-${fecha}.csv`
    a.click()
    URL.revokeObjectURL(url)
    mostrar('exito', 'Reporte descargado')
  }

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Reportes</h1>
            <p className="pagina__descripcion">
              El cierre contable de cualquier día.
            </p>
          </div>
          <Boton
            variante="secundario"
            onClick={exportarCSV}
            disabled={!reporte || cargando}
          >
            <Download size={16} aria-hidden="true" />
            Exportar CSV
          </Boton>
        </header>

        <Tarjeta>
          <Campo
            etiqueta="Fecha del reporte"
            id="reporte-fecha"
            pista={reporte ? formatearFecha(reporte.fecha) : undefined}
          >
            <input
              id="reporte-fecha"
              type="date"
              className="ui-campo__control"
              style={{ maxWidth: 240 }}
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
          </Campo>
        </Tarjeta>

        {cargando ? (
          <div className="rejilla rejilla--2">
            <div className="ui-tarjeta">
              <SkeletonLineas cantidad={4} />
            </div>
            <div className="ui-tarjeta">
              <SkeletonLineas cantidad={3} />
            </div>
          </div>
        ) : reporte && (
          <div className="rejilla rejilla--2">
            <Tarjeta titulo="Ingresos">
              <div className="pagina">
                <Cifra
                  etiqueta={`Cortes (${formatearEntero(reporte.cantidad_cortes)})`}
                  valor={formatearMoneda(reporte.total_cortes)}
                />
                <Cifra
                  etiqueta="Productos"
                  valor={formatearMoneda(reporte.total_productos)}
                />
                <Cifra
                  etiqueta="Consumibles"
                  valor={formatearMoneda(reporte.total_consumibles)}
                />
                <div style={{ paddingTop: 'var(--sp-3)', borderTop: '1px solid var(--borde)' }}>
                  <Cifra
                    etiqueta="Total ingresos"
                    valor={formatearMoneda(reporte.total_ingresos)}
                    destacada
                  />
                </div>
              </div>
            </Tarjeta>

            <Tarjeta titulo="Gastos y ganancia">
              <div className="pagina">
                <Cifra
                  etiqueta="Total gastos"
                  valor={formatearMoneda(reporte.total_gastos)}
                  className="texto-peligro"
                />
                <div style={{ paddingTop: 'var(--sp-3)', borderTop: '1px solid var(--borde)' }}>
                  <Cifra
                    etiqueta="Ganancia neta"
                    valor={formatearMoneda(reporte.ganancia_neta)}
                    pie="ingresos menos gastos del día"
                    destacada
                  />
                </div>
              </div>
            </Tarjeta>
          </div>
        )}

        {!cargando && reporte && reporte.total_ingresos === 0 && (
          <p className="texto-suave texto-centrado">
            <CalendarDays
              size={16}
              aria-hidden="true"
              style={{ display: 'inline-block', verticalAlign: 'text-bottom' }}
            />{' '}
            Ese día no hubo movimiento.
          </p>
        )}
      </div>
    </div>
  )
}
