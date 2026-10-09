/**
 * T79 (paquete 11): helpers puros de la vista de caja (estados jornada,
 * devengado vs caja, pendientes). Sin DOM ni red.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fuente = path.join(raiz, 'src', 'services', 'cajaVista.ts');
if (!fs.existsSync(fuente)) {
  console.error('ROJO T79: falta src/services/cajaVista.ts');
  process.exit(1);
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't79-'));
execSync(
  `npx tsc "${fuente}" --outDir "${tmp}" --module nodenext --target es2022 --moduleResolution nodenext --skipLibCheck`,
  { cwd: raiz, stdio: 'inherit' },
);
const modulo = await import(pathToFileURL(path.join(tmp, 'cajaVista.js')).href);
const assert = (await import('node:assert/strict')).default;

assert.equal(modulo.etiquetaEstadoJornada('abierta'), 'Abierta');
assert.equal(modulo.etiquetaEstadoJornada('cerrada'), 'Cerrada');
assert.equal(modulo.textoPendientes(0), null);
assert.equal(modulo.textoPendientes(3), '3 pendientes de imputación');
assert.equal(modulo.lineaMetodo('tarjeta', '40.00'), 'tarjeta: $40.00');
assert.equal(modulo.textoBalance('40.00', '10.00'), 'Cobrado $40.00 · Pagado $10.00');
// Sin float en el módulo (usos reales, no comentarios).
const codigo = fs.readFileSync(fuente, 'utf8');
const sinComentarios = codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
assert.ok(!sinComentarios.includes('parseFloat('), 'sin parseFloat');
assert.ok(!sinComentarios.includes('Number('), 'sin Number()');

console.log('VERDE T79: vista de caja en verde (estados + devengado vs caja)');
