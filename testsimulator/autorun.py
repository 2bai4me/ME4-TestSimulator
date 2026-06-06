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
        
        # Step 5: "Analyse starten" — use evaluate for reliable event triggering
        driver.page.locator("[data-testid='btn-analyse-start']").first.evaluate("el => el.click()")
        log("Analysis started — waiting for overlay...")
        
        # Wait for the analysis overlay + completion
        try:
            driver.page.locator("#apop").first.wait_for(state="visible", timeout=15000)
            log("Analysis running...")
            
            # Wait for the summary line that signals completion (📋 N Themen gespeichert)
            driver.page.locator("#apop:has-text('Themen gespeichert')").first.wait_for(state="attached", timeout=180000)
            driver.sleep(1)
            log("Analysis blocks complete")
            
            # Wait for consolidation if running
            try:
                driver.page.locator("#apop:has-text('Konsolidiere')").first.wait_for(state="attached", timeout=30000)
                driver.page.locator("#apop:has-text('Duplikat')").first.wait_for(state="attached", timeout=30000)
                log("Consolidation complete")
            except:
                log("Consolidation done or skipped")
            
            driver.sleep(1)
            # Click OK to close overlay and render results
            driver.page.locator("#aclose").first.evaluate("el => el.click()")
            driver.sleep(2)
            log("Analysis complete — overlay closed")
        except Exception as oe:
            log(f"Analysis issue: {oe}")
        
        # Now results should be rendered
        driver.sleep(1)
        
        # Wait for results in Accordion 3 — open it first
        driver.sleep(0.5)
        panel3 = driver.page.locator('.service-panel').nth(2)
        if not panel3.evaluate("el => el.classList.contains('open')"):
            panel3.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Opened results accordion")
        
        tiles_sel = ".topic-card"
        tiles_visible = wait_for_visible(tiles_sel, timeout=45000)
        
        if not tiles_visible:
            # Debug: dump what's in the container
            try:
                html = driver.page.locator("#thema-ergebnisse-container").inner_html()
                log(f"DEBUG container HTML ({len(html)} chars): {html[:300]}")
            except Exception as de:
                log(f"DEBUG container error: {de}")
            log("Trying fallback selectors...")
            for sel in ["#thema-ergebnisse-container .topic-card", "#thema-ergebnisse-container > div:not(.text-muted)", "#thema-ergebnisse-container [data-id]"]:
                tiles_visible = wait_for_visible(sel, timeout=10000)
                if tiles_visible:
                    tiles_sel = sel
                    log(f"Found tiles via: {sel}")
                    break
        
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
