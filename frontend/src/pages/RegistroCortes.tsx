import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import { useAuthStore } from '../store/authStore'
import { db } from '../services/db'

interface Servicio {
  id: number
  nombre: string
  descripcion: string
  precio: number
  duracion_minutos: number
}

export default function RegistroCortes() {
  const { usuario } = useAuthStore()
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [servicioSeleccionado, setServicioSeleccionado] = useState<number | ''>('')
  const [metodoPago, setMetodoPago] = useState('efectivo')
  const [mensaje, setMensaje] = useState('')
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    cargarServicios()
  }, [])

  const cargarServicios = async () => {
    try {
      const response = await api.get('/servicios/')
      setServicios(response.data)
    } catch (error) {
      console.error('Error cargando servicios:', error)
      // Cargar desde IndexedDB como fallback
      const locales = await db.servicios.where('activo').equals(1).toArray()
      setServicios(locales as Servicio[])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!servicioSeleccionado) {
      setMensaje('Selecciona un servicio')
      return
    }

    setCargando(true)
    setMensaje('')

    try {
      await api.post('/cortes/', {
        servicio_id: servicioSeleccionado,
        metodo_pago: metodoPago,
      })
      setMensaje('✓ Corte registrado exitosamente')
      setServicioSeleccionado('')
    } catch (error: any) {
      setMensaje(mensajeError(error, 'Error al registrar corte'))
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Registrar Corte ✂️</h2>

      <form onSubmit={handleSubmit} className="card">
        <div className="mb-4">
          <label className="label">Servicio</label>
          <select
            className="input"
            value={servicioSeleccionado}
            onChange={(e) => setServicioSeleccionado(Number(e.target.value))}
            required
          >
            <option value="">Selecciona un servicio</option>
            {servicios.map((servicio) => (
              <option key={servicio.id} value={servicio.id}>
                {servicio.nombre} - ${servicio.precio.toFixed(2)}
              </option>
            ))}
          </select>
        </div>

        <div className="mb-4">
          <label className="label">Método de Pago</label>
          <div className="grid grid-3 gap-2">
            {['efectivo', 'tarjeta', 'transferencia'].map((metodo) => (
              <button
                key={metodo}
                type="button"
                className={`p-3 rounded-lg border-2 transition-colors ${
                  metodoPago === metodo
                    ? 'border-[var(--color-highlight)] bg-red-50'
                    : 'border-[var(--color-border)]'
                }`}
                onClick={() => setMetodoPago(metodo)}
              >
                {metodo === 'efectivo' && '💵'}
                {metodo === 'tarjeta' && '💳'}
                {metodo === 'transferencia' && '🏦'}
                <span className="ml-2 capitalize">{metodo}</span>
              </button>
            ))}
          </div>
        </div>

        {servicioSeleccionado && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-[var(--color-text-muted)]">
              Tu ganancia ({usuario?.porcentaje_ganancia}%):
            </p>
            <p className="text-2xl font-bold text-[var(--color-success)]">
              ${(
                servicios.find((s) => s.id === servicioSeleccionado)!.precio *
                ((usuario?.porcentaje_ganancia ?? 0) / 100)
              ).toFixed(2)}
            </p>
          </div>
        )}

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
          {cargando ? 'Registrando...' : 'Registrar Corte'}
        </button>
      </form>
    </div>
  )
}
