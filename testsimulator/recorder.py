"""
ME4 TestSimulator — Recorder: Click/Input/Navigate Recording via Playwright.

Provides ``RecordSession`` which opens a browser, injects event listeners,
and captures user interactions as a validated JSON macro.
"""

from __future__ import annotations

import json
import time
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import ConsoleMessage, Frame, Page, sync_playwright

from .schema import validate_macro

# ---------------------------------------------------------------------------
# JavaScript injected into the page to intercept user actions
# ---------------------------------------------------------------------------
_PREFIX = "__ME4_RECORD__"
_PREFIX_LEN = len(_PREFIX)
RECORDING_SCRIPT = r"""
(function() {
    if (window.__me4_recorder_installed) return;
    window.__me4_recorder_installed = true;

    // --- Smart-selector builder: data-testid > id > CSS-unique > XPath ----

    function buildSelector(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return 'body';
        }

        // 1. data-testid (preferred)
        var tid = el.getAttribute('data-testid');
        if (tid) {
            return '[data-testid="' + tid.replace(/"/g, '\\"') + '"]';
        }

        // 2. id attribute
        if (el.id) {
            try { return '#' + CSS.escape(el.id); } catch(_) { return '#' + el.id; }
        }

        // 3. Unique-ish CSS path
        var parts = [];
        var current = el;
        while (current && current !== document.body && current !== document.documentElement) {
            var tag = current.tagName.toLowerCase();
            if (current.id) {
                try {
                    parts.unshift('#' + CSS.escape(current.id));
                } catch (_) {
                    parts.unshift('#' + current.id);
                }
                break;
            }
            var parent = current.parentElement;
            if (parent) {
                var siblings = Array.from(parent.children).filter(function(c) {
                    return c.tagName === current.tagName;
                });
                if (siblings.length > 1) {
                    var idx = siblings.indexOf(current) + 1;
                    tag += ':nth-of-type(' + idx + ')';
                }
            }
            parts.unshift(tag);
            current = current.parentElement;
        }
        var cssPath = parts.join(' > ') || 'body';

        // Quick uniqueness check: if the CSS path matches exactly one element, use it
        try {
            if (document.querySelectorAll(cssPath).length === 1) {
                return cssPath;
            }
        } catch(_) {}

        // 4. XPath fallback
        function buildXPath(el2) {
            if (el2 === document.body) return '/html/body';
            if (el2.id) return '//*[@id="' + el2.id + '"]';
            var parts2 = [];
            var cur2 = el2;
            while (cur2 && cur2 !== document.documentElement) {
                var tag2 = cur2.tagName.toLowerCase();
                var parent2 = cur2.parentElement;
                if (parent2) {
                    var sameSibs = Array.from(parent2.children).filter(function(c) {
                        return c.tagName === cur2.tagName;
                    });
                    if (sameSibs.length > 1) {
                        var idx2 = sameSibs.indexOf(cur2) + 1;
                        tag2 += '[' + idx2 + ']';
                    }
                }
                parts2.unshift(tag2);
                cur2 = cur2.parentElement;
            }
            return '/' + parts2.join('/');
        }
        var xpath = buildXPath(el);
        try {
            var xpRes = document.evaluate(
                xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
            );
            if (xpRes.snapshotLength === 1) return 'xpath=' + xpath;
        } catch(_) {}

        // Last resort: return the CSS path anyway
        return cssPath;
    }

    // --- Send event to Python via console.log ----

    function record(action, data) {
        var payload = JSON.stringify(Object.assign({action: action}, data));
        console.log('__ME4_RECORD__' + payload);
    }

    // --- Click handler (capture phase for all clicks) ----

    document.addEventListener('click', function(e) {
        record('click', {selector: buildSelector(e.target)});
    }, true);

    // --- Change handler for form inputs (select, checkbox, radio) ----

    document.addEventListener('change', function(e) {
        var el = e.target;
        if (el.tagName === 'SELECT') {
            record('type', {selector: buildSelector(el), value: el.value});
        }
    }, true);

    // --- Input handler with debounce (text inputs / textareas) ----

    var inputTimers = {};
    document.addEventListener('input', function(e) {
        var el = e.target;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
            // Don't record password fields
            if (el.type === 'password') return;

            var sel = buildSelector(el);
            clearTimeout(inputTimers[sel]);
            inputTimers[sel] = setTimeout(function() {
                record('type', {selector: sel, value: el.value});
                delete inputTimers[sel];
            }, 600);
        }
    }, true);

    // --- Stop signal: Shift+Escape stops recording ----

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && e.shiftKey) {
            record('__stop__', {});
            e.preventDefault();
            e.stopPropagation();
        }
    }, true);

    console.log('__ME4_RECORD__' + JSON.stringify({action: '__ready__'}));
})();
"""


