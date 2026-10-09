/**
 * Cliente typed 002 (paquete 12, T82, RNF-1): strings exactos del API.
 * A diferencia de `api.ts` (conversor global a `Number`), aquí los
 * decimales viajan como strings ("12.50" nunca se vuelve 12.5) y el
 * dinero se opera en centavos enteros. `api.ts` queda intacto.
 */
import {
  centavosAPesosStr,
  pesosStrACentavos,
} from './operacionesCortes';

export { centavosAPesosStr, pesosStrACentavos };

export type HttpTexto = (url: string, cuerpo?: unknown) => Promise<{ data: string }>;

/** Revive JSON sin convertir strings numéricos (identidad exacta). */
export function parseoExacto(texto: string): unknown {
  return JSON.parse(texto);
}

export interface CortesApi {
  get<T = unknown>(url: string): Promise<T>;
  post<T = unknown>(url: string, cuerpo?: unknown): Promise<T>;
  patch<T = unknown>(url: string, cuerpo?: unknown): Promise<T>;
}

/** Cliente 002 con http inyectado (tests usan falso, prod usa fetch/axios). */
export function crearCortesApi(http: {
  get: HttpTexto;
  post: HttpTexto;
  patch: HttpTexto;
}): CortesApi {
  const envolver =
    (llamar: HttpTexto) =>
    async <T = unknown>(url: string, cuerpo?: unknown): Promise<T> => {
      const respuesta = await llamar(url, cuerpo);
      return parseoExacto(
        typeof respuesta.data === 'string' ? respuesta.data : JSON.stringify(respuesta.data),
      ) as T;
    };
  return {
    get: (url) => envolver(http.get)(url),
    post: (url, cuerpo) => envolver(http.post)(url, cuerpo),
    patch: (url, cuerpo) => envolver(http.patch)(url, cuerpo),
  };
}

/**
 * Porcentaje (0–100, ≤2 decimales) a centésimas de punto (T83).
 * El JSON ya trae el double más cercano; para este rango acotado
 * `Math.round(x*100)` es exacto (error binario ~1e-12 « 0.5) y valida
 * rango. Falla en voz alta fuera de 0–100, nunca normaliza en silencio.
 */
export function porcentajeACentesimas(porcentaje: number): number {
  if (typeof porcentaje !== 'number' || !Number.isFinite(porcentaje)) {
    throw new Error('El porcentaje debe ser un número finito');
  }
  if (porcentaje < 0 || porcentaje > 100) {
    throw new Error('El porcentaje debe estar entre 0 y 100');
  }
  return Math.round(porcentaje * 100);
}

/**
 * Centavos desde un número de catálogo local (T83): `String(n)` da la
 * representación más corta que redondea al mismo double, exacta para
 * precios con ≤2 decimales; si no parsea, falla en voz alta.
 */
export function numeroCatalogoACentavos(valor: number): number {
  return pesosStrACentavos(String(valor));
}

const CRUDO = {
  // Reemplaza el transform por defecto: la respuesta llega como texto y
  // `X-Exacto` salta además el conversor global de `api.ts`.
  transformResponse: [(datos: string) => datos],
  headers: { 'X-Exacto': '1' },
};

/** Instancia lista contra `/api` con strings exactos (pantallas 002). */
export function crearCortesApiAxios(instancia: unknown): CortesApi {
  const ax = instancia as {
    get: (url: string, config?: Record<string, unknown>) => Promise<{ data: unknown }>;
    post: (url: string, cuerpo?: unknown, config?: Record<string, unknown>) => Promise<{ data: unknown }>;
    patch: (url: string, cuerpo?: unknown, config?: Record<string, unknown>) => Promise<{ data: unknown }>;
  };
  const texto = (valor: unknown): string =>
    typeof valor === 'string' ? valor : JSON.stringify(valor);
  return crearCortesApi({
    get: (url) => ax.get(url, CRUDO).then((r) => ({ data: texto(r.data) })),
    post: (url, cuerpo) => ax.post(url, cuerpo, CRUDO).then((r) => ({ data: texto(r.data) })),
    patch: (url, cuerpo) => ax.patch(url, cuerpo, CRUDO).then((r) => ({ data: texto(r.data) })),
  });
}
