/**
 * Purgas de caches legacy (paquete 8, T55): la `api-cache` guardaba
 * respuestas autenticadas compartidas entre cuentas (RF-33/RNF-5).
 * Se elimina sin tocar IndexedDB ni exigir nueva autenticación.
 */
export async function purgarCachesApiLegacy(): Promise<void> {
  try {
    if ('caches' in window) {
      for (const nombre of await caches.keys()) {
        if (nombre === 'api-cache') {
          await caches.delete(nombre)
        }
      }
    }
  } catch (error) {
    console.error('Error purgando caches API legacy:', error)
  }
}

export async function registerServiceWorker() {
  await purgarCachesApiLegacy();
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      console.log('SW registrado:', registration)
    } catch (error) {
      console.error('Error registrando SW:', error)
    }
  }
}
