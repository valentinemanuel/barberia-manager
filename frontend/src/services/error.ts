/**
 * Extrae un mensaje legible de un error de axios.
 * El `detail` de FastAPI puede ser string o array de objetos (422),
 * y React no puede renderizar objetos: eso causaba pantalla en blanco.
 */
export function mensajeError(err: unknown, fallback: string): string {
  const detalle = (err as any)?.response?.data?.detail

  if (typeof detalle === 'string') {
    return detalle
  }

  if (Array.isArray(detalle)) {
    const mensajes = detalle
      .map((item: any) => (typeof item?.msg === 'string' ? item.msg : null))
      .filter(Boolean)
    if (mensajes.length > 0) {
      return mensajes.join('. ')
    }
  }

  return fallback
}
