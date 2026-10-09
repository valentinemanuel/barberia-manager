/**
 * T82 (paquete 12): cliente typed 002 — strings exactos sin Number() global.
 * Sin DOM ni red (inyecta un http falso).
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'cortesApi.ts');
if (!fs.existsSync(fuente)) {
  console.error('ROJO T82: falta src/services/cortesApi.ts');
  process.exit(1);
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't82-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module esnext --target es2022 --moduleResolution bundler --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
// Node ESM exige extensión explícita: la agrega el harness (la app usa bundler).
const emitido = path.join(tmp, 'cortesApi.js');
fs.writeFileSync(
  emitido,
  fs.readFileSync(emitido, 'utf8').replace("'./operacionesCortes'", "'./operacionesCortes.js'"),
);
const modulo = await import(pathToFileURL(path.join(tmp, 'cortesApi.js')).href);
const assert = (await import('node:assert/strict')).default;

// El parseo conserva strings ("12.50" no se vuelve 12.5).
const http = async () => ({ data: '{"precio":"12.50","id":7}' });
const get = modulo.crearCortesApi({ get: http, post: http, patch: http }).get;
const resp = await get('/x');
assert.equal(resp.precio, '12.50');
assert.equal(resp.id, 7);
// Codec exacto en ambos sentidos (reexportado, una sola fuente).
assert.equal(modulo.pesosStrACentavos('12.50'), 1250);
assert.equal(modulo.centavosAPesosStr(1250), '12.50');
assert.throws(() => modulo.pesosStrACentavos('12.505'), /decimales/);
// Sin Number()/parseFloat en el módulo (usos reales, no comentarios).
const codigo = fs.readFileSync(fuente, 'utf8');
const sinComentarios = codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
assert.ok(!sinComentarios.includes('parseFloat('), 'sin parseFloat');
const numberUsos = [...sinComentarios.matchAll(/Number\(([^)]*)\)/g)].map((m) => m[1].trim());
for (const uso of numberUsos) {
  assert.ok(uso === 'resultado' || uso.startsWith('resultado '), `Number() no tipado: Number(${uso})`);
}

console.log('VERDE T82: cliente typed en verde (strings exactos + codec)');
