/**
 * T53 (paquete 8): sesión durable por cuenta (titular + generación).
 * Compila solo `sesion.ts` y prueba con store en memoria. Sin DOM ni red.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'sesion.ts');
if (!fs.existsSync(fuente)) {
  console.error('ROJO T53: falta src/services/sesion.ts');
  process.exit(1);
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't53-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'sesion.js')).href);
const assert = (await import('node:assert/strict')).default;

function memoria() {
  const mapa = new Map();
  return {
    get: (k) => (mapa.has(k) ? mapa.get(k) : null),
    set: (k, v) => mapa.set(k, v),
    del: (k) => mapa.delete(k),
  };
}

// Instalar A → generación 1; reinstalar A conserva; cambiar a B sube.
const store = memoria();
let sesion = modulo.instalarSesion(store, 7, 'barbero');
assert.equal(sesion.titularId, 7);
assert.equal(sesion.generacion, 1);
sesion = modulo.instalarSesion(store, 7, 'barbero');
assert.equal(sesion.generacion, 1);
sesion = modulo.instalarSesion(store, 9, 'barbero');
assert.equal(sesion.titularId, 9);
assert.equal(sesion.generacion, 2);
// Respuesta capturada con generación vieja ya no es vigente.
assert.equal(
  modulo.esRespuestaVigente({ titularId: 7, generacion: 1 }, { titularId: 9, generacion: 2 }),
  false,
);
assert.equal(
  modulo.esRespuestaVigente({ titularId: 9, generacion: 2 }, { titularId: 9, generacion: 2 }),
  true,
);
// Invalidar sube generación y deja sin titular: nada pendiente es vigente.
sesion = modulo.invalidarSesion(store);
assert.equal(sesion.titularId, null);
assert.equal(sesion.generacion, 3);
assert.equal(
  modulo.esRespuestaVigente({ titularId: 9, generacion: 2 }, sesion),
  false,
);
// Regla de alcance: la fila solo pertenece a su actor.
assert.equal(modulo.perteneceALaCuenta(7, 7), true);
assert.equal(modulo.perteneceALaCuenta(7, 9), false);

console.log('VERDE T53: sesión por cuenta en verde (generación + vigencia + alcance)');
