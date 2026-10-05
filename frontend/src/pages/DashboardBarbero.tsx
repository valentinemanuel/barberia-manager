import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Scissors } from 'lucide-react'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'
import { Tarjeta, Cifra, SkeletonLineas } from '../components/ui'
import { formatearMoneda, formatearEntero, formatearFecha, pluralizar } from '../utils/formato'

interface Resumen {
  fecha?: string
  total_cortes: number
  acumulado: number
  porcentaje_asignado: number
}

/**
 * Vista del barbero: su día, su semana, su mes y su porcentaje.
 * Nunca muestra totales brutos de la barbería ni datos de otros barberos.
 */
export default function DashboardBarbero() {
  const { usuario } = useAuthStore()
  const [dia, setDia] = useState<Resumen | null>(null)
  const [semana, setSemana] = useState<Resumen | null>(null)
  const [mes, setMes] = useState<Resumen | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    cargarResumenes()
  }, [])

  const cargarResumenes = async () => {
    try {
      const [rDia, rSemana, rMes] = await Promise.all([
        api.get('/cortes/mi/resumen/dia'),
        api.get('/cortes/mi/resumen/semana'),
        api.get('/cortes/mi/resumen/mes'),
      ])
      setDia(rDia.data)
      setSemana(rSemana.data)
      setMes(rMes.data)
    } catch (error) {
      console.error('Error cargando resúmenes:', error)
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

  const fechaHoy = dia?.fecha ? formatearFecha(dia.fecha) : ''

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Hola, {usuario?.nombre}</h1>
            <p className="pagina__descripcion">{fechaHoy}</p>
          </div>
        </header>

        {/* La acción principal de la jornada, siempre a mano */}
        <div className="dashboard__cta">
          <Link to="/cortes" className="ui-boton ui-boton--primario">
            <Scissors size={16} aria-hidden="true" />
            Registrar corte
          </Link>
          <span className="texto-suave texto-pequeno">
            Tu parte de cada corte se acredita al instante.
          </span>
        </div>

        <div className="rejilla rejilla--3">
          <Tarjeta>
            <Cifra
              etiqueta="Hoy"
              valor={formatearEntero(dia?.total_cortes ?? 0)}
              pie={`${pluralizar(dia?.total_cortes ?? 0, 'corte', 'cortes')} · ${formatearMoneda(dia?.acumulado ?? 0)} para vos`}
              destacada
            />
          </Tarjeta>

          <Tarjeta>
            <Cifra
              etiqueta="Esta semana"
              valor={formatearEntero(semana?.total_cortes ?? 0)}
              pie={`${pluralizar(semana?.total_cortes ?? 0, 'corte', 'cortes')} · ${formatearMoneda(semana?.acumulado ?? 0)} para vos`}
              destacada
            />
          </Tarjeta>

          <Tarjeta>
            <Cifra
              etiqueta="Este mes"
              valor={formatearEntero(mes?.total_cortes ?? 0)}
              pie={`${pluralizar(mes?.total_cortes ?? 0, 'corte', 'cortes')} · ${formatearMoneda(mes?.acumulado ?? 0)} para vos`}
              destacada
            />
          </Tarjeta>
        </div>

        <Tarjeta titulo="Tu porcentaje">
          <div className="dashboard__porcentaje">
            <span className="dashboard__porcentaje-valor">
              {usuario?.porcentaje_ganancia}%
            </span>
            <span className="texto-suave">
              de cada servicio facturado corresponde a tu parte.
            </span>
          </div>
        </Tarjeta>
      </div>
    </div>
  )
}
