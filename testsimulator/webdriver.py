"""
ME4 TestSimulator — WebDriver
Playwright-based browser automation with robust selectors.
"""

from playwright.sync_api import sync_playwright
import time


class WebDriver:
    """Simple Playwright wrapper for SMproducer testing."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
    
    def start(self, url: str = "http://localhost:5173"):
        """Start browser and navigate to URL."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        return self
    
    def sleep(self, seconds: float):
        time.sleep(seconds)
        return self
    
    def stop(self):
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
