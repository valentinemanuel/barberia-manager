import { ButtonHTMLAttributes, ReactNode } from 'react'

type Variante = 'primario' | 'secundario' | 'exito' | 'peligro' | 'fantasma'
type Tamano = 'normal' | 'peq'

interface BotonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante
  tamano?: Tamano
  ancho?: boolean
  cargando?: boolean
  children: ReactNode
}

/**
 * Botón base del sistema. Maneja los estados de foco, hover y carga;
 * el spinner de "cargando" reemplaza a los textos ad-hoc de cada página.
 */
export default function Boton({
  variante = 'primario',
  tamano = 'normal',
  ancho = false,
  cargando = false,
  disabled,
  className = '',
  children,
  ...resto
}: BotonProps) {
  const clases = [
    'ui-boton',
    `ui-boton--${variante}`,
    tamano === 'peq' ? 'ui-boton--peq' : '',
    ancho ? 'ui-boton--ancho' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button
      className={clases}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      {...resto}
    >
      {cargando && <span className="ui-boton__spinner" aria-hidden="true" />}
      {children}
    </button>
  )
}
