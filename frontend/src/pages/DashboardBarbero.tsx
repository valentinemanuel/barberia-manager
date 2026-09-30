import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'

interface Resumen {
  total_cortes: number
  acumulado: number
  porcentaje_asignado: number
}

export default function DashboardBarbero() {
  const { usuario } = useAuthStore()
  const [resumenDia, setResumenDia] = useState<Resumen | null>(null)
  const [resumenSemana, setResumenSemana] = useState<Resumen | null>(null)
  const [resumenMes, setResumenMes] = useState<Resumen | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    cargarResumenes()
  }, [])

  const cargarResumenes = async () => {
    try {
      const [dia, semana, mes] = await Promise.all([
        api.get('/cortes/mi/resumen/dia'),
        api.get('/cortes/mi/resumen/semana'),
        api.get('/cortes/mi/resumen/mes'),
      ])
      setResumenDia(dia.data)
      setResumenSemana(semana.data)
      setResumenMes(mes.data)
    } catch (error) {
      console.error('Error cargando resúmenes:', error)
    } finally {
      setCargando(false)
    }
  }

  if (cargando) {
    return <div className="text-center p-8">Cargando...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">
        ¡Hola, {usuario?.nombre}! 👋
      </h2>

      <div className="grid grid-3">
        {/* Hoy */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-2 text-[var(--color-text-muted)]">
            Hoy
          </h3>
          <p className="text-3xl font-bold text-[var(--color-highlight)]">
            {resumenDia?.total_cortes || 0}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">cortes</p>
          <p className="text-2xl font-bold text-[var(--color-success)] mt-2">
            ${resumenDia?.acumulado?.toFixed(2) || '0.00'}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">acumulado</p>
        </div>

        {/* Semana */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-2 text-[var(--color-text-muted)]">
            Esta Semana
          </h3>
          <p className="text-3xl font-bold text-[var(--color-highlight)]">
            {resumenSemana?.total_cortes || 0}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">cortes</p>
          <p className="text-2xl font-bold text-[var(--color-success)] mt-2">
            ${resumenSemana?.acumulado?.toFixed(2) || '0.00'}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">acumulado</p>
        </div>

        {/* Mes */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-2 text-[var(--color-text-muted)]">
            Este Mes
          </h3>
          <p className="text-3xl font-bold text-[var(--color-highlight)]">
            {resumenMes?.total_cortes || 0}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">cortes</p>
          <p className="text-2xl font-bold text-[var(--color-success)] mt-2">
            ${resumenMes?.acumulado?.toFixed(2) || '0.00'}
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">acumulado</p>
        </div>
      </div>

      <div className="card mt-4">
        <h3 className="text-lg font-semibold mb-2">Tu Porcentaje</h3>
        <p className="text-4xl font-bold text-[var(--color-highlight)]">
          {usuario?.porcentaje_ganancia}%
        </p>
        <p className="text-sm text-[var(--color-text-muted)]">
          de cada corte registrado
        </p>
      </div>
    </div>
  )
}
