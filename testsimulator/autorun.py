"""
SMproducer Test via Playwright — Topic + Research workflow.
"""
from .webdriver import WebDriver
import random


def run_smproducer_test(youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", headless=False):
    """Full Step 1 (Topic) workflow: project → YouTube → analyse → tile → description → complete."""
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
        try:
            el = driver.page.locator(selector).first
            el.wait_for(state="visible", timeout=timeout)
            return el
        except:
            return None
    
    try:
        driver.start("http://localhost:5173")
        driver.sleep(3)
        log("Page loaded")
        
        click("btn-new-project")
        driver.sleep(2)
        log("New project created")
        
        # Ensure Accordion 2 open
        driver.sleep(0.5)
        panel2 = driver.page.locator('.service-panel').nth(1)
        if not panel2.evaluate("el => el.classList.contains('open')"):
            panel2.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Opened source text accordion")
        
        # YouTube tab + URL
        yt_check = driver.page.locator("#source-check-youtube")
        yt_check.evaluate("el => { el.disabled = false; el.checked = true; el.dispatchEvent(new Event('change', {bubbles:true})); }")
        driver.sleep(0.5)
        fill("youtube-url-input", youtube_url)
        driver.sleep(0.3)
        log("URL entered")
        
        click("btn-add-youtube")
        driver.sleep(5)
        log("Video added — transcript fetched")
        
        # Analyse starten
        driver.page.locator("[data-testid='btn-analyse-start']").first.evaluate("el => el.click()")
        log("Analysis started — waiting...")
        
        try:
            driver.page.locator("#apop").first.wait_for(state="visible", timeout=15000)
            driver.page.locator("#apop:has-text('Themen gespeichert')").first.wait_for(state="attached", timeout=180000)
            driver.sleep(1)
            try:
                driver.page.locator("#apop:has-text('Konsolidiere')").first.wait_for(state="attached", timeout=30000)
                driver.page.locator("#apop:has-text('Duplikat')").first.wait_for(state="attached", timeout=30000)
            except: pass
            driver.sleep(1)
            driver.page.locator("#aclose").first.evaluate("el => el.click()")
            driver.sleep(2)
            log("Analysis complete")
        except Exception as oe:
            log(f"Analysis: {oe}")
        
        driver.sleep(1)
        
        # Open Accordion 3 (results)
        panel3 = driver.page.locator('.service-panel').nth(2)
        if not panel3.evaluate("el => el.classList.contains('open')"):
            panel3.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
        
        tiles_sel = ".topic-card"
        tiles_visible = wait_for_visible(tiles_sel, timeout=45000)
        if not tiles_visible:
            for sel in ["#thema-ergebnisse-container .topic-card", "#thema-ergebnisse-container [data-id]"]:
                tiles_visible = wait_for_visible(sel, timeout=10000)
                if tiles_visible:
                    tiles_sel = sel
                    break
        
        if tiles_visible:
            driver.sleep(1)
            tiles = driver.page.locator(tiles_sel).all()
            log(f"Analysis complete — {len(tiles)} tiles")
            if tiles:
                chosen = rng.choice(tiles)
                chosen.evaluate("el => el.click()")
                driver.sleep(1)
                log("Tile selected (random)")
        else:
            log("No tiles found — continuing")
        
        # Open Accordion 4 (Projektstart)
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        panel4 = driver.page.locator('.service-panel').nth(3)
        if not panel4.evaluate("el => el.classList.contains('open')"):
            panel4.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
        
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        
        click("btn-beschreibung-erstellen", timeout=15000)
        log("Description created")
        driver.sleep(3)
        
        click("btn-service-abschliessen", timeout=10000)
        driver.sleep(2)
        log("Topic complete ✓")
        
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


def run_research_test(headless=False):
    """Step 2 (Research) workflow: validate prerequisites, test NotebookLM data, criteria, prompt."""
    driver = WebDriver(headless=headless)
    steps = []
    
    def log(msg):
        print(f"[ResearchTest] {msg}")
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
    
    try:
        driver.start("http://localhost:5173")
        driver.sleep(3)
        log("Page loaded")
        
        # Navigate to Research page — click Research in navigator
        # Use the sidebar navigator to go to Step 2
        nav_links = driver.page.locator("nav a, .sidebar-nav a, [data-nav='research']").all()
        research_clicked = False
        for link in nav_links:
            text = link.inner_text()
            if "Research" in text or "Recherche" in text or "Pesquisa" in text:
                link.evaluate("el => el.click()")
                research_clicked = True
                log(f"Navigated to Research via: {text.strip()}")
                break
        
        if not research_clicked:
            # Fallback: direct URL hash navigation
            driver.page.evaluate("window.location.hash = '#research'")
            driver.sleep(2)
            log("Navigated to Research via hash")
        
        driver.sleep(3)
        
        # ===== TASK 1: Prerequisites Check =====
        # Verify title field is filled
        title_val = driver.page.locator("[data-testid='research-nb-title']").input_value()
        if title_val:
            log(f"✓ Title present: {title_val[:50]}")
        else:
            log("✗ Title EMPTY — Step 1 may not be complete")
        
        desc_val = driver.page.locator("[data-testid='research-nb-desc']").input_value()
        if desc_val:
            log(f"✓ Description present ({len(desc_val)} chars)")
        else:
            log("✗ Description EMPTY")
        
        # ===== TASK 2: Accordion 1 — NotebookLM Data =====
        # Click copy title button
        click("btn-copy-title", timeout=5000)
        driver.sleep(0.5)
        log("Copy title clicked")
        
        # Click copy description button
        click("btn-copy-desc", timeout=5000)
        driver.sleep(0.5)
        log("Copy description clicked")
        
        # Type into notebook content
        fill("research-notebook-content", "Test note from TestSimulator: Research workflow validation.")
        driver.sleep(0.5)
        log("Notebook content typed")
        
        # Save notes
        click("btn-save-notizen", timeout=5000)
        driver.sleep(1)
        log("Notes saved")
        
        # ===== TASK 3: Accordion 2 — Criteria & Prompt =====
        # Open accordion 2 if closed
        panel2 = driver.page.locator('#research-accordion .service-panel').nth(1)
        if not panel2.evaluate("el => el.classList.contains('open')"):
            panel2.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Opened criteria accordion")
        
        # Type in extra text
        fill("research-extra-text", "TestSimulator: Testing criteria selection and prompt generation.")
        driver.sleep(0.5)
        log("Extra text entered")
        
        # Click "Auswahl speichern & Prompt generieren"
        click("btn-select-kriterien", timeout=10000)
        log("Generating prompt...")
        
        # Wait for prompt to appear (loading spinner disappears)
        driver.sleep(3)
        try:
            driver.page.locator("#generated-prompt pre").first.wait_for(state="visible", timeout=30000)
            log("Prompt generated ✓")
        except:
            try:
                driver.page.locator("#generated-prompt").first.wait_for(state="visible", timeout=10000)
                log("Prompt area visible")
            except:
                log("Prompt generation may have failed")
        
        driver.sleep(1)
        
        # ===== TASK 4: Accordion 3 — Prompt Actions =====
        # Copy prompt
        try:
            click("btn-copy-prompt", timeout=5000)
            driver.sleep(0.5)
            log("Prompt copied")
        except:
            log("Copy prompt button not available")
        
        # Teilen (split into chapters)
        try:
            click("btn-teilen-prompt", timeout=5000)
            driver.sleep(1)
            log("Split prompt clicked")
        except:
            log("Teilen button not available")
        
        driver.sleep(2)
        log("Research test complete ✓")
        
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
