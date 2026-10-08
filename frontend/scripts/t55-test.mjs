/**
 * T55 (paquete 8): catálogo que no se pierde + PWA sin api-cache.
 * Verificación estática (sin DOM): falla mientras exista `clear()` en el
 * sender, `api-cache` en la config o filtros booleanos inválidos.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fallos = [];

const sync = fs.readFileSync(path.join(raiz, 'src', 'hooks', 'useSync.ts'), 'utf8');
if (sync.includes(".catch(() => ({ data: [] }))")) {
  fallos.push('useSync.ts alimenta clear()+bulkPut con listas vacías ante fallos');
}
if (!sync.includes('esListaValida') || !sync.includes("db.transaction('rw'")) {
  fallos.push('useSync.ts no reemplaza el catálogo en transacción tras respuesta validada');
}
const config = fs.readFileSync(path.join(raiz, 'vite.config.ts'), 'utf8');
if (config.includes('api-cache')) {
  fallos.push('vite.config.ts todavía cachea API autenticada (api-cache)');
}
const sw = fs.readFileSync(
  path.join(raiz, 'src', 'pwa', 'ServiceWorkerRegistration.ts'), 'utf8',
);
if (!sw.includes('api-cache')) {
  fallos.push('ServiceWorkerRegistration.ts no purga la api-cache legacy');
}
// Filtros booleanos inválidos en código (no comentarios): where('activo').
for (const archivo of ['src/pages/RegistroCortes.tsx', 'src/hooks/useSync.ts']) {
  const lineas = fs
    .readFileSync(path.join(raiz, archivo), 'utf8')
    .split('\n')
    .filter((l) => !l.trim().startsWith('//') && !l.trim().startsWith('*'));
  if (lineas.some((l) => l.includes("where('activo')") || l.includes('where("activo")'))) {
    fallos.push(`${archivo} usa where('activo') con índice booleano inválido`);
  }
}

if (fallos.length > 0) {
  console.error('ROJO T55:');
  for (const f of fallos) console.error(' - ' + f);
  process.exit(1);
}
console.log('VERDE T55: catálogo transaccional + PWA sin api-cache en verde');
