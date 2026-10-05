import { ReactNode } from 'react'

interface VacioProps {
  /** Icono de lucide-react a renderizar */
  icono?: ReactNode
  titulo: string
  texto: string
  /** Acción sugerida (normalmente un <Boton>) */
  accion?: ReactNode
}

/**
 * Estado vacío con dirección: dice qué pasó y qué hacer.
 * Nunca "Sin datos" a secas.
 */
export default function Vacio({ icono, titulo, texto, accion }: VacioProps) {
  return (
    <div className="ui-vacio">
      {icono && <div className="ui-vacio__icono">{icono}</div>}
      <p className="ui-vacio__titulo">{titulo}</p>
      <p className="ui-vacio__texto">{texto}</p>
      {accion}
    </div>
  )
}