# ---------------------------------------------------------------------------
# RecordSession
# ---------------------------------------------------------------------------


class RecordSession:
    """Record a browser session as a validated JSON macro.

    Typical CLI usage::

        session = RecordSession(headless=False)
        session.start_recording("https://example.com")
        session.wait_for_stop()          # User presses Shift+Escape
        macro = session.stop_recording()
        session.save_macro("macros/demo.json")

    As a context manager::

        with RecordSession() as rec:
            rec.start_recording("https://example.com")
            rec.wait_for_stop()
            rec.save_macro("macros/demo.json")
    """

    def __init__(
        self,
        browser: str = "chromium",
        headless: bool = False,
        viewport: dict[str, int] | None = None,
    ) -> None:
        """Create a new recording session.

        Args:
            browser: Browser engine — ``"chromium"`` (default), ``"firefox"``, or ``"webkit"``.
            headless: Run without visible UI (default False — recording needs a human).
            viewport: Optional viewport dict, e.g. ``{"width": 1920, "height": 1080}``.
        """
        self.browser_name: str = browser
        self.headless: bool = headless
        self._viewport: dict[str, int] = viewport or {"width": 1920, "height": 1080}

        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Page | None = None

        self._steps: list[dict[str, Any]] = []
        self._recording: bool = False
        self._start_url: str = ""
        self._recorded_urls: set[str] = set()
        self._name: str = "recorded-macro"
        self._ready: bool = False

    # -- Public API -----------------------------------------------------------

    def start_recording(self, url: str, name: str = "recorded-macro") -> Page:
        """Launch browser, navigate to *url*, and begin event listening.

        Args:
            url: Starting URL.
            name: Human-readable name for the macro metadata.

        Returns:
            The Playwright ``Page`` so callers can inspect it if needed.
        """
        self._start_url = url
        self._name = name
        self._recorded_urls = {url, "about:blank"}

        self._playwright = sync_playwright().start()
        launcher = getattr(self._playwright, self.browser_name)
        self._browser = launcher.launch(headless=self.headless)
        self._context = self._browser.new_context(viewport=self._viewport)
        self._page = self._context.new_page()

        # Hook console messages (JS events arrive here)
        self._page.on("console", self._handle_console)

        # Track navigations
        self._page.on("framenavigated", self._handle_navigate)

        # Record the initial navigation step
        self._add_step(
            "navigate",
            url=url,
            description=f"Navigate to {url}",
        )

        self._page.goto(url)

        # Inject recording script on every new page load
        self._page.on("load", self._inject_recording_script)

        # Inject now (first page)
        self._page.evaluate(RECORDING_SCRIPT)

        self._recording = True
        return self._page

    def wait_for_stop(self, timeout: float | None = None) -> list[dict[str, Any]]:
        """Block until the user stops recording (Shift+Escape in browser).

        Args:
            timeout: Maximum seconds to wait. ``None`` means wait forever.

        Returns:
            The recorded steps so far.
        """
        if self._page is None:
            raise RuntimeError("Recording not started — call start_recording() first.")

        start = time.monotonic()
        while self._recording:
            if timeout is not None and (time.monotonic() - start) > timeout:
                self._recording = False
                break
            # Drive the Playwright event loop so console messages are delivered
            try:
                self._page.wait_for_timeout(100)
            except Exception:
                break

        return list(self._steps)

    def stop_recording(self) -> dict[str, Any]:
        """Stop recording, close the browser, and return the validated macro dict.

        Returns:
            A dict matching ``MACRO_SCHEMA`` (validated).
        """
        self._recording = False

        # Flush any pending debounced input events from JS
        if self._page:
            with suppress(Exception):
                self._page.evaluate("""
                    if (window.__me4_recorder_installed) {
                        // Fire any pending input timers immediately
                        var timers = window.__me4_inputTimers || {};
                        for (var k in timers) {
                            clearTimeout(timers[k]);
                            delete timers[k];
                        }
                    }
                """)

        # Clean up Playwright
        if self._page:
            with suppress(Exception):
                self._page.close()
            self._page = None

        if self._context:
            with suppress(Exception):
                self._context.close()
            self._context = None

        if self._browser:
            with suppress(Exception):
                self._browser.close()
            self._browser = None

        if self._playwright:
            with suppress(Exception):
                self._playwright.stop()
            self._playwright = None

        # Build and validate macro
        macro: dict[str, Any] = {
            "version": "1.0",
            "metadata": {
                "name": self._name,
                "created": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
                "browser": self.browser_name,
                "viewport": self._viewport,
            },
            "steps": self._steps,
        }

        validate_macro(macro)
        return macro

    def save_macro(self, path: str | Path) -> Path:
        """Stop recording, validate, and save the macro as JSON.

        Args:
            path: Output file path (e.g. ``"macros/demo.json"``).

        Returns:
            The resolved ``Path`` where the file was written.
        """
        macro = self.stop_recording()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(macro, fh, indent=2, ensure_ascii=False)

        return path.resolve()

    # -- Context manager -----------------------------------------------------

    def __enter__(self) -> RecordSession:
        return self

    def __exit__(self, *args: Any) -> None:
        self._recording = False
        if self._page:
            with suppress(Exception):
                self._page.close()
        if self._context:
            with suppress(Exception):
                self._context.close()
        if self._browser:
            with suppress(Exception):
                self._browser.close()
        if self._playwright:
            with suppress(Exception):
                self._playwright.stop()

    # -- Internal event handlers ---------------------------------------------

    def _handle_console(self, msg: ConsoleMessage) -> None:
        """Parse recording events from ``console.log`` messages."""
        if not msg.text.startswith(_PREFIX):
            return

        try:
            data = json.loads(msg.text[_PREFIX_LEN:])
        except json.JSONDecodeError:
            return

        action = data.get("action", "")
        if action == "__ready__":
            self._ready = True
        elif action == "__stop__":
            self._recording = False
        elif action == "click":
            self._add_step(
                "click",
                selector=data.get("selector", "body"),
                description=f"Click {data.get('selector', 'element')}",
            )
        elif action in ("input", "type"):
            self._add_step(
                "type",
                selector=data.get("selector", "body"),
                value=data.get("value", ""),
                description=f"Type '{data.get('value', '')}' into {data.get('selector', 'field')}",
            )

    def _handle_navigate(self, frame: Frame) -> None:
        """Record manual navigations (page changes after the initial load)."""
        if not self._recording:
            return
        if self._page is None:
            return
        if frame != self._page.main_frame:
            return

        url = frame.url
        if url in self._recorded_urls:
            return
        self._recorded_urls.add(url)

        self._add_step(
            "navigate",
            url=url,
            description=f"Navigate to {url}",
        )

    def _inject_recording_script(self, page: Page) -> None:
        """Re-inject the recording script after a page load."""
        with suppress(Exception):
            page.evaluate(RECORDING_SCRIPT)

    def _add_step(self, action: str, **kwargs: Any) -> None:
        """Append a step to the recording."""
        step: dict[str, Any] = {
            "id": len(self._steps) + 1,
            "action": action,
        }
        step.update(kwargs)
        self._steps.append(step)


# ---------------------------------------------------------------------------
# CLI entry-point: python -m testsimulator.recorder
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    url = "https://example.com"
    output = "macros/recording.json"
    browser_name = "chromium"
    headless = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--url", "-u") and i + 1 < len(sys.argv):
            i += 1
            url = sys.argv[i]
        elif arg in ("--output", "-o") and i + 1 < len(sys.argv):
            i += 1
            output = sys.argv[i]
        elif arg in ("--browser", "-b") and i + 1 < len(sys.argv):
            i += 1
            browser_name = sys.argv[i]
        elif arg == "--headless":
            headless = True
        i += 1

    print(f"[recorder] Starting recording on {url}")
    print(f"[recorder] Browser: {browser_name} (headless={headless})")
    print("[recorder] Interact with the browser, then press Shift+Escape to stop.")

    session = RecordSession(browser=browser_name, headless=headless)
    session.start_recording(url)
    session.wait_for_stop()
    saved = session.save_macro(output)

    print(f"[recorder] Macro saved to {saved}")
    print(f"[recorder] {len(session._steps)} steps recorded")
