"""Verificación visual del sistema de diseño (spec 001, T11).

Captura login + dashboards en desktop y móvil, y reporta errores de consola.
"""
import os
from playwright.sync_api import sync_playwright

SALIDA = os.path.join(os.path.dirname(__file__), "capturas")
os.makedirs(SALIDA, exist_ok=True)

errores_consola = []


def capturar(page, nombre):
    page.screenshot(path=os.path.join(SALIDA, f"{nombre}.png"), full_page=True)
    print(f"  captura: {nombre}.png")


with sync_playwright() as p:
    navegador = p.chromium.launch(headless=True)

    # --- Desktop (admin) ---
    contexto = navegador.new_context(viewport={"width": 1440, "height": 900})
    page = contexto.new_page()
    page.on(
        "console",
        lambda msg: errores_consola.append(msg.text) if msg.type == "error" else None,
    )

    page.goto("http://localhost:5173/")
    page.wait_for_load_state("networkidle")
    capturar(page, "01-login-desktop")

    # Login
    page.fill("#usuario", "admin")
    page.fill("#password", "admin123")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    capturar(page, "02-dashboard-admin")

    # Cada sección del rail
    for ruta, nombre in [
        ("/cortes", "03-registro-cortes"),
        ("/servicios", "04-servicios"),
        ("/productos", "05-productos"),
        ("/usuarios", "06-usuarios"),
        ("/reportes", "07-reportes"),
        ("/cierre-caja", "08-cierre-caja"),
    ]:
        page.goto(f"http://localhost:5173{ruta}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        capturar(page, nombre)

    # Modal de gestión (sin full_page: el overlay fixed se corta en capturas largas)
    page.goto("http://localhost:5173/servicios")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    botones = page.locator("button", has_text="Nuevo servicio")
    if botones.count() > 0:
        botones.first.click()
        page.wait_for_timeout(400)
        page.screenshot(path=os.path.join(SALIDA, "09-modal-servicio.png"))
        print("  captura: 09-modal-servicio.png")
        page.keyboard.press("Escape")

    contexto.close()

    # --- Móvil ---
    contexto_movil = navegador.new_context(
        viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True
    )
    movil = contexto_movil.new_page()
    movil.on(
        "console",
        lambda msg: errores_consola.append(msg.text) if msg.type == "error" else None,
    )

    movil.goto("http://localhost:5173/")
    movil.wait_for_load_state("networkidle")
    capturar(movil, "10-login-movil")

    movil.fill("#usuario", "admin")
    movil.fill("#password", "admin123")
    movil.click("button[type=submit]")
    movil.wait_for_load_state("networkidle")
    movil.wait_for_timeout(800)
    capturar(movil, "11-dashboard-movil")

    movil.goto("http://localhost:5173/cortes")
    movil.wait_for_load_state("networkidle")
    movil.wait_for_timeout(500)
    capturar(movil, "12-cortes-movil")

    # Ruta que vive en la hoja "Más": verificar la pestaña resaltada
    movil.goto("http://localhost:5173/usuarios")
    movil.wait_for_load_state("networkidle")
    movil.wait_for_timeout(500)
    capturar(movil, "13-usuarios-movil")

    boton_mas = movil.locator("button.shell__tab", has_text="Más")
    if boton_mas.count() > 0:
        boton_mas.first.click()
        movil.wait_for_timeout(400)
        capturar(movil, "14-hoja-mas-movil")

    # Concordancia y fecha en reportes (regresión de formato)
    movil.goto("http://localhost:5173/reportes")
    movil.wait_for_load_state("networkidle")
    movil.wait_for_timeout(500)
    capturar(movil, "15-reportes-movil")

    contexto_movil.close()
    navegador.close()

print()
if errores_consola:
    print(f"ERRORES DE CONSOLA ({len(errores_consola)}):")
    for e in dict.fromkeys(errores_consola):
        print(f"  - {e}")
else:
    print("Sin errores de consola.")
