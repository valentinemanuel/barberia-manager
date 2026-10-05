"""E2E: registrar un corte offline y sincronizarlo al reconectar.

Cubre la HU-2 offline de la constitución (offline-first) y valida el fix
de useSync (filtro en memoria en vez de where().equals(0)).
"""
from playwright.sync_api import sync_playwright

fallos = []

with sync_playwright() as p:
    navegador = p.chromium.launch(headless=True)
    contexto = navegador.new_context()
    page = contexto.new_page()

    page.goto("http://localhost:5173/")
    page.wait_for_load_state("networkidle")
    page.fill("#usuario", "admin")
    page.fill("#password", "admin123")
    page.click("button[type=submit]")
    page.wait_for_selector(".shell__rail", timeout=15000)

    # Limpio la cola local para arrancar de cero
    page.evaluate(
        "async () => { const m = await import('/src/services/db.ts'); await m.db.cortes.clear() }"
    )

    page.goto("http://localhost:5173/cortes")
    page.wait_for_selector(".ui-tarjeta-seleccion", timeout=15000)

    # --- 1. Sin red: registrar un corte ---
    contexto.set_offline(True)
    page.wait_for_timeout(300)

    page.locator(".ui-tarjeta-seleccion").first.click()
    page.locator("button[type=submit]").click()
    page.wait_for_timeout(1200)

    if page.locator("text=Sin conexión").count() == 0:
        fallos.append("No apareció el aviso 'Sin conexión' al guardar offline")
    else:
        print("OK: aviso de guardado offline mostrado")

    cola = page.evaluate(
        "async () => { const m = await import('/src/services/db.ts'); return (await m.db.cortes.toArray()).map(c => ({id: c.id, sinc: c.sincronizado})) }"
    )
    print(f"Cola local tras guardar offline: {cola}")
    if len(cola) != 1:
        fallos.append(f"Se esperaba 1 corte encolado, hay {len(cola)}")
    elif cola[0]["sinc"] is not False:
        fallos.append(f"El corte guardado offline tiene sincronizado={cola[0]['sinc']} (esperado False)")

    # --- 2. Reconectar: useSync debe encontrarlo y sincronizarlo ---
    contexto.set_offline(False)
    page.wait_for_timeout(3000)

    cola_final = page.evaluate(
        "async () => { const m = await import('/src/services/db.ts'); return (await m.db.cortes.toArray()).map(c => ({id: c.id, sinc: c.sincronizado, rech: c.rechazado ?? false})) }"
    )
    print(f"Cola local tras reconectar: {cola_final}")

    if not cola_final:
        fallos.append("El corte desapareció de IndexedDB")
    elif cola_final[0]["rech"]:
        fallos.append(f"El servidor rechazó la operación: {cola_final[0]}")
    elif cola_final[0]["sinc"] is not True:
        fallos.append(
            f"El corte sigue sin sincronizar (sinc={cola_final[0]['sinc']}); "
            "el fix de useSync no está funcionando"
        )
    else:
        print("OK: el corte offline se sincronizó al reconectar")

    # Limpieza
    page.evaluate(
        "async () => { const m = await import('/src/services/db.ts'); await m.db.cortes.clear() }"
    )
    navegador.close()

print()
if fallos:
    print("FALLOS:")
    for f in fallos:
        print(f"  - {f}")
    raise SystemExit(1)
print("E2E offline OK: guardar sin red, avisar, encolar y sincronizar al reconectar.")
