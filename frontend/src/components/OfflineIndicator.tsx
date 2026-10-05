import { WifiOff, RefreshCw } from 'lucide-react'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { useSync } from '../hooks/useSync'

/**
 * Píldora de estado de conexión.
 * Nota: el Layout ya muestra este estado en la topbar; este componente
 * queda disponible para pantallas que quieran mostrarlo en otro lugar.
 */
export default function OfflineIndicator() {
  const online = useOnlineStatus()
  const { sincronizando, ultimaSync } = useSync()

  if (online && !sincronizando) return null

  return (
    <div
      className={`shell__conexion ${
        sincronizando ? 'shell__conexion--sincronizando' : 'shell__conexion--offline'
      }`}
      role="status"
    >
      {sincronizando ? (
        <>
          <RefreshCw size={13} className="shell__conexion-gira" aria-hidden="true" />
          Sincronizando…
        </>
      ) : (
        <>
          <WifiOff size={13} aria-hidden="true" />
          Sin conexión — guardando en el dispositivo
        </>
      )}
      {ultimaSync && (
        <span className="ui-sr-oculto">
          Última sincronización {ultimaSync.toLocaleTimeString('es-ES')}
        </span>
      )}
    </div>
  )
}
