/**
 * T84 (paquete 12): resto de la app sin float monetario (estático + build).
 * Conteos enteros (stock/duración/length) pueden usar Number: son exactos.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fallos = [];
const sinComentarios = (codigo) =>
  codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');

const paginas = [
  'src/pages/GestionProductos.tsx',
  'src/pages/GestionServicios.tsx',
  'src/pages/GestionUsuarios.tsx',
  'src/pages/CierreCaja.tsx',
  'src/pages/Reportes.tsx',
];
for (const archivo of paginas) {
  const ruta = path.join(raiz, archivo);
  if (!fs.existsSync(ruta)) continue;
  const codigo = sinComentarios(fs.readFileSync(ruta, 'utf8'));
  if (codigo.includes('parseFloat(')) fallos.push(`${archivo}: parseFloat`);
  // Number() solo permitido en conteos enteros (línea con stock/duración).
  const lineas = codigo.split('\n');
  for (const linea of lineas) {
    if (!linea.includes('Number(')) continue;
    if (/stock|duracion|minimo|length/i.test(linea)) continue;
    fallos.push(`${archivo}: ${linea.trim().slice(0, 80)}`);
  }
  if (codigo.includes('formatearMoneda(') && !codigo.includes('formatearMonedaExacta(')) {
    fallos.push(`${archivo}: formatearMoneda(number) sin exacta`);
  }
}

if (fallos.length > 0) {
  console.error('ROJO T84:');
  for (const f of fallos) console.error(' - ' + f);
  process.exit(1);
}
console.log('VERDE T84: resto de la app sin float monetario');
