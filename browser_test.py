from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        slow_mo=700
    )

    page = browser.new_page()

    print("1. Abrindo Google...")
    page.goto("https://www.google.com")

    time.sleep(3)

    print("2. Procurando a caixa de pesquisa...")

    campo = page.locator("textarea[name='q']")

    print("3. Clicando...")
    campo.click()

    time.sleep(1)

    print("4. Digitando...")
    campo.fill("Open WebUI")

    time.sleep(2)

    print("5. Apertando Enter...")
    campo.press("Enter")

    print("6. Aguardando resultados...")
    time.sleep(8)

    print("7. Finalizado.")

    browser.close()