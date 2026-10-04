import { useEffect, useState } from 'react'
import api from '../services/api'
import { mensajeError } from '../services/error'

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

export default function GestionUsuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [modalAbierto, setModalAbierto] = useState(false)
  const [usuarioEditando, setUsuarioEditando] = useState<Usuario | null>(null)
  const [formulario, setFormulario] = useState({
    nombre: '',
    apellido: '',
    email: '',
    usuario: '',
    password: '',
    rol: 'barbero' as 'admin' | 'barbero',
    porcentaje_ganancia: 0,
  })

  useEffect(() => {
    cargarUsuarios()
  }, [])

  const cargarUsuarios = async () => {
    try {
      const response = await api.get('/usuarios/')
      setUsuarios(response.data)
    } catch (error) {
      console.error('Error cargando usuarios:', error)
    }
  }

  const abrirModal = (usuario?: Usuario) => {
    if (usuario) {
      setUsuarioEditando(usuario)
      setFormulario({
        nombre: usuario.nombre,
        apellido: usuario.apellido,
        email: usuario.email,
        usuario: usuario.usuario,
        password: '',
        rol: usuario.rol,
        porcentaje_ganancia: usuario.porcentaje_ganancia,
      })
    } else {
      setUsuarioEditando(null)
      setFormulario({
        nombre: '',
        apellido: '',
        email: '',
        usuario: '',
        password: '',
        rol: 'barbero',
        porcentaje_ganancia: 0,
      })
    }
    setModalAbierto(true)
  }

  const guardarUsuario = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (usuarioEditando) {
        await api.put(`/usuarios/${usuarioEditando.id}`, formulario)
      } else {
        await api.post('/usuarios/', formulario)
      }
      setModalAbierto(false)
      cargarUsuarios()
    } catch (error: any) {
      alert(mensajeError(error, 'Error al guardar'))
    }
  }

  const eliminarUsuario = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este usuario?')) return
    try {
      await api.delete(`/usuarios/${id}`)
      cargarUsuarios()
    } catch (error) {
      console.error('Error eliminando usuario:', error)
    }
  }

  return (
    <div>
      <div className="flex flex-between mb-4">
        <h2 className="text-2xl font-bold">Gestión de Usuarios 👥</h2>
        <button className="btn btn-primary" onClick={() => abrirModal()}>
          + Nuevo Usuario
        </button>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left p-2">Nombre</th>
              <th className="text-left p-2">Usuario</th>
              <th className="text-left p-2">Rol</th>
              <th className="text-left p-2">% Ganancia</th>
              <th className="text-left p-2">Estado</th>
              <th className="text-left p-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((usuario) => (
              <tr key={usuario.id} className="border-b">
                <td className="p-2">{usuario.nombre} {usuario.apellido}</td>
                <td className="p-2">{usuario.usuario}</td>
                <td className="p-2">
                  <span className={`px-2 py-1 rounded text-xs ${
                    usuario.rol === 'admin'
                      ? 'bg-purple-100 text-purple-600'
                      : 'bg-blue-100 text-blue-600'
                  }`}>
                    {usuario.rol}
                  </span>
                </td>
                <td className="p-2">{usuario.porcentaje_ganancia}%</td>
                <td className="p-2">
                  <span className={`px-2 py-1 rounded text-xs ${
                    usuario.activo
                      ? 'bg-green-100 text-green-600'
                      : 'bg-red-100 text-red-600'
                  }`}>
                    {usuario.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="p-2">
                  <button
                    className="btn btn-secondary text-sm py-1 px-2 mr-2"
                    onClick={() => abrirModal(usuario)}
                  >
                    Editar
                  </button>
                  <button
                    className="btn btn-danger text-sm py-1 px-2"
                    onClick={() => eliminarUsuario(usuario.id)}
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {modalAbierto && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="card w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">
              {usuarioEditando ? 'Editar Usuario' : 'Nuevo Usuario'}
            </h3>
            <form onSubmit={guardarUsuario}>
              <div className="grid grid-2 gap-2 mb-3">
                <div>
                  <label className="label">Nombre</label>
                  <input
                    className="input"
                    value={formulario.nombre}
                    onChange={(e) => setFormulario({...formulario, nombre: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <label className="label">Apellido</label>
                  <input
                    className="input"
                    value={formulario.apellido}
                    onChange={(e) => setFormulario({...formulario, apellido: e.target.value})}
                    required
                  />
                </div>
              </div>
              <div className="mb-3">
                <label className="label">Email</label>
                <input
                  type="email"
                  className="input"
                  value={formulario.email}
                  onChange={(e) => setFormulario({...formulario, email: e.target.value})}
                  required
                />
              </div>
              <div className="mb-3">
                <label className="label">Usuario</label>
                <input
                  className="input"
                  value={formulario.usuario}
                  onChange={(e) => setFormulario({...formulario, usuario: e.target.value})}
                  required
                />
              </div>
              <div className="mb-3">
                <label className="label">
                  Contraseña {usuarioEditando && '(dejar vacío para no cambiar)'}
                </label>
                <input
                  type="password"
                  className="input"
                  value={formulario.password}
                  onChange={(e) => setFormulario({...formulario, password: e.target.value})}
                  required={!usuarioEditando}
                />
              </div>
              <div className="grid grid-2 gap-2 mb-4">
                <div>
                  <label className="label">Rol</label>
                  <select
                    className="input"
                    value={formulario.rol}
                    onChange={(e) => setFormulario({...formulario, rol: e.target.value as 'admin' | 'barbero'})}
                  >
                    <option value="barbero">Barbero</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className="label">% Ganancia</label>
                  <input
                    type="number"
                    className="input"
                    value={formulario.porcentaje_ganancia}
                    onChange={(e) => setFormulario({...formulario, porcentaje_ganancia: Number(e.target.value)})}
                    min="0"
                    max="100"
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
