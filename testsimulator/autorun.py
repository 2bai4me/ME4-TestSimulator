"""
SMproducer Test Workflows
Tester role: automated end-to-end UI testing via Playwright.
"""

from .webdriver import WebDriver


def run_smproducer_test(youtube_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                         headless: bool = False):
    """
    LUYB Channel → New Project → YouTube URL → Analyze → 
    Pick Result → Project Start → Create Description → Complete Service
    """
    driver = WebDriver(headless=headless)
    steps = []
    
    def log(msg):
        print(f"[TestSimulator] {msg}")
        steps.append(msg)
    
    try:
        driver.start("http://localhost:5173")
        driver.sleep(3)
        log("Page loaded: SMproducer")
        
        # Step 1: Click "+ New Project"
        btn = driver.page.get_by_text("+ New Project").first
        btn.wait_for(state="visible", timeout=10000)
        btn.click()
        driver.sleep(2)
        log("New project created")
        
        # Step 2: Click "YouTube (URL)" tab in Source Text section
        driver.sleep(1)
        # Scroll to source text area first
        driver.page.evaluate("window.scrollTo(0, 400)")
        driver.sleep(0.5)
        clicked = False
        # Try to find the YouTube tab specifically in source-type tabs
        for sel in [
            "label:has-text('YouTube (URL)'):visible",
            "button:has-text('YouTube'):visible",
            "[data-tab='youtube']",
        ]:
            try:
                el = driver.page.locator(sel).first
                if el.is_visible():
                    el.click(timeout=3000)
                    clicked = True
                    break
            except:
                continue
        if not clicked:
            # Last resort: find the label and click its parent container
            el = driver.page.locator("label").filter(has_text="YouTube (URL)").first
            el.evaluate("el => el.click()")
        driver.sleep(1)
        log("YouTube tab selected")
        
        # Step 3: Type YouTube URL
        # Find the YouTube URL input field
        yt_input = driver.page.locator('input[placeholder*="youtube"], input[placeholder*="www.youtube"], input[placeholder*="watch"]').first
        try:
            yt_input.wait_for(state="visible", timeout=5000)
        except:
            # Alternative: find any visible input near YouTube text
            yt_input = driver.page.locator("input").filter(has_not=driver.page.locator("[type='hidden']")).first
        yt_input.fill(youtube_url)
        driver.sleep(0.5)
        log(f"YouTube URL: {youtube_url}")
        
        # Step 4: Click "Hinzufügen" / "Add"
        add_btn = driver.page.get_by_text("Hinzufügen").first
        try:
            add_btn.wait_for(state="visible", timeout=5000)
        except:
            add_btn = driver.page.locator("button:has-text('Add'), button:has-text('Hinzufügen')").first
        add_btn.click()
        driver.sleep(4)
        log("YouTube video added")
        
        # Step 5: Click "Analyse starten" / "Start Analysis"
        analyze_btn = driver.page.locator("button:has-text('Analyse'), button:has-text('Analysis')").first
        try:
            analyze_btn.wait_for(state="visible", timeout=10000)
        except:
            analyze_btn = driver.page.get_by_text("Analyse starten").first
        analyze_btn.click()
        driver.sleep(6)
        log("Analysis started")
        
        # Step 6: Pick a result card
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(1)
        cards = driver.page.locator("[class*='result'], [class*='chapter'], .card, .result-card").all()
        if cards:
            cards[0].click()
            log("Result card selected")
        else:
            log("No result cards - skipping")
        
        # Step 7: Project Start section
        driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        driver.sleep(0.5)
        ps_section = driver.page.locator("text=Project Start, text=Projektstart").first
        try:
            ps_section.click()
        except:
            pass
        driver.sleep(1)
        log("Project Start section")
        
        # Step 8: "Beschreibung erstellen" / "Create Description"
        desc_btn = driver.page.locator("button:has-text('Beschreibung'), button:has-text('Description')").first
        try:
            desc_btn.wait_for(state="visible", timeout=10000)
        except:
            desc_btn = driver.page.get_by_text("Beschreibung erstellen").first
        desc_btn.click()
        driver.sleep(3)
        log("Description created")
        
        # Step 9: "Dienst abschließen" / "Complete Service"
        complete_btn = driver.page.locator("button:has-text('abschließen'), button:has-text('Complete')").first
        try:
            complete_btn.wait_for(state="visible", timeout=10000)
        except:
            complete_btn = driver.page.get_by_text("Dienst abschließen").first
        complete_btn.click()
        driver.sleep(2)
        log("Service completed")
        
        driver.sleep(2)
        driver.stop()
        return {"status": "done", "steps": steps}
        
    except Exception as e:
        log(f"ERROR: {e}")
        try:
            driver.page.screenshot(path="workflows/last_error.png")
        except:
            pass
        try:
            driver.stop()
        except:
            pass
        return {"status": "error", "error": str(e), "steps": steps}
