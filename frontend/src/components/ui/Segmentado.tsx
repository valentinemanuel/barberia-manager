import { ReactNode } from 'react'

interface Opcion<T> {
  valor: T
  etiqueta: string
  icono?: ReactNode
}

interface SegmentadoProps<T> {
  etiqueta: string
  opciones: Opcion<T>[]
  valor: T
  onCambio: (valor: T) => void
}

/**
 * Selector tipo radio con apariencia de control segmentado.
 * Pensado para métodos de pago y filtros cortos: todo visible, sin dropdown.
 */
export default function Segmentado<T extends string | number>({
  etiqueta,
  opciones,
  valor,
  onCambio,
}: SegmentadoProps<T>) {
  return (
    <div
      className="ui-segmentado"
      role="radiogroup"
      aria-label={etiqueta}
    >
      {opciones.map((opcion) => (
        <button
          key={String(opcion.valor)}
          type="button"
          className="ui-segmentado__opcion"
          role="radio"
          aria-checked={opcion.valor === valor}
          onClick={() => onCambio(opcion.valor)}
        >
          {opcion.icono}
          {opcion.etiqueta}
        </button>
      ))}
    </div>
  )
}
