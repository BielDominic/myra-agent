from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page()
    page.goto("https://www.linkedin.com/login", timeout=30000)
    page.wait_for_timeout(5000)

    print("=== TITULO ===")
    print(page.title())
    print()
    print("=== URL ===")
    print(page.url)
    print()
    print("=== TOTAL DE INPUTS ===")
    inputs = page.locator("input").all()
    print(f"Encontrados: {len(inputs)}")
    for i, inp in enumerate(inputs):
        try:
            print(f"{i}: type={inp.get_attribute('type')!r} name={inp.get_attribute('name')!r} id={inp.get_attribute('id')!r} visible={inp.is_visible()}")
        except Exception as e:
            print(f"{i}: erro {e}")
    print()
    print("=== IFRAMES ===")
    for f in page.frames:
        print(f"  {f.url}")
    print()
    print("=== PRIMEIROS 500 CHARS DO HTML ===")
    print(page.content()[:500])

    page.wait_for_timeout(5000)
    browser.close()
