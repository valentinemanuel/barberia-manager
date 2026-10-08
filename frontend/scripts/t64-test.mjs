/**
 * T64 (paquete 9): helpers puros de la vista de saldos (excedente aparte,
 * revisión con causa, motivos propios). Sin DOM ni red.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'saldosVista.ts');
if (!fs.existsSync(fuente)) {
  console.error('ROJO T64: falta src/services/saldosVista.ts');
  process.exit(1);
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't64-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'saldosVista.js')).href);
const assert = (await import('node:assert/strict')).default;

// Excedente separado del restante: solo texto cuando hay sobrante.
assert.equal(modulo.textoExcedente({ excedente: '50.00' }), 'Excedente $50.00');
assert.equal(modulo.textoExcedente({ excedente: '0.00' }), null);
// Revisión visible con causa e importe, sin confundirla con saldo.
const movs = [
  { uuid: 'a', concepto: 'cliente', importe: '150.00', estado: 'revision', motivo_revision: 'exceso' },
  { uuid: 'b', concepto: 'cliente', importe: '30.00', estado: 'aceptado' },
  { uuid: 'c', concepto: 'comision', importe: '10.00', estado: 'aceptado' },
];
const revisiones = modulo.revisionesVisibles(movs);
assert.equal(revisiones.length, 1);
assert.equal(revisiones[0], 'Revisión: $150.00 (exceso)');
assert.deepEqual(
  modulo.agruparPorConcepto(movs).cliente.map((m) => m.uuid),
  ['a', 'b'],
);
assert.deepEqual(
  modulo.agruparPorConcepto(movs).comision.map((m) => m.uuid),
  ['c'],
);
// Motivos propios: solo filas con motivo no vacío.
assert.deepEqual(
  modulo.motivosVisibles([
    { motivo: 'cobro duplicado' },
    { motivo: null },
    { motivo: '' },
  ]),
  ['cobro duplicado'],
);

console.log('VERDE T64: vista de saldos en verde (excedente + revisión + motivos)');
