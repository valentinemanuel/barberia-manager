import { useEffect, useState } from 'react'
import { Package, Plus, TriangleAlert } from 'lucide-react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import {
  Boton,
  Tarjeta,
  Campo,
  Insignia,
  Modal,
  Vacio,
  SkeletonLineas,
  useToast,
} from '../components/ui'
import { formatearMoneda, formatearEntero } from '../utils/formato'

interface Producto {
  id: number
  nombre: string
  descripcion: string
  precio: number
  stock: number
  stock_minimo: number
  activo: boolean
}

const formularioVacio = {
  nombre: '',
  descripcion: '',
  precio: 0,
  stock: 0,
  stock_minimo: 5,
}

export default function GestionProductos() {
  const { mostrar } = useToast()
  const [productos, setProductos] = useState<Producto[]>([])
  const [cargando, setCargando] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [productoEditando, setProductoEditando] = useState<Producto | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [porEliminar, setPorEliminar] = useState<Producto | null>(null)
  const [formulario, setFormulario] = useState(formularioVacio)
  // El error de precio no debe gritar antes de que el usuario toque el campo
  const [precioTocado, setPrecioTocado] = useState(false)

  useEffect(() => {
    cargarProductos()
  }, [])

  const cargarProductos = async () => {
    try {
      const response = await api.get('/productos/')
      setProductos(response.data)
    } catch (error) {
      console.error('Error cargando productos:', error)
      mostrar('error', 'No se pudieron cargar los productos')
    } finally {
      setCargando(false)
    }
  }

  const abrirModal = (producto?: Producto) => {
    setProductoEditando(producto ?? null)
    setPrecioTocado(false)
    setFormulario(
      producto
        ? {
            nombre: producto.nombre,
            descripcion: producto.descripcion || '',
            precio: producto.precio,
            stock: producto.stock,
            stock_minimo: producto.stock_minimo,
          }
        : formularioVacio
    )
    setModalAbierto(true)
  }

  const guardar = async () => {
    setGuardando(true)
    try {
      if (productoEditando) {
        await api.put(`/productos/${productoEditando.id}`, formulario)
      } else {
        await api.post('/productos/', formulario)
      }
      setModalAbierto(false)
      mostrar('exito', productoEditando ? 'Producto actualizado' : 'Producto creado')
      cargarProductos()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo guardar el producto'))
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async () => {
    if (!porEliminar) return
    try {
      await api.delete(`/productos/${porEliminar.id}`)
      mostrar('exito', `${porEliminar.nombre} eliminado`)
      setPorEliminar(null)
      cargarProductos()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo eliminar el producto'))
    }
  }

  const conStockBajo = (producto: Producto) => producto.stock <= producto.stock_minimo

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Productos</h1>
            <p className="pagina__descripcion">
              Inventario de venta y avisos de stock bajo.
            </p>
          </div>
          <Boton onClick={() => abrirModal()}>
            <Plus size={16} aria-hidden="true" />
            Nuevo producto
          </Boton>
        </header>

        {cargando ? (
          <div className="ui-tarjeta">
            <SkeletonLineas cantidad={4} />
          </div>
        ) : productos.length === 0 ? (
          <Vacio
            icono={<Package size={32} />}
            titulo="No hay productos cargados"
            texto="Cargá el primer producto para poder venderlo desde la caja."
            accion={
              <Boton onClick={() => abrirModal()}>
                <Plus size={16} aria-hidden="true" />
                Nuevo producto
              </Boton>
            }
          />
        ) : (
          <div className="rejilla rejilla--3">
            {productos.map((producto) => (
              <Tarjeta
                key={producto.id}
                titulo={
                  <span className="fila fila--envolver" style={{ gap: 'var(--sp-2)' }}>
                    {producto.nombre}
                    {conStockBajo(producto) && (
                      <Insignia tono="peligro">
                        <TriangleAlert size={12} aria-hidden="true" />
                        Stock bajo
                      </Insignia>
                    )}
                  </span>
                }
                acciones={
                  <span className="gestion__fila-acciones">
                    <Boton variante="secundario" tamano="peq" onClick={() => abrirModal(producto)}>
                      Editar
                    </Boton>
                    <Boton variante="peligro" tamano="peq" onClick={() => setPorEliminar(producto)}>
                      Eliminar
                    </Boton>
                  </span>
                }
              >
                <p className="texto-suave texto-pequeno">{producto.descripcion}</p>
                <p className="ui-cifra__valor cifra" style={{ marginTop: 'var(--sp-3)' }}>
                  {formatearMoneda(producto.precio)}
                </p>
                <p className="texto-suave texto-pequeno">
                  Stock: {formatearEntero(producto.stock)} unidades
                  {producto.stock_minimo > 0 && ` · mínimo ${formatearEntero(producto.stock_minimo)}`}
                </p>
              </Tarjeta>
            ))}
          </div>
        )}
      </div>

      <Modal
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        titulo={productoEditando ? 'Editar producto' : 'Nuevo producto'}
        onConfirmar={guardar}
        cargando={guardando}
        confirmarDeshabilitado={!formulario.nombre.trim() || formulario.precio <= 0}
      >
        <div className="pagina">
          <Campo etiqueta="Nombre" id="producto-nombre">
            <input
              id="producto-nombre"
              className="ui-campo__control"
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
              required
            />
          </Campo>

          <Campo etiqueta="Descripción" id="producto-descripcion" pista="Opcional">
            <input
              id="producto-descripcion"
              className="ui-campo__control"
              value={formulario.descripcion}
              onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
            />
          </Campo>

          <div className="rejilla rejilla--3">
            <Campo
              etiqueta="Precio"
              id="producto-precio"
              error={precioTocado && formulario.precio <= 0 ? 'Debe ser mayor a 0' : undefined}
            >
              <input
                id="producto-precio"
                type="number"
                step="0.01"
                min="0"
                className="ui-campo__control"
                value={formulario.precio}
                onChange={(e) => setFormulario({ ...formulario, precio: Number(e.target.value) })}
                onBlur={() => setPrecioTocado(true)}
              />
            </Campo>

            <Campo etiqueta="Stock" id="producto-stock">
              <input
                id="producto-stock"
                type="number"
                min="0"
                className="ui-campo__control"
                value={formulario.stock}
                onChange={(e) => setFormulario({ ...formulario, stock: Number(e.target.value) })}
              />
            </Campo>

            <Campo etiqueta="Stock mínimo" id="producto-minimo" pista="Aviso al llegar">
              <input
                id="producto-minimo"
                type="number"
                min="0"
                className="ui-campo__control"
                value={formulario.stock_minimo}
                onChange={(e) =>
                  setFormulario({ ...formulario, stock_minimo: Number(e.target.value) })
                }
              />
            </Campo>
          </div>
        </div>
      </Modal>

      <Modal
        abierto={Boolean(porEliminar)}
        onCerrar={() => setPorEliminar(null)}
        titulo="Eliminar producto"
        onConfirmar={eliminar}
        textoConfirmar="Eliminar"
      >
        <p>
          Vas a eliminar <strong>{porEliminar?.nombre}</strong> del inventario.
        </p>
      </Modal>
    </div>
  )
}
