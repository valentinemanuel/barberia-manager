import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface ProtectedRouteProps {
  children: ReactNode
  rol?: 'admin' | 'barbero'
}

export default function ProtectedRoute({ children, rol }: ProtectedRouteProps) {
  const { usuario, token } = useAuthStore()

  if (!token || !usuario) {
    return <Navigate to="/" replace />
  }

  if (rol && usuario.rol !== rol) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
