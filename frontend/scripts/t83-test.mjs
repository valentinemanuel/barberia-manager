/**
 * T83 (paquete 12): pantallas 002 sin puentes float (estático + build).
 * Falla mientras queden conversiones float en Registro/MisSaldos/Dashboard.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fallos = [];
const sinComentarios = (codigo) =>
  codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');

const paginas = [
  'src/pages/RegistroCortes.tsx',
  'src/pages/MisSaldos.tsx',
  'src/pages/DashboardBarbero.tsx',
];
for (const archivo of paginas) {
  const codigo = sinComentarios(fs.readFileSync(path.join(raiz, archivo), 'utf8'));
  if (codigo.includes('parseFloat(')) fallos.push(`${archivo}: parseFloat`);
  if (codigo.includes('.toFixed(')) fallos.push(`${archivo}: toFixed sobre binario`);
  if (/Math\.round\([^)]*\* *100/.test(codigo) || /Math\.round\([^)]*\/ *100/.test(codigo)) {
    fallos.push(`${archivo}: Math.round con *100//100 float`);
  }
  const numbers = [...codigo.matchAll(/Number\(([^)]*)\)/g)].map((m) => m[1].trim());
  for (const uso of numbers) {
    if (!/^(conteo|cantidad|totalCortes|length)/.test(uso)) {
      fallos.push(`${archivo}: Number(${uso}) monetario`);
    }
  }
  if (codigo.includes('formatearMoneda(') && !codigo.includes('formatearMonedaExacta(')) {
    fallos.push(`${archivo}: formatearMoneda(number) sin exacta`);
  }
}

if (fallos.length > 0) {
  console.error('ROJO T83:');
  for (const f of fallos) console.error(' - ' + f);
  process.exit(1);
}
console.log('VERDE T83: pantallas 002 sin puentes float');
