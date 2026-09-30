import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'

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
      const formData = new FormData()
      formData.append('username', usuario)
      formData.append('password', password)

      const response = await api.post('/auth/login', formData)
      const { access_token } = response.data

      // Obtener perfil del usuario
      const perfilResponse = await api.get('/usuarios/me/perfil', {
        headers: { Authorization: `Bearer ${access_token}` }
      })

      setAuth(access_token, perfilResponse.data)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-primary)] p-4">
      <div className="card w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-2">Barbería</h1>
        <p className="text-center text-[var(--color-text-muted)] mb-6">
          Sistema de Gestión
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="label">Usuario</label>
            <input
              type="text"
              className="input"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="mb-6">
            <label className="label">Contraseña</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary w-full"
            disabled={cargando}
          >
            {cargando ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  )
}
