import { ReactNode } from 'react'

interface TarjetaProps {
  children: ReactNode
  /** Encabezado opcional con título y acciones */
  titulo?: ReactNode
  acciones?: ReactNode
  apretada?: boolean
  className?: string
}

/**
 * Superficie base del sistema: papel blanco sobre fondo hueso,
 * borde fino en lugar de sombras pesadas.
 */
export default function Tarjeta({
  children,
  titulo,
  acciones,
  apretada = false,
  className = '',
}: TarjetaProps) {
  const clases = ['ui-tarjeta', apretada ? 'ui-tarjeta--apretada' : '', className]
    .filter(Boolean)
    .join(' ')

  return (
    <section className={clases}>
      {(titulo || acciones) && (
        <header className="ui-tarjeta__cabecera">
          {titulo && <h3 className="ui-tarjeta__titulo">{titulo}</h3>}
          {acciones}
        </header>
      )}
      {children}
    </section>
  )
}
