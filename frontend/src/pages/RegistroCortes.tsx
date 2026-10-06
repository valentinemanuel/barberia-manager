import { useEffect, useState } from 'react'
import { CheckCircle2, CreditCard, Landmark, Banknote } from 'lucide-react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import { useAuthStore } from '../store/authStore'
import { db } from '../services/db'
import { Boton, Campo, Segmentado, Vacio, useToast } from '../components/ui'
import { formatearMoneda } from '../utils/formato'

interface Servicio {
  id: number
  nombre: string
  descripcion: string
  precio: number
  duracion_minutos: number
}

type MetodoPago = 'efectivo' | 'tarjeta' | 'transferencia'

/**
 * Registrar un corte: los servicios se eligen como tarjetas (un toque,
 * sin dropdown) y el método de pago con control segmentado.
 * Si la red falla, el corte se guarda en el dispositivo y se sincroniza después.
 */
export default function RegistroCortes() {
  const { usuario } = useAuthStore()
  const { mostrar } = useToast()
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [servicioSeleccionado, setServicioSeleccionado] = useState<number | null>(null)
  const [metodoPago, setMetodoPago] = useState<MetodoPago>('efectivo')
  const [cargando, setCargando] = useState(false)
  const [ultimoExito, setUltimoExito] = useState<string | null>(null)
  const [sinServicios, setSinServicios] = useState(false)

  useEffect(() => {
    cargarServicios()
  }, [])

  const cargarServicios = async () => {
    try {
      const response = await api.get('/servicios/')
      setServicios(response.data)
      setSinServicios(response.data.length === 0)
    } catch (error) {
      console.error('Error cargando servicios, pruebo los locales:', error)
      // Fallback offline: servicios cacheados en IndexedDB
      const locales = await db.servicios.where('activo').equals(1).toArray()
      setServicios(locales as Servicio[])
      setSinServicios(locales.length === 0)
    }
  }

  const servicio = servicios.find((s) => s.id === servicioSeleccionado) ?? null
  const ganancia =
    servicio && usuario
      ? servicio.precio * (usuario.porcentaje_ganancia / 100)
      : 0

  const registrar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!servicio) return

    setCargando(true)
    setUltimoExito(null)

    try {
      await api.post('/cortes/', {
        servicio_id: servicio.id,
        metodo_pago: metodoPago,
      })
      setUltimoExito(servicio.nombre)
      mostrar('exito', `Corte registrado: ${servicio.nombre}`)
      setServicioSeleccionado(null)
    } catch (error: unknown) {
      const huboRespuesta = Boolean(
        (error as { response?: unknown }).response
      )

      if (!huboRespuesta && usuario) {
        // Sin red: guardo en el dispositivo; useSync lo enviará al reconectar
        const parte = Math.round(servicio.precio * (usuario.porcentaje_ganancia / 100) * 100) / 100
        await db.cortes.add({
          barbero_id: usuario.id,
          servicio_id: servicio.id,
          precio: servicio.precio,
          porcentaje_barbero: usuario.porcentaje_ganancia,
          parte_barbero: parte,
          metodo_pago: metodoPago,
          fecha: new Date().toISOString(),
          sincronizado: false,
        })
        mostrar('info', 'Sin conexión: el corte quedó guardado en el dispositivo y se sincronizará solo.')
        setServicioSeleccionado(null)
      } else {
        mostrar('error', mensajeError(error, 'No se pudo registrar el corte'))
      }
    } finally {
      setCargando(false)
    }
  }

  if (sinServicios) {
    return (
      <div className="contenedor">
        <Vacio
          titulo="No hay servicios cargados"
          texto="Tocá “Servicios” para dar de alta el primero, o esperá a que sincronice si recién entraste en la barbería."
        />
      </div>
    )
  }

  return (
    <div className="contenedor">
      <div className="registro">
        <header className="pagina__cabecera">
          <div>
            <h1>Registrar corte</h1>
            <p className="pagina__descripcion">
              Elegí el servicio, cobrá como te paguen y listo.
            </p>
          </div>
        </header>

        {ultimoExito && (
          <div className="registro__exito" role="status">
            <CheckCircle2 size={18} aria-hidden="true" />
            {ultimoExito} registrado. ¿Seguimos con el próximo?
          </div>
        )}

        <form onSubmit={registrar} className="pagina">
          <fieldset className="ui-campo" style={{ border: 'none', padding: 0, margin: 0 }}>
            <legend className="ui-campo__etiqueta" style={{ padding: 0 }}>
              Servicio
            </legend>
            <div className="ui-tarjetas-seleccion">
              {servicios.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className="ui-tarjeta-seleccion"
                  role="radio"
                  aria-checked={s.id === servicioSeleccionado}
                  onClick={() => setServicioSeleccionado(s.id)}
                >
                  <span>
                    <span className="ui-tarjeta-seleccion__nombre">{s.nombre}</span>
                    <span className="ui-tarjeta-seleccion__meta" style={{ display: 'block' }}>
                      {s.duracion_minutos} min
                    </span>
                  </span>
                  <span className="ui-tarjeta-seleccion__precio">
                    {formatearMoneda(s.precio)}
                  </span>
                </button>
              ))}
            </div>
          </fieldset>

          <Campo etiqueta="Método de pago" id="metodo-pago">
            <Segmentado
              etiqueta="Método de pago"
              valor={metodoPago}
              onCambio={setMetodoPago}
              opciones={[
                { valor: 'efectivo', etiqueta: 'Efectivo', icono: <Banknote size={16} /> },
                { valor: 'tarjeta', etiqueta: 'Tarjeta', icono: <CreditCard size={16} /> },
                { valor: 'transferencia', etiqueta: 'Transferencia', icono: <Landmark size={16} /> },
              ]}
            />
          </Campo>

          {servicio && (
            <div className="registro__preview">
              <span className="registro__preview-etiqueta">
                Tu ganancia ({usuario?.porcentaje_ganancia}%)
              </span>
              <span className="registro__preview-valor cifra">
                {formatearMoneda(ganancia)}
              </span>
            </div>
          )}

          <Boton
            type="submit"
            cargando={cargando}
            disabled={!servicio}
            ancho
          >
            Registrar corte
          </Boton>
        </form>
      </div>
    </div>
  )
}
