/**
 * T50 (paquete 8): verifica el módulo puro de operaciones de corte.
 * Sin dependencias: compila solo `operacionesCortes.ts` a JS temporal
 * y ejecuta asserts con `node:test`. Rojo si el módulo falta o falla.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'operacionesCortes.ts');
if (!fs.existsSync(fuente)) {
  console.error('ROJO T50: falta src/services/operacionesCortes.ts');
  process.exit(1);
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't50-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'operacionesCortes.js')).href);
const assert = (await import('node:assert/strict')).default;

const { describe, it } = await import('node:test');

// --- Codec centavos por dígitos (sin float) ---
assert.equal(modulo.pesosStrACentavos('100.00'), 10000);
assert.equal(modulo.pesosStrACentavos('0.05'), 5);
assert.equal(modulo.centavosAPesosStr(3), '0.03');
assert.throws(() => modulo.pesosStrACentavos('10.005'), /decimales/);
assert.throws(() => modulo.pesosStrACentavos('abc'), /formato/);
// --- Comisión exacta HALF_UP con enteros (0.05 al 50% → 3 centavos) ---
assert.equal(modulo.estimarComisionCentavos(5, 5000), 3);
assert.equal(modulo.estimarComisionCentavos(8, 3000), 2);
assert.equal(modulo.estimarComisionCentavos(10000, 5000), 5000);
// --- Operación con instante único + UUIDs ---
const ahora = new Date('2026-10-07T10:00:00.000Z');
const op = modulo.crearOperacionCorte({
  actorId: 7,
  servicioId: 3,
  metodoPago: 'efectivo',
  precioCentavos: 10000,
  porcentajeCentesimas: 5000,
  modoCaptura: 'offline',
  ahora,
});
assert.match(op.operacionUuid, /^[0-9a-f-]{36}$/i);
assert.match(op.corteUuid, /^[0-9a-f-]{36}$/i);
assert.notEqual(op.operacionUuid, op.corteUuid);
assert.equal(op.actorId, 7);
assert.equal(op.modoCaptura, 'offline');
assert.equal(op.instanteCambioUtc, '2026-10-07T10:00:00.000Z');
assert.equal(op.momentoRealUtc, '2026-10-07T10:00:00.000Z');
assert.equal(op.estado, 'pendiente');
// --- Sin float en el módulo (usos reales, no menciones en comentarios) ---
const codigo = fs.readFileSync(fuente, 'utf8');
const sinComentarios = codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
assert.ok(!sinComentarios.includes('parseFloat('), 'sin parseFloat');
// Prohibido: convertir strings de dinero a float. Permitido: Number(bigint)
// y guards Number.isSafeInteger / Number.isNaN.
const numberUsos = [...sinComentarios.matchAll(/Number\(([^)]*)\)/g)].map((m) => m[1].trim());
for (const uso of numberUsos) {
  assert.ok(
    uso === 'resultado' || uso.startsWith('resultado '),
    `Number() solo para BigInt->Number, hallado: Number(${uso})`,
  );
}

console.log('VERDE T50: operacionesCortes puro en verde (codec + HALF_UP + UUID + instante único)');
