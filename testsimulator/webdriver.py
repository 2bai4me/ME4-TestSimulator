"""
ME4 TestSimulator — WebDriver: Playwright Browser Lifecycle.

Provides module-level functions for browser management and a WebDriver
class for element-based interaction. Supports Chromium (default),
Firefox, and WebKit.
"""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Literal

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_playwright: Playwright | None = None
_browser: Browser | None = None
_context: BrowserContext | None = None
_page: Page | None = None

BrowserName = Literal["chromium", "firefox", "webkit"]


def launch_browser(
    headless: bool = True,
    browser: BrowserName = "chromium",
    viewport: dict | None = None,
) -> tuple[Browser, BrowserContext, Page]:
    """Launch a Playwright browser and return (browser, context, page).

    Args:
        headless: Run browser without visible UI (default True).
        browser: Browser engine — ``"chromium"`` (default), ``"firefox"``, or ``"webkit"``.
        viewport: Optional viewport dict, e.g. ``{"width": 1920, "height": 1080}``.

    Returns:
        Tuple of ``(Browser, BrowserContext, Page)``.
    """
    global _playwright, _browser, _context, _page

    _playwright = sync_playwright().start()

    launcher = getattr(_playwright, browser)
    _browser = launcher.launch(headless=headless)

    context_kwargs: dict = {}
    if viewport:
        context_kwargs["viewport"] = viewport
    _context = _browser.new_context(**context_kwargs)

    _page = _context.new_page()

    return _browser, _context, _page


def new_page() -> Page:
    """Open a new page in the existing browser context.

    Returns:
        A new Playwright ``Page``.
    """
    global _page, _context
    if _context is None:
        raise RuntimeError("No browser context — call launch_browser() first.")
    _page = _context.new_page()
    return _page


def close_browser() -> None:
    """Close browser, context, and stop Playwright cleanly."""
    global _playwright, _browser, _context, _page

    if _page:
        with suppress(Exception):
            _page.close()
        _page = None

    if _context:
        with suppress(Exception):
            _context.close()
        _context = None

    if _browser:
        with suppress(Exception):
            _browser.close()
        _browser = None

    if _playwright:
        with suppress(Exception):
            _playwright.stop()
        _playwright = None


def get_page() -> Page | None:
    """Return the current active page, or None."""
    return _page


# ---------------------------------------------------------------------------
# WebDriver class — kept for backward compatibility with autorun.py
# ---------------------------------------------------------------------------
class WebDriver:
    """Browser automation wrapper using Playwright (class-based API)."""

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self.browser: Browser | None = None
        self.page: Page | None = None

    def start(self, url: str = "http://localhost:5173") -> WebDriver:
        """Start browser and navigate to *url*."""
        browser, _ctx, page = launch_browser(headless=self.headless)
        self.browser = browser
        self.page = page
        page.goto(url)
        return self

    # -- Element interaction helpers ------------------------------------------

    def click(self, selector: str, timeout: float = 10.0) -> WebDriver:
        el = self.page.wait_for_selector(selector, timeout=timeout * 1000)
        el.click()
        return self

    def click_text(self, text: str, timeout: float = 10.0) -> WebDriver:
        el = self.page.get_by_text(text, exact=True).first
        el.wait_for(timeout=timeout * 1000)
        el.click()
        return self

    def type(self, selector: str, text: str, timeout: float = 10.0) -> WebDriver:
        el = self.page.wait_for_selector(selector, timeout=timeout * 1000)
        el.fill(text)
        return self

    def type_into(self, placeholder: str, text: str, timeout: float = 10.0) -> WebDriver:
        el = self.page.get_by_placeholder(placeholder).first
        el.wait_for(timeout=timeout * 1000)
        el.fill(text)
        return self

    def get_text(self, selector: str) -> str:
        return self.page.text_content(selector) or ""

    def wait_for(self, selector: str, timeout: float = 10.0) -> WebDriver:
        self.page.wait_for_selector(selector, timeout=timeout * 1000)
        return self

    def wait_for_text(self, text: str, timeout: float = 10.0) -> WebDriver:
        self.page.get_by_text(text).first.wait_for(timeout=timeout * 1000)
        return self

    def is_visible(self, selector: str) -> bool:
        el = self.page.query_selector(selector)
        return el is not None and el.is_visible()

    def screenshot(self, path: str) -> WebDriver:
        self.page.screenshot(path=path)
        return self

    def sleep(self, seconds: float) -> WebDriver:
        time.sleep(seconds)
        return self

    def stop(self) -> WebDriver:
        close_browser()
        self.browser = None
        self.page = None
        return self


# ---------------------------------------------------------------------------
# CLI entry-point: python -m testsimulator.webdriver
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    browser_name: BrowserName = "chromium"
    if len(sys.argv) > 1 and sys.argv[1] in ("chromium", "firefox", "webkit"):
        browser_name = sys.argv[1]  # type: ignore[assignment]

    print(f"[webdriver] Launching {browser_name} (headless)...")
    browser, context, page = launch_browser(headless=True, browser=browser_name)
    print(f"[webdriver] Browser launched: {browser}")

    page.goto("data:text/html,<h1>ME4 TestSimulator WebDriver OK</h1>")
    print(f"[webdriver] Page title: {page.title()}")

    close_browser()
    print("[webdriver] Browser closed cleanly.")
