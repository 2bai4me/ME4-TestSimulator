"""
SMproducer Test via PyAutoGUI — screen-position based automation.
Falls Playwright-Selektoren Probleme machen, PyAutoGUI als Fallback.
"""

import pyautogui as pg
import time

pg.FAILSAFE = True
pg.PAUSE = 0.1


def run_smproducer_test_pyautogui():
    """
    SMproducer Workflow via screen automation.
    Browser must be open at http://localhost:5173, maximized.
    """
    steps = []
    def log(msg):
        print(f"[TestSimulator] {msg}")
        steps.append(msg)
    
    try:
        log("Starting PyAutoGUI workflow")
        
        # Step 1: Click "+ New Project" - approximately at position
        # The button is in the main content area, below channel selector
        pg.click(600, 350)  # Approximate position of "+ New Project"
        time.sleep(2)
        log("New project clicked")
        
        # Step 2: Find and click "YouTube (URL)" tab using image recognition
        # First scroll down to see source tabs
        pg.scroll(-200)
        time.sleep(0.5)
        
        # Click where "Source Text" section should be
        pg.click(400, 600)  # Approximate Source Text area
        time.sleep(0.5)
        
        # Click YouTube tab - it's one of the source type options
        pg.click(480, 650)  # Approximate YouTube tab position
        time.sleep(1)
        log("YouTube tab selected")
        
        # Step 3: Type YouTube URL
        pg.click(500, 750)  # Click URL input field
        time.sleep(0.3)
        pg.hotkey('ctrl', 'a')  # Select all
        pg.typewrite("https://www.youtube.com/watch?v=dQw4w9WgXcQ", interval=0.02)
        time.sleep(0.5)
        log("YouTube URL entered")
        
        # Step 4: Click "Hinzufügen"
        pg.press('tab')
        pg.press('enter')
        time.sleep(4)
        log("Video added")
        
        # Step 5: Click "Analyse starten"
        pg.scroll(-300)
        time.sleep(0.5)
        pg.click(500, 900)  # Approximate analyze button position
        time.sleep(6)
        log("Analysis started")
        
        # Step 6: Pick a result (scroll to results area)
        pg.scroll(-500)
        time.sleep(1)
        pg.click(400, 1000)  # Click first result
        time.sleep(1)
        log("Result selected")
        
        # Step 7: Project Start section
        pg.scroll(-300)
        time.sleep(0.5)
        pg.click(500, 1100)  # Project Start area
        time.sleep(1)
        log("Project Start")
        
        # Step 8: "Beschreibung erstellen"
        pg.click(600, 1200)
        time.sleep(3)
        log("Description created")
        
        # Step 9: "Dienst abschließen"
        pg.click(700, 1300)
        time.sleep(2)
        log("Service completed")
        
        return {"status": "done", "steps": steps}
        
    except Exception as e:
        log(f"ERROR: {e}")
        return {"status": "error", "error": str(e), "steps": steps}
