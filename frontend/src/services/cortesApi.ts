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
