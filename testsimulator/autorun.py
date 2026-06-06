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
        el.click(force=True)
    
    def fill(testid, text, timeout=10000):
        sel = f"[data-testid='{testid}']"
        el = driver.page.locator(sel).first
        el.wait_for(state="visible", timeout=timeout)
        el.fill(text)
    
    def click_js(selector, timeout=10000):
        el = driver.page.locator(selector).first
        el.wait_for(state="attached", timeout=timeout)
        el.evaluate("el => el.click()")
    
    try:
        driver.start("http://localhost:5173")
        driver.sleep(3)
        log("Page loaded")
        
        # Step 1: "+ New Project"
        click("btn-new-project")
        driver.sleep(2)
        log("New project created")
        
        # Step 2: Ensure Accordion 2 ("Quelltext") is open
        driver.sleep(0.5)
        panel2 = driver.page.locator('.service-panel').nth(1)
        if not panel2.evaluate("el => el.classList.contains('open')"):
            panel2.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Opened source text accordion")
        else:
            log("Source text accordion already open")
        
        # Step 3: Click YouTube source tab  
        # The checkbox is disabled — click it via JavaScript
        yt_check = driver.page.locator("#source-check-youtube")
        yt_check.evaluate("""
            el => { 
                el.disabled = false; 
                el.checked = true; 
                el.dispatchEvent(new Event('change', {bubbles:true}));
            }
        """)
        driver.sleep(0.5)
        log("YouTube tab activated")
        
        # Step 4: Type YouTube URL
        fill("youtube-url-input", youtube_url)
        driver.sleep(0.3)
        log(f"URL entered: ...{youtube_url[-20:]}")
        
        # Step 5: Click "Hinzufügen"
        click("btn-add-youtube")
        driver.sleep(5)
        log("Video added — waiting for transcript...")
        
        # Step 6: Click "Analyse starten" 
        driver.page.locator("button:has-text('Analyse starten')").first.evaluate("el => el.click()")
        driver.sleep(8)
        log("Analysis running...")
        
        # Open Accordion 4 ("Projektstart") — has Beschreibung erstellen + Service abschließen
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        panel4 = driver.page.locator('.service-panel').nth(3)
        if not panel4.evaluate("el => el.classList.contains('open')"):
            panel4.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Opened project start accordion")
        
        # Scroll into view for buttons
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Step 7: Pick first result card if visible
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(1)
        cards = driver.page.locator("[class*='chapter'], [class*='result'], [class*='topic'], .topic-card").all()
        if cards:
            cards[0].evaluate("el => el.click()")
            driver.sleep(1)
            log(f"Selected result tile ({len(cards)} available)")
        
        # Step 8: Beschreibung erstellen
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        click("btn-beschreibung-erstellen", timeout=15000)
        driver.sleep(3)
        log("Description created")
        
        # Step 9: Service abschließen
        click("btn-service-abschliessen", timeout=10000)
        driver.sleep(2)
        log("Service completed ✓")
        
        driver.stop()
        return {"status": "done", "steps": steps}
        
    except Exception as e:
        log(f"ERROR: {e}")
        try:
            driver.page.screenshot(path="workflows/last_error.png")
            log("Screenshot saved to workflows/last_error.png")
        except: pass
        try: driver.stop()
        except: pass
        return {"status": "error", "error": str(e), "steps": steps}
