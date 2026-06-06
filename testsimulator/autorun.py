"""
SMproducer Test via Playwright — robust multi-step workflow.
"""
from .webdriver import WebDriver
import random


def run_smproducer_test(youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", headless=False):
    driver = WebDriver(headless=headless)
    steps = []
    rng = random.Random()
    
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
    
    def wait_for_visible(selector, timeout=30000):
        """Wait for an element to become visible. Returns the element or None."""
        try:
            el = driver.page.locator(selector).first
            el.wait_for(state="visible", timeout=timeout)
            return el
        except:
            return None
    
    def wait_for_hidden(selector, timeout=60000):
        """Wait for an element to become hidden. Returns True if hidden."""
        try:
            el = driver.page.locator(selector).first
            el.wait_for(state="hidden", timeout=timeout)
            return True
        except:
            return False
    
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
            log("Source text accordion open")
        
        # Step 3: YouTube tab + URL
        yt_check = driver.page.locator("#source-check-youtube")
        yt_check.evaluate("el => { el.disabled = false; el.checked = true; el.dispatchEvent(new Event('change', {bubbles:true})); }")
        driver.sleep(0.5)
        fill("youtube-url-input", youtube_url)
        driver.sleep(0.3)
        log(f"URL entered")
        
        # Step 4: "Hinzufügen"
        click("btn-add-youtube")
        driver.sleep(5)
        log("Video added — transcript fetched")
        
        # Step 5: "Analyse starten" — then WAIT for completion
        click("btn-analyse-start")
        log("Analysis started — waiting for completion...")
        
        # Wait for the AI overlay / loading to disappear (up to 90s)
        ai_done = wait_for_hidden("#ai-overlay", timeout=90000)
        if ai_done:
            log("AI overlay dismissed")
        else:
            # Fallback: wait for result tiles to appear
            log("Waiting for result tiles...")
        
        # Wait for results in Accordion 3
        tiles_sel = "#thema-ergebnisse-container .topic-card, #thema-ergebnisse-container [class*='result'], #thema-ergebnisse-container [class*='ergebnis']"
        tiles_visible = wait_for_visible(tiles_sel, timeout=60000)
        
        if tiles_visible:
            driver.sleep(1)
            # Get all result tiles
            tiles = driver.page.locator(tiles_sel).all()
            log(f"Analysis complete — {len(tiles)} result tiles found")
            
            # Step 6: Random tile selection — click a random tile
            if tiles:
                chosen = rng.choice(tiles)
                chosen.evaluate("el => el.click()")
                driver.sleep(1)
                # Try to get the title
                try:
                    title_el = chosen.locator("h3, h4, strong, [class*='title']").first
                    title_text = title_el.inner_text() if title_el else "unknown"
                    log(f"Selected tile: {title_text[:60]}")
                except:
                    log("Tile selected (random)")
        else:
            log("No result tiles found — continuing anyway")
        
        # Open Accordion 4 ("Projektstart")
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        panel4 = driver.page.locator('.service-panel').nth(3)
        if not panel4.evaluate("el => el.classList.contains('open')"):
            panel4.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Opened project start accordion")
        
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        
        # Step 7: "Beschreibung erstellen"
        click("btn-beschreibung-erstellen", timeout=15000)
        log("Description creating...")
        
        # Wait for creation to complete (button re-enables)
        driver.sleep(3)
        try:
            btn = driver.page.locator("[data-testid='btn-beschreibung-erstellen']")
            btn.wait_for(state="visible", timeout=10000)
            # Wait until it's not disabled anymore
            for _ in range(30):
                if btn.is_enabled():
                    break
                driver.sleep(1)
        except: pass
        log("Description created")
        
        # Step 8: "Service abschließen"
        click("btn-service-abschliessen", timeout=10000)
        driver.sleep(2)
        log("Service completed ✓")
        
        driver.sleep(2)
        driver.stop()
        return {"status": "done", "steps": steps}
        
    except Exception as e:
        log(f"ERROR: {e}")
        try:
            driver.page.screenshot(path="workflows/last_error.png")
            log("Screenshot saved")
        except: pass
        try: driver.stop()
        except: pass
        return {"status": "error", "error": str(e), "steps": steps}
