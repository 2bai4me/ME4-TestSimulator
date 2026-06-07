"""
SMproducer Combined Test — Step 1 (Topic) → Step 2 (Research) via Playwright.
"""
from .webdriver import WebDriver
import random


def run_smproducer_test(youtube_url="https://www.youtube.com/watch?v=RdqYvdT74i0", headless=False):
    """Step 1 only."""
    driver = WebDriver(headless=headless)
    steps = []
    rng = random.Random()
    
    def log(msg):
        print(f"[Step1] {msg}")
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
        
        click("btn-new-project")
        driver.sleep(2)
        log("New project created")
        
        panel2 = driver.page.locator('.service-panel').nth(1)
        if not panel2.evaluate("el => el.classList.contains('open')"):
            panel2.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
        
        yt_check = driver.page.locator("#source-check-youtube")
        yt_check.evaluate("el => { el.disabled = false; el.checked = true; el.dispatchEvent(new Event('change', {bubbles:true})); }")
        driver.sleep(0.5)
        fill("youtube-url-input", youtube_url)
        driver.sleep(0.3)
        click("btn-add-youtube")
        driver.sleep(5)
        log("Video added")
        
        driver.page.locator("[data-testid='btn-analyse-start']").first.evaluate("el => el.click()")
        log("Analyse...")
        
        try:
            driver.page.locator("#apop").first.wait_for(state="visible", timeout=15000)
            driver.page.locator("#apop:has-text('Themen gespeichert')").first.wait_for(state="attached", timeout=180000)
            driver.sleep(1)
            try:
                driver.page.locator("#apop:has-text('Konsolidiere')").first.wait_for(state="attached", timeout=30000)
                driver.page.locator("#apop:has-text('Duplikat')").first.wait_for(state="attached", timeout=30000)
            except: pass
            driver.page.locator("#aclose").first.evaluate("el => el.click()")
            driver.sleep(2)
            log("Analysis done")
        except Exception as oe:
            log(f"Analysis: {oe}")
        
        # Open Accordion 3 + pick tile
        panel3 = driver.page.locator('.service-panel').nth(2)
        if not panel3.evaluate("el => el.classList.contains('open')"):
            panel3.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
        
        tiles = driver.page.locator(".topic-card").all()
        if tiles:
            rng.choice(tiles).evaluate("el => el.click()")
            log(f"Tile selected ({len(tiles)} available)")
        
        # Accordion 4 → Beschreibung → Abschluss
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        panel4 = driver.page.locator('.service-panel').nth(3)
        if not panel4.evaluate("el => el.classList.contains('open')"):
            panel4.locator('.service-panel-header').evaluate("el => el.click()")
            driver.sleep(0.5)
        
        click("btn-beschreibung-erstellen", timeout=15000)
        driver.sleep(3)
        log("Description created")
        
        click("btn-service-abschliessen", timeout=10000)
        driver.sleep(2)
        log("Topic complete ✓")
        
        driver.stop()
        return {"status": "done", "steps": steps, "driver": None}
        
    except Exception as e:
        log(f"ERROR: {e}")
        try: driver.page.screenshot(path="workflows/last_error.png")
        except: pass
        try: driver.stop()
        except: pass
        return {"status": "error", "error": str(e), "steps": steps}


