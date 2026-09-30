export async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      console.log('SW registrado:', registration)
    } catch (error) {
      console.error('Error registrando SW:', error)
    }
  }
}
