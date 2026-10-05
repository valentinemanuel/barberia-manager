import { Component, ReactNode } from 'react'
import { Boton, Tarjeta } from './ui'

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
        <div
          className="login__panel"
          style={{ minHeight: '100vh' }}
        >
          <Tarjeta className="login__caja">
            <h1 style={{ fontSize: 'var(--fs-lg)' }}>Algo salió mal</h1>
            <p className="texto-suave" style={{ margin: 'var(--sp-3) 0 var(--sp-5)' }}>
              La pantalla encontró un error inesperado. Recargar suele resolverlo;
              si vuelve a pasar, avisale al encargado.
            </p>
            <p
              className="texto-pequeno texto-suave"
              style={{ wordBreak: 'break-word', marginBottom: 'var(--sp-4)' }}
            >
              {this.estado.mensaje}
            </p>
            <Boton ancho onClick={() => window.location.reload()}>
              Recargar aplicación
            </Boton>
          </Tarjeta>
        </div>
      )
    }

    return this.props.children
  }
}
