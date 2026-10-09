/**
 * T80 (paquete 11): aviso de imputación pendiente en la vista del titular.
 * Sin DOM ni red.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'saldosVista.ts');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't80-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'saldosVista.js')).href);
const assert = (await import('node:assert/strict')).default;

if (typeof modulo.resumenImputacion !== 'function') {
  console.error('ROJO T80: falta resumenImputacion en saldosVista.ts');
  process.exit(1);
}
assert.equal(
  modulo.resumenImputacion([
    { uuid: 'a', concepto: 'cliente', importe: '40.00', estado: 'aceptado', imputacion: 'pendiente' },
  ]),
  'Pendiente de imputación: se solicita apertura administrativa.',
);
assert.equal(
  modulo.resumenImputacion([
    { uuid: 'a', concepto: 'cliente', importe: '40.00', estado: 'aceptado', imputacion: 'imputado' },
  ]),
  null,
);
assert.equal(modulo.resumenImputacion([]), null);

console.log('VERDE T80: aviso de imputación en verde (saldo + apertura)');