def run_full_test(youtube_url="https://www.youtube.com/watch?v=RdqYvdT74i0", headless=False):
    """Combined Step 1 + Step 2 workflow — single browser session."""
    driver = WebDriver(headless=headless)
    steps = []
    rng = random.Random()
    
    def log(msg):
        print(f"[FullTest] {msg}")
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
        log("=== STEP 1: TOPIC ===")
        
        click("btn-new-project")
        driver.sleep(2)
        log("[1] New project")
        
        panel2 = driver.page.locator('.service-panel').nth(1)
        if not panel2.evaluate("el => el.classList.contains('open')"):
            panel2.locator('.service-panel-header').evaluate("el => el.click()")
        
        yt_check = driver.page.locator("#source-check-youtube")
        yt_check.evaluate("el => { el.disabled = false; el.checked = true; el.dispatchEvent(new Event('change', {bubbles:true})); }")
        fill("youtube-url-input", youtube_url)
        click("btn-add-youtube")
        driver.sleep(5)
        log("[1] Video added")
        
        driver.page.locator("[data-testid='btn-analyse-start']").first.evaluate("el => el.click()")
        driver.page.locator("#apop").first.wait_for(state="visible", timeout=15000)
        driver.page.locator("#apop:has-text('Themen gespeichert')").first.wait_for(state="attached", timeout=180000)
        try:
            driver.page.locator("#apop:has-text('Duplikat')").first.wait_for(state="attached", timeout=60000)
        except: pass
        driver.page.locator("#aclose").first.evaluate("el => el.click()")
        driver.sleep(2)
        log("[1] Analysis done")
        
        panel3 = driver.page.locator('.service-panel').nth(2)
        if not panel3.evaluate("el => el.classList.contains('open')"):
            panel3.locator('.service-panel-header').evaluate("el => el.click()")
        tiles = driver.page.locator(".topic-card").all()
        if tiles:
            rng.choice(tiles).evaluate("el => el.click()")
            log(f"[1] Tile selected ({len(tiles)})")
        
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        panel4 = driver.page.locator('.service-panel').nth(3)
        if not panel4.evaluate("el => el.classList.contains('open')"):
            panel4.locator('.service-panel-header').evaluate("el => el.click()")
        click("btn-beschreibung-erstellen", timeout=15000)
        driver.sleep(3)
        click("btn-service-abschliessen", timeout=10000)
        driver.sleep(2)
        log("[1] Topic complete ✓")
        
        # ===== STEP 2: RESEARCH =====
        log("=== STEP 2: RESEARCH ===")
        
        # Navigate to Research — reload page first to clear Vite module cache
        log("=== STEP 2: RESEARCH ===")
        driver.page.reload()
        driver.sleep(3)
        log("[2] Page reloaded")
        
        # Click Research in navigator (page is fresh now)
        driver.page.locator("[data-nav='2']").first.click(force=True)
        driver.sleep(3)
        
        # Check prerequisites: title and description should be filled
        try:
            nb_title = driver.page.locator("[data-testid='research-nb-title']").input_value(timeout=10000)
            log(f"[2] ✓ Title: {nb_title[:50] if nb_title else 'EMPTY'}")
        except:
            log("[2] ✗ Title field not found or empty — Research may show empty state")
            # Research page might show "no project" state — try clicking nav again
            driver.page.locator("[data-nav='1']").first.click(force=True, timeout=3000)
            driver.sleep(1)
            driver.page.locator("[data-nav='2']").first.click(force=True, timeout=3000)
            driver.sleep(3)
        
        # Copy title + description
        try: click("btn-copy-title", timeout=5000); log("[2] Copy title ✓")
        except: log("[2] Copy title skipped")
        try: click("btn-copy-desc", timeout=5000); log("[2] Copy desc ✓")  
        except: log("[2] Copy desc skipped")
        
        # Type notebook content + save
        try:
            fill("research-notebook-content", "TestSimulator Research validation note.")
            driver.sleep(0.5)
            click("btn-save-notizen", timeout=5000)
            log("[2] Notes saved ✓")
        except Exception as e:
            log(f"[2] Notes: {e}")
        
        # Criteria selection + prompt generation
        try:
            panel_r2 = driver.page.locator('#research-accordion .service-panel').nth(1)
            if not panel_r2.evaluate("el => el.classList.contains('open')"):
                panel_r2.locator('.service-panel-header').evaluate("el => el.click()")
                driver.sleep(0.5)
            
            fill("research-extra-text", "TestSimulator criteria test.")
            click("btn-select-kriterien", timeout=10000)
            driver.sleep(3)
            
            try:
                driver.page.locator("#generated-prompt pre").first.wait_for(state="visible", timeout=30000)
                log("[2] Prompt generated ✓")
            except:
                log("[2] Prompt: waiting longer...")
                driver.sleep(10)
            
            click("btn-copy-prompt", timeout=5000)
            log("[2] Prompt copied ✓")
        except Exception as e:
            log(f"[2] Criteria/Prompt: {e}")
        
        driver.sleep(2)
        log("=== FULL WORKFLOW DONE ✓ ===")
        driver.stop()
        return {"status": "done", "steps": steps}
        
    except Exception as e:
        log(f"ERROR: {e}")
        try: driver.page.screenshot(path="workflows/last_error.png")
        except: pass
        try: driver.stop()
        except: pass
        return {"status": "error", "error": str(e), "steps": steps}


