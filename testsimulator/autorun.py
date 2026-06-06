"""
SMproducer Test via Playwright with data-testid selectors.
"""
from .webdriver import WebDriver


def run_smproducer_test(youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", headless=False):
    driver = WebDriver(headless=headless)
    steps = []
    
    def log(msg):
        print(f"[TestSimulator] {msg}")
        steps.append(msg)
    
    def click(testid, timeout=10000):
        sel = f"[data-testid='{testid}']"
        el = driver.page.locator(sel).first
        el.wait_for(state="visible", timeout=timeout)
        el.click()
    
    def fill(testid, text, timeout=10000):
        sel = f"[data-testid='{testid}']"
        el = driver.page.locator(sel).first
        el.wait_for(state="visible", timeout=timeout)
        el.fill(text)
    
    try:
        driver.start("http://localhost:5173")
        driver.sleep(3)
        log("Page loaded")
        
        # Step 1: "+ New Project"
        click("btn-new-project")
        driver.sleep(2)
        log("New project created")
        
        # Step 2: Click YouTube source tab (checkbox)
        driver.sleep(0.5)
        click("source-tab-youtube")
        driver.sleep(0.5)
        log("YouTube tab selected")
        
        # Step 3: Type YouTube URL
        fill("youtube-url-input", youtube_url)
        driver.sleep(0.3)
        log(f"URL: {youtube_url}")
        
        # Step 4: Click "Hinzufügen"
        click("btn-add-youtube")
        driver.sleep(4)
        log("Video added")
        
        # Step 5: Click "Analyse starten"
        driver.page.locator("button:has-text('Analyse starten')").first.click()
        driver.sleep(6)
        log("Analysis started")
        
        # Step 6: Pick first result card
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(1)
        cards = driver.page.locator("[class*='chapter'], [class*='result'], [class*='topic']").all()
        if cards:
            cards[0].click()
            log("Result selected")
        
        # Step 7: Project Start -> Beschreibung erstellen
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        click("btn-beschreibung-erstellen", timeout=15000)
        driver.sleep(3)
        log("Description created")
        
        # Step 8: Service abschließen
        click("btn-service-abschliessen", timeout=10000)
        driver.sleep(2)
        log("Service completed")
        
        driver.sleep(2)
        driver.stop()
        return {"status": "done", "steps": steps}
        
    except Exception as e:
        log(f"ERROR: {e}")
        try:
            driver.page.screenshot(path="workflows/last_error.png")
        except: pass
        try: driver.stop()
        except: pass
        return {"status": "error", "error": str(e), "steps": steps}
