/**
 * T54 (paquete 8): operación de abono encadenada al corte (dependeDe).
 * Reutiliza el harness de compilación de T50; agrega asserts de abono.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'operacionesCortes.ts');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't54-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'operacionesCortes.js')).href);
const assert = (await import('node:assert/strict')).default;

if (typeof modulo.crearOperacionAbono !== 'function') {
  console.error('ROJO T54: falta crearOperacionAbono en operacionesCortes.ts');
  process.exit(1);
}
// Abono válido encadenado al corte: conserva importe y referencia.
const ahora = new Date('2026-10-07T10:00:00.000Z');
const abono = modulo.crearOperacionAbono({
  actorId: 7,
  corteUuid: 'corte-uuid-1',
  concepto: 'cliente',
  importeCentavos: 5000,
  modoCaptura: 'offline',
  ahora,
});
assert.match(abono.operacionUuid, /^[0-9a-f-]{36}$/i);
assert.equal(abono.dependeDe, 'corte-uuid-1');
assert.equal(abono.importeCentavos, 5000);
assert.equal(abono.instanteCambioUtc, '2026-10-07T10:00:00.000Z');
assert.equal(abono.estado, 'pendiente');
// Concepto inválido e importe cero se rechazan sin crear nada.
assert.throws(
  () => modulo.crearOperacionAbono({
    actorId: 7, corteUuid: 'x', concepto: 'otro', importeCentavos: 100,
    modoCaptura: 'offline', ahora,
  }),
  /concepto/,
);
assert.throws(
  () => modulo.crearOperacionAbono({
    actorId: 7, corteUuid: 'x', concepto: 'cliente', importeCentavos: 0,
    modoCaptura: 'offline', ahora,
  }),
  /centavos/,
);

console.log('VERDE T54: operación de abono encadenada en verde (dependeDe + importe real)');
