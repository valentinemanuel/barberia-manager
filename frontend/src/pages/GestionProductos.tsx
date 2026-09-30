import { useEffect, useState } from 'react'
import api from '../services/api'

interface Producto {
  id: number
  nombre: string
  descripcion: string
  precio: number
  stock: number
  stock_minimo: number
  activo: boolean
}

export default function GestionProductos() {
  const [productos, setProductos] = useState<Producto[]>([])
  const [modalAbierto, setModalAbierto] = useState(false)
  const [productoEditando, setProductoEditando] = useState<Producto | null>(null)
  const [formulario, setFormulario] = useState({
    nombre: '',
    descripcion: '',
    precio: 0,
    stock: 0,
    stock_minimo: 5,
  })

  useEffect(() => {
    cargarProductos()
  }, [])

  const cargarProductos = async () => {
    try {
      const response = await api.get('/productos/')
      setProductos(response.data)
    } catch (error) {
      console.error('Error cargando productos:', error)
    }
  }

  const abrirModal = (producto?: Producto) => {
    if (producto) {
      setProductoEditando(producto)
      setFormulario({
        nombre: producto.nombre,
        descripcion: producto.descripcion || '',
        precio: producto.precio,
        stock: producto.stock,
        stock_minimo: producto.stock_minimo,
      })
    } else {
      setProductoEditando(null)
      setFormulario({
        nombre: '',
        descripcion: '',
        precio: 0,
        stock: 0,
        stock_minimo: 5,
      })
    }
    setModalAbierto(true)
  }

  const guardarProducto = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (productoEditando) {
        await api.put(`/productos/${productoEditando.id}`, formulario)
      } else {
        await api.post('/productos/', formulario)
      }
      setModalAbierto(false)
      cargarProductos()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al guardar')
    }
  }

  const eliminarProducto = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este producto?')) return
    try {
      await api.delete(`/productos/${id}`)
      cargarProductos()
    } catch (error) {
      console.error('Error eliminando producto:', error)
    }
  }

  return (
    <div>
      <div className="flex flex-between mb-4">
        <h2 className="text-2xl font-bold">Gestión de Productos 📦</h2>
        <button className="btn btn-primary" onClick={() => abrirModal()}>
          + Nuevo Producto
        </button>
      </div>

      <div className="grid grid-3">
        {productos.map((producto) => (
          <div key={producto.id} className="card">
            <h3 className="font-bold text-lg">{producto.nombre}</h3>
            <p className="text-sm text-[var(--color-text-muted)] mb-2">
              {producto.descripcion}
            </p>
            <p className="text-2xl font-bold text-[var(--color-highlight)]">
              ${producto.precio.toFixed(2)}
            </p>
            <p className={`text-sm ${
              producto.stock <= producto.stock_minimo
                ? 'text-[var(--color-danger)] font-semibold'
                : 'text-[var(--color-text-muted)]'
            }`}>
              Stock: {producto.stock} {producto.stock <= producto.stock_minimo && '⚠️'}
            </p>
            <div className="flex gap-2 mt-3">
              <button
                className="btn btn-secondary text-sm py-1 px-3"
                onClick={() => abrirModal(producto)}
              >
                Editar
              </button>
              <button
                className="btn btn-danger text-sm py-1 px-3"
                onClick={() => eliminarProducto(producto.id)}
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
              {productoEditando ? 'Editar Producto' : 'Nuevo Producto'}
            </h3>
            <form onSubmit={guardarProducto}>
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
              <div className="grid grid-3 gap-2 mb-4">
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
                  <label className="label">Stock</label>
                  <input
                    type="number"
                    className="input"
                    value={formulario.stock}
                    onChange={(e) => setFormulario({...formulario, stock: Number(e.target.value)})}
                    required
                  />
                </div>
                <div>
                  <label className="label">Stock Mín.</label>
                  <input
                    type="number"
                    className="input"
                    value={formulario.stock_minimo}
                    onChange={(e) => setFormulario({...formulario, stock_minimo: Number(e.target.value)})}
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
