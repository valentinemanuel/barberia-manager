import { ReactNode, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { usuario, logout } = useAuthStore()
  const location = useLocation()
  const [menuAbierto, setMenuAbierto] = useState(false)

  const enlaces = [
    { ruta: '/', nombre: 'Dashboard', icono: '📊' },
    { ruta: '/cortes', nombre: 'Cortes', icono: '✂️' },
  ]

  if (usuario?.rol === 'admin') {
    enlaces.push(
      { ruta: '/usuarios', nombre: 'Usuarios', icono: '👥' },
      { ruta: '/servicios', nombre: 'Servicios', icono: '📋' },
      { ruta: '/productos', nombre: 'Productos', icono: '📦' },
      { ruta: '/reportes', nombre: 'Reportes', icono: '📈' },
      { ruta: '/cierre-caja', nombre: 'Cierre de Caja', icono: '💰' },
    )
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      {/* Header */}
      <header className="bg-[var(--color-primary)] text-white p-4 shadow-lg">
        <div className="container flex flex-between flex-center">
          <h1 className="text-xl font-bold">Barbería</h1>
          <div className="flex flex-center gap-2">
            <span className="text-sm opacity-80">
              {usuario?.nombre} {usuario?.apellido}
            </span>
            <button
              onClick={logout}
              className="btn btn-danger text-sm py-1 px-3"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      {/* Navegación móvil */}
      <nav className="bg-[var(--color-secondary)] p-2 md:hidden">
        <button
          onClick={() => setMenuAbierto(!menuAbierto)}
          className="btn btn-secondary w-full"
        >
          {menuAbierto ? '✕ Cerrar' : '☰ Menú'}
        </button>
        {menuAbierto && (
          <div className="mt-2 grid gap-1">
            {enlaces.map((enlace) => (
              <Link
                key={enlace.ruta}
                to={enlace.ruta}
                className={`p-3 rounded-lg text-white ${
                  location.pathname === enlace.ruta
                    ? 'bg-[var(--color-highlight)]'
                    : 'bg-[var(--color-accent)]'
                }`}
                onClick={() => setMenuAbierto(false)}
              >
                {enlace.icono} {enlace.nombre}
              </Link>
            ))}
          </div>
        )}
      </nav>

      {/* Navegación desktop */}
      <nav className="bg-[var(--color-secondary)] p-2 hidden md:block">
        <div className="container flex gap-2">
          {enlaces.map((enlace) => (
            <Link
              key={enlace.ruta}
              to={enlace.ruta}
              className={`px-4 py-2 rounded-lg text-white transition-colors ${
                location.pathname === enlace.ruta
                  ? 'bg-[var(--color-highlight)]'
                  : 'bg-[var(--color-accent)] hover:bg-[var(--color-highlight)]'
              }`}
            >
              {enlace.icono} {enlace.nombre}
            </Link>
          ))}
        </div>
      </nav>

      {/* Contenido */}
      <main className="container py-4">
        {children}
      </main>
    </div>
  )
}
