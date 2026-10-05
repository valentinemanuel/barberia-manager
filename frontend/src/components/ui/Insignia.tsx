import { ReactNode } from 'react'

type Tono = 'neutra' | 'exito' | 'alerta' | 'peligro' | 'info' | 'laton'

interface InsigniaProps {
  tono?: Tono
  children: ReactNode
}

/**
 * Insignia para estados cortos: rol, estado del usuario, stock, método de pago.
 */
export default function Insignia({ tono = 'neutra', children }: InsigniaProps) {
  return <span className={`ui-insignia ui-insignia--${tono}`}>{children}</span>
}
