import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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

interface AuthState {
  token: string | null
  usuario: Usuario | null
  setAuth: (token: string, usuario: Usuario) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      usuario: null,
      setAuth: (token, usuario) => set({ token, usuario }),
      logout: () => set({ token: null, usuario: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
)
