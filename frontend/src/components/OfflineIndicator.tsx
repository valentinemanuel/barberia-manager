import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { useSync } from '../hooks/useSync'

export default function OfflineIndicator() {
  const online = useOnlineStatus()
  const { sincronizando, ultimaSync } = useSync()

  if (online && !sincronizando) return null

  return (
    <div className={`fixed bottom-4 right-4 p-3 rounded-lg shadow-lg text-white text-sm ${
      online ? 'bg-blue-500' : 'bg-orange-500'
    }`>
      {sincronizando ? (
        <span>🔄 Sincronizando...</span>
      ) : !online ? (
        <span>📴 Sin conexión - Modo offline</span>
      ) : null}
      {ultimaSync && (
        <p className="text-xs opacity-80 mt-1">
          Última sync: {ultimaSync.toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
