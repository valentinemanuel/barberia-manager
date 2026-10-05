import { ReactNode } from 'react'

interface TablaProps {
  /** Encabezados de columna */
  columnas: string[]
  children: ReactNode
}

/**
 * Tabla con envoltorio con scroll horizontal propio.
 * Las filas y celdas se pintan con las clases `ui-tabla`.
 */
export default function Tabla({ columnas, children }: TablaProps) {
  return (
    <div className="ui-tabla-envoltorio">
      <table className="ui-tabla">
        <thead>
          <tr>
            {columnas.map((columna) => (
              <th key={columna} scope="col">
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}