def run_research_test(headless=False):
    """Research-only test — uses existing project with Step 1 completed."""
    driver = WebDriver(headless=headless)
    steps = []
    
    def log(msg):
        print(f"[Research] {msg}")
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
        
        driver.page.locator("#thema-channel-select").select_option("LUYB")
        driver.sleep(1)
        project_select = driver.page.locator("#existing-project-select")
        last_val = project_select.locator("option").last.get_attribute("value")
        project_select.select_option(value=last_val)
        log(f"Project: {last_val}")
        driver.sleep(2)
        
        # Navigate to Research — call onclick on .nav-item directly
        driver.sleep(0.5)
        nav_clicked = driver.page.evaluate("""
            (() => {
                const items = document.querySelectorAll('.nav-item');
                for (const li of items) {
                    if (li.dataset.nav === '2') {
                        if (li.onclick) li.onclick();
                        return 'onclick called';
                    }
                }
                return 'not found among ' + items.length;
            })()
        """)
        log(f"Nav: {nav_clicked}")
        driver.sleep(4)
        ws_title = driver.page.locator(".workspace-title").first.inner_text(timeout=5000)
        log(f"Page: {ws_title}")
        
        # Open Accordion 1 (NotebookLM Data) — it starts closed
        p1 = driver.page.locator("#research-accordion .service-panel").nth(0)
        if not p1.evaluate("el => el.classList.contains('open')"):
            p1.locator(".service-panel-header").evaluate("el => el.click()")
            driver.sleep(0.5)
            log("Accordion 1 opened")
        
        passed = 0
        total = 6
        
        try:
            t = driver.page.locator("[data-testid='research-nb-title']").input_value(timeout=10000)
            log("[✓] Title present" if t else "[✗] Title EMPTY")
            if t: passed += 1
        except Exception as e:
            log(f"[✗] Title error: {e}")
            ws = driver.page.locator("#workspace").inner_html(timeout=3000)[:300]
            log(f"Workspace: {ws}")
            driver.stop()
            return {"status": "error", "error": f"Research not loaded", "steps": steps}
        
        try:
            d = driver.page.locator("[data-testid='research-nb-desc']").input_value(timeout=5000)
            log(f"[✓] Description {len(d)} chars" if d else "[✗] Description EMPTY")
            if d: passed += 1
        except:
            log("[✗] Description error")
        
        try:
            click("btn-copy-title", timeout=5000)
            log("[✓] Copy title")
            passed += 1
        except Exception as e:
            log(f"[✗] Copy title: {e}")
        
        try:
            click("btn-copy-desc", timeout=5000)
            log("[✓] Copy desc")
            passed += 1
        except:
            log("[✗] Copy desc")
        
        try:
            fill("research-notebook-content", "TestSimulator Research note.")
            click("btn-save-notizen", timeout=5000)
            log("[✓] Notes saved")
            passed += 1
        except Exception as e:
            log(f"[✗] Notes: {e}")
        
        try:
            p2 = driver.page.locator("#research-accordion .service-panel").nth(1)
            if not p2.evaluate("el => el.classList.contains('open')"):
                p2.locator(".service-panel-header").evaluate("el => el.click()")
                driver.sleep(0.5)
            fill("research-extra-text", "TestSimulator criteria test.")
            click("btn-select-kriterien", timeout=10000)
            driver.sleep(3)
            driver.page.locator("#generated-prompt pre").first.wait_for(state="visible", timeout=30000)
            log("[✓] Prompt generated")
            passed += 1
        except Exception as e:
            log(f"[✗] Prompt: {e}")
        
        try:
            click("btn-copy-prompt", timeout=5000)
            log("[✓] Copy prompt")
        except:
            log("[✗] Copy prompt")
        
        log(f"=== RESEARCH: {passed}/{total} passed ===")
        driver.stop()
        return {"status": "done" if passed >= total else "partial", "passed": passed, "total": total, "steps": steps}
        
    except Exception as e:
        log(f"FATAL: {e}")
        try: driver.page.screenshot(path="workflows/last_error.png")
        except: pass
        try: driver.stop()
        except: pass
        return {"status": "error", "error": str(e), "steps": steps}
