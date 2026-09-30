import { useEffect, useState } from 'react'
import api from '../services/api'

interface DashboardData {
  ganancias_hoy: number
  ganancias_semana: number
  ganancias_mes: number
  cortes_hoy: number
  cortes_semana: number
  cortes_mes: number
  top_barberos: any[]
  productos_mas_vendidos: any[]
}

export default function DashboardAdmin() {
  const [datos, setDatos] = useState<DashboardData | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    cargarDashboard()
  }, [])

  const cargarDashboard = async () => {
    try {
      const response = await api.get('/reportes/dashboard')
      setDatos(response.data)
    } catch (error) {
      console.error('Error cargando dashboard:', error)
    } finally {
      setCargando(false)
    }
  }

  if (cargando) {
    return <div className="text-center p-8">Cargando...</div>
  }

  if (!datos) {
    return <div className="text-center p-8">Error cargando datos</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Dashboard 📊</h2>

      <div className="grid grid-3 mb-4">
        <div className="card">
          <h3 className="text-sm text-[var(--color-text-muted)] mb-1">Ganancias Hoy</h3>
          <p className="text-3xl font-bold text-[var(--color-success)]">
            ${datos.ganancias_hoy.toFixed(2)}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">
            {datos.cortes_hoy} cortes
          </p>
        </div>

        <div className="card">
          <h3 className="text-sm text-[var(--color-text-muted)] mb-1">Ganancias Semana</h3>
          <p className="text-3xl font-bold text-[var(--color-success)]">
            ${datos.ganancias_semana.toFixed(2)}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">
            {datos.cortes_semana} cortes
          </p>
        </div>

        <div className="card">
          <h3 className="text-sm text-[var(--color-text-muted)] mb-1">Ganancias Mes</h3>
          <p className="text-3xl font-bold text-[var(--color-success)]">
            ${datos.ganancias_mes.toFixed(2)}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">
            {datos.cortes_mes} cortes
          </p>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">Top Barberos (Mes)</h3>
          {datos.top_barberos.length === 0 ? (
            <p className="text-[var(--color-text-muted)]">Sin datos</p>
          ) : (
            <div className="space-y-2">
              {datos.top_barberos.map((barbero) => (
                <div key={barbero.barbero_id} className="flex flex-between p-2 bg-gray-50 rounded">
                  <span>{barbero.nombre_barbero}</span>
                  <span className="font-semibold">{barbero.cantidad_cortes} cortes</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-3">Productos Más Vendidos</h3>
          {datos.productos_mas_vendidos.length === 0 ? (
            <p className="text-[var(--color-text-muted)]">Sin datos</p>
          ) : (
            <div className="space-y-2">
              {datos.productos_mas_vendidos.map((producto, idx) => (
                <div key={idx} className="flex flex-between p-2 bg-gray-50 rounded">
                  <span>Producto #{producto.producto_id}</span>
                  <span className="font-semibold">{producto.total_vendido} uds</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
