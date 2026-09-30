import { useEffect, useState } from 'react'
import api from '../services/api'

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
  const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0])
  const [reporte, setReporte] = useState<ReporteDia | null>(null)
  const [cargando, setCargando] = useState(false)

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
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reporte-${fecha}.csv`
    a.click()
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Reportes 📈</h2>

      <div className="card mb-4">
        <div className="flex flex-between flex-center gap-4">
          <div>
            <label className="label">Fecha</label>
            <input
              type="date"
              className="input"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
          </div>
          <button className="btn btn-primary mt-4" onClick={exportarCSV}>
            Exportar CSV
          </button>
        </div>
      </div>

      {cargando && <div className="text-center p-4">Cargando...</div>}

      {reporte && (
        <div className="grid grid-2">
          <div className="card">
            <h3 className="text-lg font-semibold mb-3">Ingresos</h3>
            <div className="space-y-2">
              <div className="flex flex-between p-2 bg-gray-50 rounded">
                <span>Cortes ({reporte.cantidad_cortes})</span>
                <span className="font-semibold">${reporte.total_cortes.toFixed(2)}</span>
              </div>
              <div className="flex flex-between p-2 bg-gray-50 rounded">
                <span>Productos</span>
                <span className="font-semibold">${reporte.total_productos.toFixed(2)}</span>
              </div>
              <div className="flex flex-between p-2 bg-gray-50 rounded">
                <span>Consumibles</span>
                <span className="font-semibold">${reporte.total_consumibles.toFixed(2)}</span>
              </div>
              <div className="flex flex-between p-2 bg-green-50 rounded font-bold">
                <span>Total Ingresos</span>
                <span className="text-[var(--color-success)]">${reporte.total_ingresos.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-3">Gastos y Ganancia</h3>
            <div className="space-y-2">
              <div className="flex flex-between p-2 bg-gray-50 rounded">
                <span>Total Gastos</span>
                <span className="font-semibold text-[var(--color-danger)]">
                  -${reporte.total_gastos.toFixed(2)}
                </span>
              </div>
              <div className="flex flex-between p-2 bg-green-50 rounded font-bold">
                <span>Ganancia Neta</span>
                <span className="text-[var(--color-success)]">
                  ${reporte.ganancia_neta.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
