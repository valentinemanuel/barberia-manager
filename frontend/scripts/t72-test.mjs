/**
 * T72 (paquete 10): operaciones de edición/anulación offline (UUID +
 * instante único + cambios explícitos). Sin DOM ni red.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'operacionesCortes.ts');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't72-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'operacionesCortes.js')).href);
const assert = (await import('node:assert/strict')).default;

if (typeof modulo.crearOperacionEdicion !== 'function') {
  console.error('ROJO T72: falta crearOperacionEdicion en operacionesCortes.ts');
  process.exit(1);
}
if (typeof modulo.crearOperacionAnulacion !== 'function') {
  console.error('ROJO T72: falta crearOperacionAnulacion en operacionesCortes.ts');
  process.exit(1);
}
const ahora = new Date('2026-10-08T10:00:00.000Z');
const edicion = modulo.crearOperacionEdicion({
  actorId: 7,
  corteUuid: 'corte-uuid-9',
  cambios: { metodo_pago: 'tarjeta' },
  modoCaptura: 'offline',
  ahora,
});
assert.match(edicion.operacionUuid, /^[0-9a-f-]{36}$/i);
assert.equal(edicion.dependeDe, 'corte-uuid-9');
assert.deepEqual(edicion.cambios, { metodo_pago: 'tarjeta' });
assert.equal(edicion.instanteCambioUtc, '2026-10-08T10:00:00.000Z');
assert.equal(edicion.estado, 'pendiente');
// Sin cambios → error, sin crear nada.
assert.throws(
  () => modulo.crearOperacionEdicion({
    actorId: 7, corteUuid: 'x', cambios: {}, modoCaptura: 'offline', ahora,
  }),
  /cambios/,
);
const anulacion = modulo.crearOperacionAnulacion({
  actorId: 7, corteUuid: 'corte-uuid-9', modoCaptura: 'offline', ahora,
});
assert.equal(anulacion.accion, 'anular');
assert.equal(anulacion.dependeDe, 'corte-uuid-9');

console.log('VERDE T72: edición/anulación offline en verde (instante + cambios)');
