import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scissors } from 'lucide-react'
import api from '../services/api'
import { mensajeError } from '../services/error'
import { useAuthStore } from '../store/authStore'
import { Boton, Campo } from '../components/ui'

/**
 * Pantalla de acceso. El momento de marca es la franja del poste barbero
 * a la izquierda: se desplaza en bucle suave (quieto con movimiento reducido).
 */
export default function Login() {
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setCargando(true)

    try {
      const response = await api.post('/auth/login/json', { usuario, password })
      const { access_token } = response.data

      // Obtener perfil del usuario
      const perfilResponse = await api.get('/usuarios/me/perfil', {
        headers: { Authorization: `Bearer ${access_token}` },
      })

      setAuth(access_token, perfilResponse.data)
      navigate('/')
    } catch (err: unknown) {
      setError(mensajeError(err, 'No se pudo iniciar sesión. Revisá usuario y contraseña.'))
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="login">
      {/* Franja del poste: identidad de marca */}
      <div className="login__poste" aria-hidden="true">
        <div className="login__poste-franja" />
      </div>

      <div className="login__panel">
        <div className="login__caja animar-pagina">
          <span className="login__icono">
            <Scissors size={22} aria-hidden="true" />
          </span>
          <h1 className="login__titulo">Barbería</h1>
          <p className="login__subtitulo">Sistema de gestión</p>

          <form onSubmit={handleSubmit} className="login__formulario">
            <Campo etiqueta="Usuario" id="usuario">
              <input
                id="usuario"
                type="text"
                className="ui-campo__control"
                autoComplete="username"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                required
                autoFocus
              />
            </Campo>

            <Campo
              etiqueta="Contraseña"
              id="password"
              error={error || undefined}
            >
              <input
                id="password"
                type="password"
                className="ui-campo__control"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                aria-invalid={error ? 'true' : undefined}
              />
            </Campo>

            <Boton type="submit" cargando={cargando} ancho>
              Ingresar
            </Boton>
          </form>
        </div>
      </div>
    </div>
  )
}
