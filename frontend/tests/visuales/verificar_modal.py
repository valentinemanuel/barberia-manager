"""Verificación programática del modal (no depende de lectura de capturas).

Comprueba que:
1. El overlay cubre todo el viewport (regresión del bug de transform fill-mode).
2. El modal queda completamente dentro del viewport y centrado.
3. Escape lo cierra.
4. El error de precio NO aparece antes de tocar el campo.
"""
from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
fallos = []

with sync_playwright() as p:
    navegador = p.chromium.launch(headless=True)
    page = navegador.new_context(viewport=VIEWPORT).new_page()
    page.goto("http://localhost:5173/")
    page.wait_for_load_state("networkidle")
    page.fill("#usuario", "admin")
    page.fill("#password", "admin123")
    page.click("button[type=submit]")
    # Login y dashboard comparten URL "/", así que espero el shell (no la URL)
    page.wait_for_selector(".shell__rail", timeout=15000)
    page.wait_for_timeout(600)

    page.goto("http://localhost:5173/servicios")
    page.wait_for_selector(".shell__rail", timeout=15000)
    page.wait_for_selector("button:has-text('Nuevo servicio')", timeout=15000)
    page.locator("button", has_text="Nuevo servicio").first.click()
    page.wait_for_timeout(500)

    overlay = page.locator(".ui-modal-overlay")
    modal = page.locator(".ui-modal")

    if overlay.count() == 0:
        fallos.append("No existe .ui-modal-overlay")
    else:
        ob = overlay.bounding_box()
        print(f"Overlay: {ob}")
        if ob:
            if abs(ob["width"] - VIEWPORT["width"]) > 1 or abs(ob["height"] - VIEWPORT["height"]) > 1:
                fallos.append(
                    f"El overlay no cubre todo el viewport: "
                    f"{ob['width']}x{ob['height']} vs {VIEWPORT['width']}x{VIEWPORT['height']}"
                )

    mb = modal.bounding_box()
    print(f"Modal: {mb}")
    if mb:
        if mb["y"] < 0 or mb["y"] + mb["height"] > VIEWPORT["height"]:
            fallos.append(f"El modal se sale del viewport verticalmente: {mb}")
        centrado_x = abs((mb["x"] + mb["width"] / 2) - VIEWPORT["width"] / 2)
        if centrado_x > 2:
            fallos.append(f"El modal no está centrado horizontalmente (desvío {centrado_x}px)")

    # El error de precio no debe aparecer sin tocar el campo
    if page.locator("text=Debe ser mayor a 0").count() > 0:
        fallos.append("El error de precio aparece antes de que el usuario toque el campo")

    # Escape cierra
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    if page.locator(".ui-modal-overlay").count() > 0:
        fallos.append("Escape no cerró el modal")

    navegador.close()

print()
if fallos:
    print("FALLOS:")
    for f in fallos:
        print(f"  - {f}")
    raise SystemExit(1)
print("Modal OK: overlay completo, centrado, sin error prematuro, Escape cierra.")
