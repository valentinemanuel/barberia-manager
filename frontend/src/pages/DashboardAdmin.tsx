import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Package, ArrowRight, BarChart3 } from 'lucide-react'
import api from '../services/api'
import { Tarjeta, Cifra, Vacio, SkeletonLineas } from '../components/ui'
import { formatearMoneda, formatearEntero, pluralizar } from '../utils/formato'

interface ReporteBarbero {
  barbero_id: number
  nombre_barbero: string
  cantidad_cortes: number
  total_bruto: number
  parte_barbero: number
  parte_barberia: number
}

interface ProductoTop {
  producto_id: number
  total_vendido: number
}

interface DashboardData {
  ganancias_hoy: number
  ganancias_semana: number
  ganancias_mes: number
  cortes_hoy: number
  cortes_semana: number
  cortes_mes: number
  top_barberos: ReporteBarbero[]
  productos_mas_vendidos: ProductoTop[]
}

/**
 * Vista del admin: "el día de la casa".
 * Una cifra manda (ganancia de hoy) y el resto la acompaña; abajo,
 * ranking de barberos y productos, con datos del mes.
 */
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

  if (!datos) {
    return (
      <div className="contenedor">
        <Vacio
          icono={<BarChart3 size={32} />}
          titulo="No pudimos cargar el resumen"
          texto="Revisá la conexión con el servidor y recargá la pantalla."
          accion={
            <button type="button" className="ui-boton ui-boton--secundario" onClick={cargarDashboard}>
              Reintentar
            </button>
          }
        />
      </div>
    )
  }

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Resumen del día</h1>
            <p className="pagina__descripcion">La casa, de un vistazo.</p>
          </div>
          <Link to="/reportes" className="ui-boton ui-boton--secundario">
            Ver reportes
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </header>

        {/* Ledger: la cifra del día manda */}
        <div className="rejilla rejilla--2">
          <Tarjeta>
            <Cifra
              etiqueta="Ganancia de hoy"
              valor={formatearMoneda(datos.ganancias_hoy)}
              pie={`${formatearEntero(datos.cortes_hoy)} ${pluralizar(datos.cortes_hoy, 'corte registrado', 'cortes registrados')}`}
              destacada
            />
            <div className="dashboard__periodos">
              <Cifra
                etiqueta="Semana"
                valor={formatearMoneda(datos.ganancias_semana)}
                pie={`${formatearEntero(datos.cortes_semana)} ${pluralizar(datos.cortes_semana, 'corte', 'cortes')}`}
              />
              <Cifra
                etiqueta="Mes"
                valor={formatearMoneda(datos.ganancias_mes)}
                pie={`${formatearEntero(datos.cortes_mes)} ${pluralizar(datos.cortes_mes, 'corte', 'cortes')}`}
              />
            </div>
          </Tarjeta>

          <Tarjeta titulo="Barberos del mes">
            {datos.top_barberos.length === 0 ? (
              <p className="texto-suave">
                Todavía no hay cortes este mes. Los primeros del mes aparecen acá.
              </p>
            ) : (
              <ul className="dashboard__lista">
                {datos.top_barberos.map((barbero, indice) => (
                  <li key={barbero.barbero_id} className="dashboard__fila">
                    <span className="dashboard__orden cifra">{indice + 1}</span>
                    <span className="dashboard__fila-nombre">
                      {barbero.nombre_barbero}
                    </span>
                    <span className="dashboard__fila-valor cifra">
                      {formatearEntero(barbero.cantidad_cortes)}{' '}
                      {pluralizar(barbero.cantidad_cortes, 'corte', 'cortes')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Tarjeta>
        </div>

        <Tarjeta titulo="Productos más vendidos (mes)">
          {datos.productos_mas_vendidos.length === 0 ? (
            <p className="texto-suave">
              Sin ventas de productos este mes.{' '}
              <Link to="/productos" className="dashboard__enlace">
                Revisá el stock
              </Link>
              .
            </p>
          ) : (
            <ul className="dashboard__lista">
              {datos.productos_mas_vendidos.map((producto) => (
                <li key={producto.producto_id} className="dashboard__fila">
                  <span className="dashboard__orden">
                    <Package size={16} aria-hidden="true" />
                  </span>
                  <span className="dashboard__fila-nombre">
                    Producto #{producto.producto_id}
                  </span>
                  <span className="dashboard__fila-valor cifra">
                    {formatearEntero(producto.total_vendido)} uds
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      </div>
    </div>
  )
}
