import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'

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
  const [resumen, setResumen] = useState<ResumenDia | null>(null)
  const [totalEnCaja, setTotalEnCaja] = useState('')
  const [montoRetirado, setMontoRetirado] = useState('')
  const [cargando, setCargando] = useState(false)
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    cargarResumen()
  }, [])

  const cargarResumen = async () => {
    try {
      const response = await api.get('/cierre-caja/resumen/dia')
      setResumen(response.data)
    } catch (error) {
      console.error('Error cargando resumen:', error)
    }
  }

  const diferencia = resumen
    ? (parseFloat(totalEnCaja) || 0) - (parseFloat(montoRetirado) || 0) - resumen.total_ingresos
    : 0

  const handleCierre = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resumen) return

    setCargando(true)
    setMensaje('')

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
      setMensaje('✓ Cierre de caja realizado exitosamente')
      setTotalEnCaja('')
      setMontoRetirado('')
    } catch (error: any) {
      setMensaje(mensajeError(error, 'Error al realizar cierre'))
    } finally {
      setCargando(false)
    }
  }

  if (!resumen) {
    return <div className="text-center p-8">Cargando...</div>
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Cierre de Caja 💰</h2>

      <div className="card mb-4">
        <h3 className="text-lg font-semibold mb-3">Resumen del Día</h3>
        <div className="grid grid-2 gap-4">
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">Total Cortes</p>
            <p className="text-xl font-bold">${resumen.total_cortes.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">Total Productos</p>
            <p className="text-xl font-bold">${resumen.total_productos.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">Total Consumibles</p>
            <p className="text-xl font-bold">${resumen.total_consumibles.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">Total Gastos</p>
            <p className="text-xl font-bold text-[var(--color-danger)]">
              -${resumen.total_gastos.toFixed(2)}
            </p>
          </div>
        </div>
        <div className="mt-4 p-3 bg-green-50 rounded-lg">
          <p className="text-sm text-[var(--color-text-muted)]">Total en Caja (según registros)</p>
          <p className="text-2xl font-bold text-[var(--color-success)]">
            ${resumen.total_ingresos.toFixed(2)}
          </p>
        </div>
      </div>

      <form onSubmit={handleCierre} className="card">
        <h3 className="text-lg font-semibold mb-3">Realizar Cierre</h3>

        <div className="mb-4">
          <label className="label">Total en Caja (Físico)</label>
          <input
            type="number"
            step="0.01"
            className="input"
            value={totalEnCaja}
            onChange={(e) => setTotalEnCaja(e.target.value)}
            required
            placeholder="0.00"
          />
        </div>

        <div className="mb-4">
          <label className="label">Monto Retirado</label>
          <input
            type="number"
            step="0.01"
            className="input"
            value={montoRetirado}
            onChange={(e) => setMontoRetirado(e.target.value)}
            required
            placeholder="0.00"
          />
        </div>

        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-[var(--color-text-muted)]">Diferencia</p>
          <p className={`text-2xl font-bold ${
            diferencia === 0
              ? 'text-[var(--color-success)]'
              : diferencia > 0
              ? 'text-[var(--color-warning)]'
              : 'text-[var(--color-danger)]'
          }`}>
            ${diferencia.toFixed(2)}
          </p>
          {diferencia !== 0 && (
            <p className="text-xs text-[var(--color-text-muted)]">
              {diferencia > 0
                ? 'Hay más dinero en caja de lo registrado'
                : 'Hay menos dinero en caja de lo registrado'}
            </p>
          )}
        </div>

        {mensaje && (
          <div className={`mb-4 p-3 rounded-lg text-sm ${
            mensaje.startsWith('✓')
              ? 'bg-green-50 text-green-600'
              : 'bg-red-50 text-red-600'
          }`}>
            {mensaje}
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary w-full"
          disabled={cargando}
        >
          {cargando ? 'Procesando...' : 'Realizar Cierre de Caja'}
        </button>
      </form>
    </div>
  )
}
