import { ReactNode, useEffect, useRef, useCallback } from 'react'
import { X } from 'lucide-react'
import Boton from './Boton'

interface ModalProps {
  abierto: boolean
  onCerrar: () => void
  titulo: string
  children: ReactNode
  /** Botón de confirmación del pie (opcional) */
  onConfirmar?: () => void
  textoConfirmar?: string
  cargando?: boolean
  /** Deshabilita el confirmar (p. ej. formulario incompleto) */
  confirmarDeshabilitado?: boolean
}

/**
 * Diálogo modal con cierre por Escape y overlay clickeable.
 * El foco se mueve al modal al abrirse y vuelve al disparador al cerrarse.
 */
export default function Modal({
  abierto,
  onCerrar,
  titulo,
  children,
  onConfirmar,
  textoConfirmar = 'Guardar',
  cargando = false,
  confirmarDeshabilitado = false,
}: ModalProps) {
  const refModal = useRef<HTMLDivElement>(null)
  const refAnterior = useRef<HTMLElement | null>(null)
  // Recuerda si el modal ya estaba abierto: el foco solo se mueve
  // en las transiciones abrir/cerrar, nunca en re-renderizados
  // (p. ej. al escribir en un input del formulario).
  const refEstabaAbierto = useRef(false)

  const cerrar = useCallback(() => {
    if (!cargando) onCerrar()
  }, [cargando, onCerrar])

  useEffect(() => {
    if (abierto && !refEstabaAbierto.current) {
      refAnterior.current = document.activeElement as HTMLElement | null
      refModal.current?.focus()
    }
    if (!abierto && refEstabaAbierto.current) {
      refAnterior.current?.focus()
    }
    refEstabaAbierto.current = abierto
  }, [abierto])

  useEffect(() => {
    if (!abierto) return

    const alPresionar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') cerrar()
    }
    document.addEventListener('keydown', alPresionar)
    return () => {
      document.removeEventListener('keydown', alPresionar)
    }
  }, [abierto, cerrar])

  if (!abierto) return null

  return (
    <div
      className="ui-modal-overlay"
      onClick={(evento) => {
        if (evento.target === evento.currentTarget) cerrar()
      }}
    >
      <div
        className="ui-modal"
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        tabIndex={-1}
        ref={refModal}
      >
        <header className="ui-modal__cabecera">
          <h2 className="ui-modal__titulo">{titulo}</h2>
          <button
            type="button"
            className="ui-modal__cierre"
            onClick={cerrar}
            aria-label="Cerrar"
            disabled={cargando}
          >
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        {children}

        {onConfirmar && (
          <footer className="ui-modal__pie">
            <Boton
              variante="secundario"
              onClick={cerrar}
              disabled={cargando}
            >
              Cancelar
            </Boton>
            <Boton
              variante="primario"
              onClick={onConfirmar}
              cargando={cargando}
              disabled={confirmarDeshabilitado}
            >
              {textoConfirmar}
            </Boton>
          </footer>
        )}
      </div>
    </div>
  )
}
