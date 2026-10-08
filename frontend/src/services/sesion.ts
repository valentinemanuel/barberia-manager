/**
 * Sesión durable por cuenta (paquete 8, T53, RF-33 parcial, RNF-5).
 * Puro e inyectable: el store real es `localStorage`, los tests usan memoria.
 * Sin cifrado en este paquete (aislamiento simplificado aprobado): las filas
 * locales persisten por cuenta (`actorId`) y nunca se leen ni envían como
 * de otra; el cambio de cuenta invalida la generación para que respuestas
 * tardías no toquen datos de la cuenta nueva.
 */

export interface SesionCuenta {
  titularId: number | null;
  generacion: number;
  ultimoRol: string | null;
  actualizadoEn: string;
}

export interface AlmacenSesion {
  get: (clave: string) => string | null;
  set: (clave: string, valor: string) => void;
  del: (clave: string) => void;
}

const CLAVE = 'sesion-activa-cuenta';

function leer(store: AlmacenSesion): SesionCuenta {
  const raw = store.get(CLAVE);
  if (!raw) {
    return { titularId: null, generacion: 0, ultimoRol: null, actualizadoEn: '' };
  }
  try {
    const datos = JSON.parse(raw) as Partial<SesionCuenta>;
    return {
      titularId: typeof datos.titularId === 'number' ? datos.titularId : null,
      generacion: typeof datos.generacion === 'number' ? datos.generacion : 0,
      ultimoRol: typeof datos.ultimoRol === 'string' ? datos.ultimoRol : null,
      actualizadoEn: typeof datos.actualizadoEn === 'string' ? datos.actualizadoEn : '',
    };
  } catch {
    return { titularId: null, generacion: 0, ultimoRol: null, actualizadoEn: '' };
  }
}

function guardar(store: AlmacenSesion, sesion: SesionCuenta): SesionCuenta {
  store.set(CLAVE, JSON.stringify(sesion));
  return sesion;
}

/**
 * Instala la sesión del titular. Mismo titular reconectado conserva su
 * generación (sus pendientes siguen vigentes); titular distinto la sube
 * (los pendientes del anterior dejan de ser enviables/aplicables).
 */
export function instalarSesion(
  store: AlmacenSesion,
  titularId: number,
  rol: string,
  ahora: Date = new Date(),
): SesionCuenta {
  const previa = leer(store);
  const generacion =
    previa.titularId === titularId ? previa.generacion : previa.generacion + 1;
  return guardar(store, {
    titularId,
    generacion,
    ultimoRol: rol,
    actualizadoEn: ahora.toISOString(),
  });
}

/**
 * Cierra la sesión durable: sube la generación y deja sin titular.
 * Las filas locales persisten por cuenta (sin borrado), pero ninguna
 * respuesta en vuelo con generación anterior puede aplicarse después.
 */
export function invalidarSesion(
  store: AlmacenSesion,
  ahora: Date = new Date(),
): SesionCuenta {
  const previa = leer(store);
  return guardar(store, {
    titularId: null,
    generacion: previa.generacion + 1,
    ultimoRol: previa.ultimoRol,
    actualizadoEn: ahora.toISOString(),
  });
}

/** Una respuesta solo puede aplicarse si titular y generación coinciden. */
export function esRespuestaVigente(
  capturada: { titularId: number | null; generacion: number },
  actual: { titularId: number | null; generacion: number },
): boolean {
  return (
    capturada.titularId !== null &&
    capturada.titularId === actual.titularId &&
    capturada.generacion === actual.generacion
  );
}

/** Regla de alcance: la fila local solo pertenece a su actor. */
export function perteneceALaCuenta(actorFila: number, titularId: number | null): boolean {
  return titularId !== null && actorFila === titularId;
}

/** Lee la sesión durable del navegador (fuera de tests). */
export function leerSesionNavegador(): SesionCuenta {
  try {
    return leer({
      get: (k) => localStorage.getItem(k),
      set: (k, v) => localStorage.setItem(k, v),
      del: (k) => localStorage.removeItem(k),
    });
  } catch {
    return { titularId: null, generacion: 0, ultimoRol: null, actualizadoEn: '' };
  }
}
