import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { instalarSesion, invalidarSesion } from '../services/sesion'

const almacenSesion = {
  get: (clave: string) => {
    try {
      return localStorage.getItem(clave)
    } catch {
      return null
    }
  },
  set: (clave: string, valor: string) => {
    try {
      localStorage.setItem(clave, valor)
    } catch {
      // Sin almacenamiento durable no se confirma aislamiento; la app
      // sigue, pero la sesión no sobrevive a recarga (limitación visible).
    }
  },
  del: (clave: string) => {
    try {
      localStorage.removeItem(clave)
    } catch {
      // Sin efecto.
    }
  },
}

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
      setAuth: (token, usuario) => {
        // La cuenta propietaria de lo local es el actor (T53, RF-33).
        instalarSesion(almacenSesion, usuario.id, usuario.rol)
        set({ token, usuario })
      },
      logout: () => {
        // Invalida la generación: respuestas tardías en vuelo no pueden
        // aplicarse a la cuenta siguiente. Las filas locales persisten
        // por cuenta (sin borrado), nunca visibles como de otra.
        invalidarSesion(almacenSesion)
        set({ token: null, usuario: null })
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)
