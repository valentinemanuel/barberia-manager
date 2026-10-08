import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Scissors,
  Receipt,
  Users,
  ClipboardList,
  Package,
  BarChart3,
  Wallet,
  LogOut,
  WifiOff,
  RefreshCw,
  MoreHorizontal,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { useSync } from '../hooks/useSync'
import { ToastProvider, Modal } from './ui'

/** Pestañas visibles en la barra inferior; el resto va en la hoja "Más". */
const MAX_TABS_MOVIL = 3

interface LayoutProps {
  children: ReactNode
}

interface Enlace {
  ruta: string
  nombre: string
  icono: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { usuario, logout } = useAuthStore()
  const location = useLocation()
  const [menuMovilAbierto, setMenuMovilAbierto] = useState(false)

  const enlaces: Enlace[] = useMemo(() => {
    const base: Enlace[] = [
      { ruta: '/', nombre: 'Inicio', icono: <LayoutDashboard size={18} /> },
      { ruta: '/cortes', nombre: 'Cortes', icono: <Scissors size={18} /> },
      { ruta: '/saldos', nombre: 'Saldos', icono: <Receipt size={18} /> },
    ]

    if (usuario?.rol === 'admin') {
      base.push(
        { ruta: '/usuarios', nombre: 'Usuarios', icono: <Users size={18} /> },
        { ruta: '/servicios', nombre: 'Servicios', icono: <ClipboardList size={18} /> },
        { ruta: '/productos', nombre: 'Productos', icono: <Package size={18} /> },
        { ruta: '/reportes', nombre: 'Reportes', icono: <BarChart3 size={18} /> },
        { ruta: '/cierre-caja', nombre: 'Cierre de caja', icono: <Wallet size={18} /> }
      )
    }

    return base
  }, [usuario?.rol])

  // En pantallas angostas la barra inferior solo admite un puñado de pestañas;
  // el resto (incluida la ruta activa actual) vive en la hoja "Más".
  const tabsVisibles = enlaces.slice(0, MAX_TABS_MOVIL)
  const restantes = enlaces.slice(MAX_TABS_MOVIL)

  // Si la ruta activa quedó fuera de las pestañas visibles, "Más" se resalta
  // para que el usuario sepa dónde está parado.
  const hayActivaEnRestantes = restantes.some((enlace) =>
    enlace.ruta === '/'
      ? location.pathname === '/'
      : location.pathname.startsWith(enlace.ruta)
  )

  return (
    <ToastProvider>
      <div className="shell">
        <header className="shell__topbar">
          <span className="shell__marca">
            <span className="shell__franja" aria-hidden="true" />
            Barbería
          </span>

          <div className="shell__topbar-derecha">
            <IndicadorConexion />
            <span className="shell__usuario">
              <span className="shell__usuario-nombre">
                {usuario?.nombre} {usuario?.apellido}
              </span>
              <span className="shell__usuario-rol">{usuario?.rol}</span>
            </span>
            <button
              type="button"
              onClick={logout}
              className="ui-boton ui-boton--fantasma ui-boton--peq"
              style={{ color: 'var(--shell-texto)' }}
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
            >
              <LogOut size={16} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="shell__cuerpo">
          <nav className="shell__rail" aria-label="Navegación principal">
            {enlaces.map((enlace) => (
              <NavLink
                key={enlace.ruta}
                to={enlace.ruta}
                end={enlace.ruta === '/'}
                className="shell__rail-enlace"
              >
                {enlace.icono}
                {enlace.nombre}
              </NavLink>
            ))}
          </nav>

          <main className="shell__contenido">
            <div key={location.pathname} className="animar-pagina">
              {children}
            </div>
          </main>
        </div>

        <nav className="shell__tabbar" aria-label="Navegación principal">
          {tabsVisibles.map((enlace) => (
            <NavLink
              key={enlace.ruta}
              to={enlace.ruta}
              end={enlace.ruta === '/'}
              className="shell__tab"
            >
              {enlace.icono}
              {enlace.nombre}
            </NavLink>
          ))}

          {restantes.length > 0 && (
            <button
              type="button"
              className={`shell__tab ${
                hayActivaEnRestantes ? 'shell__tab--activo' : ''
              }`.trim()}
              onClick={() => setMenuMovilAbierto(true)}
              aria-haspopup="dialog"
              aria-expanded={menuMovilAbierto}
            >
              <MoreHorizontal size={18} aria-hidden="true" />
              Más
            </button>
          )}
        </nav>

        {/* Hoja con las rutas que no caben en la barra inferior */}
        <Modal
          abierto={menuMovilAbierto}
          onCerrar={() => setMenuMovilAbierto(false)}
          titulo="Más secciones"
        >
          <div className="shell__menu-movil">
            {restantes.map((enlace) => (
              <NavLink
                key={enlace.ruta}
                to={enlace.ruta}
                end={enlace.ruta === '/'}
                className="shell__rail-enlace"
                onClick={() => setMenuMovilAbierto(false)}
              >
                {enlace.icono}
                {enlace.nombre}
              </NavLink>
            ))}
          </div>
        </Modal>
      </div>
    </ToastProvider>
  )
}

/**
 * Píldora de conexión en la topbar: informa offline y sincronización.
 * No aparece nada cuando todo está en orden.
 */
function IndicadorConexion() {
  const online = useOnlineStatus()
  const { sincronizando, ultimaSync } = useSync()

  if (online && !sincronizando) return null

  if (sincronizando) {
    return (
      <span className="shell__conexion shell__conexion--sincronizando">
        <RefreshCw size={13} className="shell__conexion-gira" aria-hidden="true" />
        Sincronizando
        {ultimaSync && (
          <span className="ui-sr-oculto">
            , última sincronización {ultimaSync.toLocaleTimeString('es-ES')}
          </span>
        )}
      </span>
    )
  }

  return (
    <span className="shell__conexion shell__conexion--offline">
      <WifiOff size={13} aria-hidden="true" />
      Sin conexión
    </span>
  )
}
