import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    // Los Decimal de Pydantic llegan como strings ("12.50"); convertirlos a
    // número para que .toFixed() funcione y React no truene (pantalla en blanco)
    if (response.data && typeof response.data === 'object') {
      response.data = convertirDecimales(response.data)
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/'
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
