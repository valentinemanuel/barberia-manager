interface SkeletonProps {
  /** Alto en rem del bloque simulado */
  alto?: string
  ancho?: string
}

/**
 * Bloque de carga con pulso. Usa `animar-skeleton` para que
 * prefers-reduced-motion lo deje estático.
 */
export default function Skeleton({ alto = '1rem', ancho = '100%' }: SkeletonProps) {
  return (
    <div
      className="ui-skeleton"
      style={{ height: alto, width: ancho }}
      aria-hidden="true"
    />
  )
}

/** Grupo apilado de líneas, típico para listas que cargan. */
export function SkeletonLineas({ cantidad = 3 }: { cantidad?: number }) {
  return (
    <div className="ui-skeleton-grupo" aria-hidden="true">
      {Array.from({ length: cantidad }).map((_, i) => (
        <Skeleton key={i} ancho={i === cantidad - 1 ? '60%' : '100%'} />
      ))}
    </div>
  )
}
