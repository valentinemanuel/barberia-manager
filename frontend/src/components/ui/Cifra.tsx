import { ReactNode } from 'react'

interface CifraProps {
  etiqueta: string
  valor: ReactNode
  pie?: ReactNode
  /** Destacada usa el tamaño grande; media el de sección */
  destacada?: boolean
  className?: string
}

/**
 * Dato numérico con etiqueta. El valor siempre en cifras tabulares
 * para que las columnas de dinero se alineen.
 */
export default function Cifra({
  etiqueta,
  valor,
  pie,
  destacada = false,
  className = '',
}: CifraProps) {
  return (
    <div className={`ui-cifra ${className}`.trim()}>
      <span className="ui-cifra__etiqueta">{etiqueta}</span>
      <span className={`ui-cifra__valor ${destacada ? '' : 'ui-cifra__valor--medio'}`.trim()}>
        {valor}
      </span>
      {pie && <span className="ui-cifra__pie">{pie}</span>}
    </div>
  )
}
