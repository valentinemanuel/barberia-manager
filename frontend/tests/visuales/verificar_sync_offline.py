"""Comprueba si useSync realmente encuentra los cortes encolados offline.

Dexie: db.cortes.where('sincronizado').equals(0)
Si los booleanos no indexan en IndexedDB, esto devuelve [] y los cortes
guardados offline NUNCA se sincronizan (rompe offline-first).
"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    navegador = p.chromium.launch(headless=True)
    page = navegador.new_context().new_page()
    page.goto("http://localhost:5173/")
    page.wait_for_load_state("networkidle")
    page.fill("#usuario", "admin")
    page.fill("#password", "admin123")
    page.click("button[type=submit]")
    page.wait_for_selector(".shell__rail", timeout=15000)

    resultado = page.evaluate(
        """async () => {
      const m = await import('/src/services/db.ts')
      const db = m.db
      await db.cortes.clear()
      await db.cortes.add({
        barbero_id: 1, servicio_id: 1, precio: 100, porcentaje_barbero: 40,
        parte_barbero: 40, parte_barberia: 60, metodo_pago: 'efectivo',
        fecha: new Date().toISOString(), sincronizado: false
      })
      const porWhere = await db.cortes.where('sincronizado').equals(0).toArray()
      const porFiltro = await db.cortes.filter(c => !c.sincronizado).toArray()
      await db.cortes.clear()
      return { porWhere: porWhere.length, porFiltro: porFiltro.length }
    }"""
    )

    navegador.close()

print(f"where('sincronizado').equals(0) -> {resultado['porWhere']} cortes")
print(f"filter(c => !c.sincronizado)    -> {resultado['porFiltro']} cortes")

if resultado["porWhere"] == 0 and resultado["porFiltro"] > 0:
    print("\nCONFIRMADO: la consulta de useSync NO encuentra los cortes offline.")
    raise SystemExit(1)
print("\nOK: la consulta de useSync sí encuentra los cortes pendientes.")
