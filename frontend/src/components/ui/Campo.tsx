import { ReactNode } from 'react'

interface CampoProps {
  etiqueta: string
  /** Identificador para vincular label y control */
  id: string
  error?: string
  pista?: string
  children: ReactNode
}

/**
 * Envoltorio de campo de formulario: etiqueta, control y mensajes.
 * El control hijo (input/select) recibe aria-invalid si hay error.
 */
export default function Campo({ etiqueta, id, error, pista, children }: CampoProps) {
  return (
    <div className="ui-campo">
      <label className="ui-campo__etiqueta" htmlFor={id}>
        {etiqueta}
      </label>
      {children}
      {error && (
        <span className="ui-campo__error" role="alert">
          {error}
        </span>
      )}
      {!error && pista && <span className="ui-campo__pista">{pista}</span>}
    </div>
  )
}
