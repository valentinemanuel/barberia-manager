import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'

interface Servicio {
  id: number
  nombre: string
  descripcion: string
  precio: number
  duracion_minutos: number
  activo: boolean
}

export default function GestionServicios() {
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [modalAbierto, setModalAbierto] = useState(false)
  const [servicioEditando, setServicioEditando] = useState<Servicio | null>(null)
  const [formulario, setFormulario] = useState({
    nombre: '',
    descripcion: '',
    precio: 0,
    duracion_minutos: 30,
  })

  useEffect(() => {
    cargarServicios()
  }, [])

  const cargarServicios = async () => {
    try {
      const response = await api.get('/servicios/')
      setServicios(response.data)
    } catch (error) {
      console.error('Error cargando servicios:', error)
    }
  }

  const abrirModal = (servicio?: Servicio) => {
    if (servicio) {
      setServicioEditando(servicio)
      setFormulario({
        nombre: servicio.nombre,
        descripcion: servicio.descripcion || '',
        precio: servicio.precio,
        duracion_minutos: servicio.duracion_minutos,
      })
    } else {
      setServicioEditando(null)
      setFormulario({
        nombre: '',
        descripcion: '',
        precio: 0,
        duracion_minutos: 30,
      })
    }
    setModalAbierto(true)
  }

  const guardarServicio = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (servicioEditando) {
        await api.put(`/servicios/${servicioEditando.id}`, formulario)
      } else {
        await api.post('/servicios/', formulario)
      }
      setModalAbierto(false)
      cargarServicios()
    } catch (error: any) {
      alert(mensajeError(error, 'Error al guardar'))
    }
  }

  const eliminarServicio = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este servicio?')) return
    try {
      await api.delete(`/servicios/${id}`)
      cargarServicios()
    } catch (error) {
      console.error('Error eliminando servicio:', error)
    }
  }

  return (
    <div>
      <div className="flex flex-between mb-4">
        <h2 className="text-2xl font-bold">Gestión de Servicios 📋</h2>
        <button className="btn btn-primary" onClick={() => abrirModal()}>
          + Nuevo Servicio
        </button>
      </div>

      <div className="grid grid-3">
        {servicios.map((servicio) => (
          <div key={servicio.id} className="card">
            <h3 className="font-bold text-lg">{servicio.nombre}</h3>
            <p className="text-sm text-[var(--color-text-muted)] mb-2">
              {servicio.descripcion}
            </p>
            <p className="text-2xl font-bold text-[var(--color-highlight)]">
              ${servicio.precio.toFixed(2)}
            </p>
            <p className="text-sm text-[var(--color-text-muted)]">
              {servicio.duracion_minutos} min
            </p>
            <div className="flex gap-2 mt-3">
              <button
                className="btn btn-secondary text-sm py-1 px-3"
                onClick={() => abrirModal(servicio)}
              >
                Editar
              </button>
              <button
                className="btn btn-danger text-sm py-1 px-3"
                onClick={() => eliminarServicio(servicio.id)}
              >
                Eliminar
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="card w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">
              {servicioEditando ? 'Editar Servicio' : 'Nuevo Servicio'}
            </h3>
            <form onSubmit={guardarServicio}>
              <div className="mb-3">
                <label className="label">Nombre</label>
                <input
                  className="input"
                  value={formulario.nombre}
                  onChange={(e) => setFormulario({...formulario, nombre: e.target.value})}
                  required
                />
              </div>
              <div className="mb-3">
                <label className="label">Descripción</label>
                <input
                  className="input"
                  value={formulario.descripcion}
                  onChange={(e) => setFormulario({...formulario, descripcion: e.target.value})}
                />
              </div>
              <div className="grid grid-2 gap-2 mb-4">
                <div>
                  <label className="label">Precio ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    className="input"
                    value={formulario.precio}
                    onChange={(e) => setFormulario({...formulario, precio: Number(e.target.value)})}
                    required
                  />
                </div>
                <div>
                  <label className="label">Duración (min)</label>
                  <input
                    type="number"
                    className="input"
                    value={formulario.duracion_minutos}
                    onChange={(e) => setFormulario({...formulario, duracion_minutos: Number(e.target.value)})}
                    required
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn btn-secondary flex-1" onClick={() => setModalAbierto(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary flex-1">
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
