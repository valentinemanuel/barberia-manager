import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface Estado {
  hayError: boolean
  mensaje: string
}

/**
 * Evita que un error de render deje la pantalla completamente en blanco:
 * muestra el error y un botón para recargar.
 */
export default class ErrorBoundary extends Component<Props, Estado> {
  estado: Estado = { hayError: false, mensaje: '' }

  static getDerivedStateFromError(error: Error): Estado {
    return { hayError: true, mensaje: error.message }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Error capturado por ErrorBoundary:', error, info.componentStack)
  }

  render() {
    if (this.estado.hayError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] p-4">
          <div className="card w-full max-w-md text-center">
            <h2 className="text-xl font-bold mb-2">Algo salió mal 😕</h2>
            <p className="text-[var(--color-text-muted)] mb-4 break-words">
              {this.estado.mensaje}
            </p>
            <button
              className="btn btn-primary w-full"
              onClick={() => window.location.reload()}
            >
              Recargar aplicación
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
