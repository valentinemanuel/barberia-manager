import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const { token, usuario } = useAuthStore.getState()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Foto por solicitud (T53, RF-33): un 401 tardío de la cuenta anterior
  // no puede cerrar la sesión de la cuenta nueva.
  const foto = { token, titularId: usuario?.id ?? null }
  ;(config as unknown as { __sesionFoto?: typeof foto }).__sesionFoto = foto
  return config
})

api.interceptors.response.use(
  (response) => {
    // Camino exacto 002 (paquete 12, T83): con `X-Exacto` se omiten las
    // conversiones y los decimales viajan como strings ("12.50" intacto).
    if (response.config?.headers?.['X-Exacto']) {
      return response
    }
    // Los Decimal de Pydantic llegan como strings ("12.50"); convertirlos a
    // número para que .toFixed() funcione y React no truene (pantalla en blanco)
    if (response.data && typeof response.data === 'object') {
      response.data = convertirDecimales(response.data)
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      const foto = (error.config as unknown as { __sesionFoto?: { token: string | null } })
        ?.__sesionFoto
      const actual = useAuthStore.getState()
      // Solo desloguea si el token rechazado sigue siendo el vigente.
      if (foto && foto.token === actual.token) {
        actual.logout()
        window.location.href = '/'
      }
    }
    return Promise.reject(error)
  }
)

function convertirDecimales(valor: unknown): unknown {
  if (typeof valor === 'string') {
    return /^-?\d+(\.\d+)?$/.test(valor) ? Number(valor) : valor
  }
  if (Array.isArray(valor)) {
    return valor.map(convertirDecimales)
  }
  if (typeof valor === 'object' && valor !== null) {
    return Object.fromEntries(
      Object.entries(valor).map(([clave, v]) => [clave, convertirDecimales(v)])
    )
  }
  return valor
}

export default api
