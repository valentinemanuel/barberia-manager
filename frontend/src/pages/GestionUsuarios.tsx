import { useEffect, useState } from 'react'
import { Users, Plus } from 'lucide-react'
import api from '../services/api'
import { validarPorcentajeStr } from '../services/cortesApi'
import { mensajeError } from '../services/error'
import {
  Boton,
  Campo,
  Insignia,
  Modal,
  Tabla,
  Vacio,
  SkeletonLineas,
  useToast,
} from '../components/ui'

interface Usuario {
  id: number
  nombre: string
  apellido: string
  email: string
  usuario: string
  rol: 'admin' | 'barbero'
  porcentaje_ganancia: number
  activo: boolean
}

const formularioVacio = {
  nombre: '',
  apellido: '',
  email: '',
  usuario: '',
  password: '',
  rol: 'barbero' as 'admin' | 'barbero',
  porcentaje_ganancia: '',
}

/** Porcentaje del formulario valido (0 a 100, 2 decimales maximo). */
function porcentajeValido(valor: string): boolean {
  try {
    validarPorcentajeStr(valor.trim())
    return true
  } catch {
    return false
  }
}

export default function GestionUsuarios() {
  const { mostrar } = useToast()
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [cargando, setCargando] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [usuarioEditando, setUsuarioEditando] = useState<Usuario | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [porEliminar, setPorEliminar] = useState<Usuario | null>(null)
  const [formulario, setFormulario] = useState(formularioVacio)

  useEffect(() => {
    cargarUsuarios()
  }, [])

  const cargarUsuarios = async () => {
    try {
      const response = await api.get('/usuarios/')
      setUsuarios(response.data)
    } catch (error) {
      console.error('Error cargando usuarios:', error)
      mostrar('error', 'No se pudieron cargar los usuarios')
    } finally {
      setCargando(false)
    }
  }

  const abrirModal = (usuario?: Usuario) => {
    setUsuarioEditando(usuario ?? null)
    setFormulario(
      usuario
        ? {
            nombre: usuario.nombre,
            apellido: usuario.apellido,
            email: usuario.email,
            usuario: usuario.usuario,
            password: '',
            rol: usuario.rol,
            porcentaje_ganancia: String(usuario.porcentaje_ganancia),
          }
        : formularioVacio
    )
    setModalAbierto(true)
  }

  const guardar = async () => {
    setGuardando(true)
    try {
      if (usuarioEditando) {
        await api.put(`/usuarios/${usuarioEditando.id}`, formulario)
      } else {
        await api.post('/usuarios/', formulario)
      }
      setModalAbierto(false)
      mostrar('exito', usuarioEditando ? 'Usuario actualizado' : 'Usuario creado')
      cargarUsuarios()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo guardar el usuario'))
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async () => {
    if (!porEliminar) return
    try {
      await api.delete(`/usuarios/${porEliminar.id}`)
      mostrar('exito', `${porEliminar.nombre} ${porEliminar.apellido} eliminado`)
      setPorEliminar(null)
      cargarUsuarios()
    } catch (error: unknown) {
      mostrar('error', mensajeError(error, 'No se pudo eliminar el usuario'))
    }
  }

  const formCompleto =
    formulario.nombre.trim() &&
    formulario.apellido.trim() &&
    formulario.usuario.trim() &&
    porcentajeValido(formulario.porcentaje_ganancia) &&
    (usuarioEditando || formulario.password)

  return (
    <div className="contenedor">
      <div className="pagina">
        <header className="pagina__cabecera">
          <div>
            <h1>Usuarios</h1>
            <p className="pagina__descripcion">
              Equipo de la casa: roles y porcentajes.
            </p>
          </div>
          <Boton onClick={() => abrirModal()}>
            <Plus size={16} aria-hidden="true" />
            Nuevo usuario
          </Boton>
        </header>

        {cargando ? (
          <div className="ui-tarjeta">
            <SkeletonLineas cantidad={5} />
          </div>
        ) : usuarios.length === 0 ? (
          <Vacio
            icono={<Users size={32} />}
            titulo="Sin usuarios cargados"
            texto="Cargá a los barberos del equipo para que puedan registrar cortes."
            accion={
              <Boton onClick={() => abrirModal()}>
                <Plus size={16} aria-hidden="true" />
                Nuevo usuario
              </Boton>
            }
          />
        ) : (
          <Tabla
            columnas={['Nombre', 'Usuario', 'Rol', '% ganancia', 'Estado', '']}
          >
            {usuarios.map((usuario) => (
              <tr key={usuario.id}>
                <td>
                  {usuario.nombre} {usuario.apellido}
                </td>
                <td className="texto-suave">{usuario.usuario}</td>
                <td>
                  <Insignia tono={usuario.rol === 'admin' ? 'laton' : 'info'}>
                    {usuario.rol === 'admin' ? 'Admin' : 'Barbero'}
                  </Insignia>
                </td>
                <td className="cifra">{usuario.porcentaje_ganancia}%</td>
                <td>
                  <Insignia tono={usuario.activo ? 'exito' : 'peligro'}>
                    {usuario.activo ? 'Activo' : 'Inactivo'}
                  </Insignia>
                </td>
                <td>
                  <span className="gestion__fila-acciones">
                    <Boton variante="secundario" tamano="peq" onClick={() => abrirModal(usuario)}>
                      Editar
                    </Boton>
                    <Boton variante="peligro" tamano="peq" onClick={() => setPorEliminar(usuario)}>
                      Eliminar
                    </Boton>
                  </span>
                </td>
              </tr>
            ))}
          </Tabla>
        )}
      </div>

      <Modal
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        titulo={usuarioEditando ? 'Editar usuario' : 'Nuevo usuario'}
        onConfirmar={guardar}
        cargando={guardando}
        confirmarDeshabilitado={!formCompleto}
      >
        <div className="pagina">
          <div className="rejilla rejilla--2">
            <Campo etiqueta="Nombre" id="usuario-nombre">
              <input
                id="usuario-nombre"
                className="ui-campo__control"
                value={formulario.nombre}
                onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
                required
              />
            </Campo>

            <Campo etiqueta="Apellido" id="usuario-apellido">
              <input
                id="usuario-apellido"
                className="ui-campo__control"
                value={formulario.apellido}
                onChange={(e) => setFormulario({ ...formulario, apellido: e.target.value })}
                required
              />
            </Campo>
          </div>

          <Campo etiqueta="Email" id="usuario-email">
            <input
              id="usuario-email"
              type="email"
              className="ui-campo__control"
              value={formulario.email}
              onChange={(e) => setFormulario({ ...formulario, email: e.target.value })}
              required
            />
          </Campo>

          <Campo etiqueta="Usuario" id="usuario-login">
            <input
              id="usuario-login"
              className="ui-campo__control"
              value={formulario.usuario}
              onChange={(e) => setFormulario({ ...formulario, usuario: e.target.value })}
              required
            />
          </Campo>

          <Campo
            etiqueta="Contraseña"
            id="usuario-password"
            pista={usuarioEditando ? 'Dejar vacío para no cambiar' : undefined}
            error={
              !usuarioEditando && !formulario.password
                ? 'Requerida para crear el usuario'
                : undefined
            }
          >
            <input
              id="usuario-password"
              type="password"
              className="ui-campo__control"
              autoComplete="new-password"
              value={formulario.password}
              onChange={(e) => setFormulario({ ...formulario, password: e.target.value })}
              required={!usuarioEditando}
              aria-invalid={
                !usuarioEditando && !formulario.password ? 'true' : undefined
              }
            />
          </Campo>

          <div className="rejilla rejilla--2">
            <Campo etiqueta="Rol" id="usuario-rol">
              <select
                id="usuario-rol"
                className="ui-campo__control"
                value={formulario.rol}
                onChange={(e) =>
                  setFormulario({
                    ...formulario,
                    rol: e.target.value as 'admin' | 'barbero',
                  })
                }
              >
                <option value="barbero">Barbero</option>
                <option value="admin">Admin</option>
              </select>
            </Campo>

            <Campo
              etiqueta="% ganancia"
              id="usuario-porcentaje"
              pista="Solo sobre servicios"
            >
              <input
                id="usuario-porcentaje"
                type="number"
                min="0"
                max="100"
                className="ui-campo__control"
                value={formulario.porcentaje_ganancia}
                onChange={(e) =>
                  setFormulario({
                    ...formulario,
                    porcentaje_ganancia: e.target.value,
                  })
                }
              />
            </Campo>
          </div>
        </div>
      </Modal>

      <Modal
        abierto={Boolean(porEliminar)}
        onCerrar={() => setPorEliminar(null)}
        titulo="Eliminar usuario"
        onConfirmar={eliminar}
        textoConfirmar="Eliminar"
      >
        <p>
          Vas a eliminar a <strong>{porEliminar?.nombre} {porEliminar?.apellido}</strong> del
          equipo. Su historial de cortes se conserva.
        </p>
      </Modal>
    </div>
  )
}
