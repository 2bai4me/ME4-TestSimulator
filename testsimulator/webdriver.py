"""
ME4 TestSimulator — Web Element Interaction Layer
Uses Playwright for reliable element-based automation.
"""

from playwright.sync_api import sync_playwright, Page, Browser
from typing import Optional
import time

class WebDriver:
    """Browser automation wrapper using Playwright."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    def start(self, url: str = "http://localhost:5173"):
        """Start browser and navigate to URL."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.goto(url)
        return self
    
    def click(self, selector: str, timeout: float = 10.0):
        """Click an element by CSS/text selector."""
        el = self.page.wait_for_selector(selector, timeout=timeout * 1000)
        el.click()
        return self
    
    def click_text(self, text: str, timeout: float = 10.0):
        """Click an element containing exact text."""
        el = self.page.get_by_text(text, exact=True).first
        el.wait_for(timeout=timeout * 1000)
        el.click()
        return self
    
    def type(self, selector: str, text: str, timeout: float = 10.0):
        """Type text into an input field."""
        el = self.page.wait_for_selector(selector, timeout=timeout * 1000)
        el.fill(text)
        return self
    
    def type_into(self, placeholder: str, text: str, timeout: float = 10.0):
        """Type into input by placeholder text."""
        el = self.page.get_by_placeholder(placeholder).first
        el.wait_for(timeout=timeout * 1000)
        el.fill(text)
        return self
    
    def get_text(self, selector: str) -> str:
        """Get text content of an element."""
        return self.page.text_content(selector) or ""
    
    def wait_for(self, selector: str, timeout: float = 10.0):
        """Wait for an element to appear."""
        self.page.wait_for_selector(selector, timeout=timeout * 1000)
        return self
    
    def wait_for_text(self, text: str, timeout: float = 10.0):
        """Wait for text to appear on page."""
        self.page.get_by_text(text).first.wait_for(timeout=timeout * 1000)
        return self
    
    def is_visible(self, selector: str) -> bool:
        """Check if element is visible."""
        el = self.page.query_selector(selector)
        return el is not None and el.is_visible()
    
    def screenshot(self, path: str):
        """Take a screenshot."""
        self.page.screenshot(path=path)
        return self
    
    def sleep(self, seconds: float):
        """Wait for human-like delay."""
        time.sleep(seconds)
        return self
    
    def stop(self):
        """Close browser and cleanup."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
