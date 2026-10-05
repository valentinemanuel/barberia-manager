import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  ReactNode,
} from 'react'
import { CheckCircle2, Info, XCircle, X } from 'lucide-react'

type TipoToast = 'exito' | 'error' | 'info'

interface Toast {
  id: number
  tipo: TipoToast
  mensaje: string
}

interface ContextoToast {
  mostrar: (tipo: TipoToast, mensaje: string) => void
}

const Contexto = createContext<ContextoToast | null>(null)

const ICONOS: Record<TipoToast, typeof Info> = {
  exito: CheckCircle2,
  error: XCircle,
  info: Info,
}

/**
 * Proveedor de toasts. Debe montarse una sola vez, dentro del Layout.
 * Uso: const { mostrar } = useToast(); mostrar('exito', 'Corte registrado')
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const contador = useRef(0)

  const cerrar = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const mostrar = useCallback(
    (tipo: TipoToast, mensaje: string) => {
      contador.current += 1
      const id = contador.current
      setToasts((prev) => [...prev, { id, tipo, mensaje }])
      // El toast se retira solo; la información ya no es nueva después de un rato
      window.setTimeout(() => cerrar(id), 5000)
    },
    [cerrar]
  )

  const valor = useMemo(() => ({ mostrar }), [mostrar])

  return (
    <Contexto.Provider value={valor}>
      {children}
      <div className="ui-toasts" role="status" aria-live="polite">
        {toasts.map((toast) => {
          const Icono = ICONOS[toast.tipo]
          return (
            <div key={toast.id} className={`ui-toast ui-toast--${toast.tipo}`}>
              <Icono className="ui-toast__icono" size={18} aria-hidden="true" />
              <span className="ui-toast__cuerpo">{toast.mensaje}</span>
              <button
                type="button"
                className="ui-toast__cerrar"
                onClick={() => cerrar(toast.id)}
                aria-label="Cerrar aviso"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
          )
        })}
      </div>
    </Contexto.Provider>
  )
}

export function useToast(): ContextoToast {
  const contexto = useContext(Contexto)
  if (!contexto) {
    throw new Error('useToast debe usarse dentro de ToastProvider')
  }
  return contexto
}
