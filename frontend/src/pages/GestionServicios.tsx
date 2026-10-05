import { useEffect, useState } from 'react'
import { ClipboardList, Plus } from 'lucide-react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import {
  Boton,
  Tarjeta,
  Campo,
  Modal,
  Vacio,
  SkeletonLineas,
  useToast,
} from '../components/ui'
import { formatearMoneda } from '../utils/formato'

interface Servicio {
  id: number
  nombre: string
  descripcion: string
  precio: number
  duracion_minutos: number
  activo: boolean
}

const formularioVacio = {
  nombre: '',
  descripcion: '',
  precio: 0,
  duracion_minutos: 30,
}

export default function GestionServicios() {
  const { mostrar } = useToast()
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [cargando, setCargando] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [servicioEditando, setServicioEditando] = useState<Servicio | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [porEliminar, setPorEliminar] = useState<Servicio | null>(null)
  const [formulario, setFormulario] = useState(formularioVacio)
  // El error de precio no debe gritar antes de que el usuario toque el campo
  const [precioTocado, setPrecioTocado] = useState(false)

  useEffect(() => {
    cargarServicios()
  }, [])

  const cargarServicios = async () => {
    try {
      const response = await api.get('/servicios/')
      setServicios(response.data)
    } catch (error) {
      console.error('Error cargando servicios:', error)
      mostrar('error', 'No se pudieron cargar los servicios')
    } finally {
      setCargando(false)
    }
  }

  const abrirModal = (servicio?: Servicio) => {
    setServicioEditando(servicio ?? null)
    setPrecioTocado(false)
    setFormulario(
      servicio
        ? {
            nombre: servicio.nombre,
            descripcion: servicio.descripcion || '',
            precio: servicio.precio,
            duracion_minutos: servicio.duracion_minutos,
          }
        : formularioVacio
    )
    setModalAbierto(true)
  }

  const guardar = async () => {
    setGuardando(true)
    try {
      if (servicioEditando) {
        await api.put(`/servicios/${servicioEditando.id}`, formulario)
      } else {
        await api.post('/servicios/', formulario)
      }
      setModalAbierto(false)
      mostrar('exito', servicioEditando ? 'Servicio actualizado' : 'Servicio creado')
      cargarServicios()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo guardar el servicio'))
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async () => {
    if (!porEliminar) return
    try {
      await api.delete(`/servicios/${porEliminar.id}`)
      mostrar('exito', `${porEliminar.nombre} eliminado`)
      setPorEliminar(null)
      cargarServicios()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo eliminar el servicio'))
    }
  }

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Servicios</h1>
            <p className="pagina__descripcion">
              Lo que se corta y cuánto vale cada cosa.
            </p>
          </div>
          <Boton onClick={() => abrirModal()}>
            <Plus size={16} aria-hidden="true" />
            Nuevo servicio
          </Boton>
        </header>

        {cargando ? (
          <div className="ui-tarjeta">
            <SkeletonLineas cantidad={4} />
          </div>
        ) : servicios.length === 0 ? (
          <Vacio
            icono={<ClipboardList size={32} />}
            titulo="Todavía no hay servicios"
            texto="Cargá el primer servicio para poder registrar cortes."
            accion={
              <Boton onClick={() => abrirModal()}>
                <Plus size={16} aria-hidden="true" />
                Nuevo servicio
              </Boton>
            }
          />
        ) : (
          <div className="rejilla rejilla--3">
            {servicios.map((servicio) => (
              <Tarjeta
                key={servicio.id}
                titulo={servicio.nombre}
                acciones={
                  <span className="gestion__fila-acciones">
                    <Boton variante="secundario" tamano="peq" onClick={() => abrirModal(servicio)}>
                      Editar
                    </Boton>
                    <Boton variante="peligro" tamano="peq" onClick={() => setPorEliminar(servicio)}>
                      Eliminar
                    </Boton>
                  </span>
                }
              >
                <p className="texto-suave texto-pequeno">{servicio.descripcion}</p>
                <p className="ui-cifra__valor cifra" style={{ marginTop: 'var(--sp-3)' }}>
                  {formatearMoneda(servicio.precio)}
                </p>
                <p className="texto-suave texto-pequeno">
                  {servicio.duracion_minutos} minutos
                </p>
              </Tarjeta>
            ))}
          </div>
        )}
      </div>

      <Modal
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        titulo={servicioEditando ? 'Editar servicio' : 'Nuevo servicio'}
        onConfirmar={guardar}
        cargando={guardando}
        confirmarDeshabilitado={!formulario.nombre.trim() || formulario.precio <= 0}
      >
        <div className="pagina">
          <Campo etiqueta="Nombre" id="servicio-nombre">
            <input
              id="servicio-nombre"
              className="ui-campo__control"
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
              required
            />
          </Campo>

          <Campo etiqueta="Descripción" id="servicio-descripcion" pista="Opcional">
            <input
              id="servicio-descripcion"
              className="ui-campo__control"
              value={formulario.descripcion}
              onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
            />
          </Campo>

          <div className="rejilla rejilla--2">
            <Campo
              etiqueta="Precio"
              id="servicio-precio"
              error={precioTocado && formulario.precio <= 0 ? 'Debe ser mayor a 0' : undefined}
            >
              <input
                id="servicio-precio"
                type="number"
                step="0.01"
                min="0"
                className="ui-campo__control"
                value={formulario.precio}
                onChange={(e) => setFormulario({ ...formulario, precio: Number(e.target.value) })}
                onBlur={() => setPrecioTocado(true)}
              />
            </Campo>

            <Campo etiqueta="Duración (min)" id="servicio-duracion">
              <input
                id="servicio-duracion"
                type="number"
                min="5"
                step="5"
                className="ui-campo__control"
                value={formulario.duracion_minutos}
                onChange={(e) =>
                  setFormulario({ ...formulario, duracion_minutos: Number(e.target.value) })
                }
              />
            </Campo>
          </div>
        </div>
      </Modal>

      <Modal
        abierto={Boolean(porEliminar)}
        onCerrar={() => setPorEliminar(null)}
        titulo="Eliminar servicio"
        onConfirmar={eliminar}
        textoConfirmar="Eliminar"
      >
        <p>
          Vas a eliminar <strong>{porEliminar?.nombre}</strong>. Los cortes ya
          registrados no se modifican.
        </p>
      </Modal>
    </div>
  )
}
