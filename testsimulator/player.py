"""
ME4 TestSimulator — Player: JSON Macro Execution with Auto-Wait + Error Handling.

Provides ``MacroPlayer`` which takes a validated macro, opens a headless (or visible)
browser, and replays every step. On failure it retries (up to 3x), captures a
screenshot, and continues — collecting errors into a ``PlayResult``.
"""

from __future__ import annotations

import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .schema import validate_macro

# ---------------------------------------------------------------------------
# PlayResult
# ---------------------------------------------------------------------------


@dataclass
class PlayError:
    """A single step-level error captured during replay."""

    step_id: int
    action: str
    message: str
    screenshot: str | None = None


@dataclass
class PlayResult:
    """Result of a ``MacroPlayer.play()`` call.

    Attributes:
        success: ``True`` if all steps completed without errors.
        steps_executed: Number of steps that were attempted (all of them).
        errors: List of ``PlayError`` entries for each failed step.
    """

    success: bool
    steps_executed: int
    errors: list[PlayError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)


# ---------------------------------------------------------------------------
# MacroPlayer
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds, exponential backoff: base * 2^attempt


class MacroPlayer:
    """Replay a recorded/json macro with full error handling.

    Typical usage::

        macro = load_macro("macros/test-recording.json")
        player = MacroPlayer(headless=True, screenshots=False)
        result = player.play(macro)
        print(result)
    """

    def __init__(
        self,
        headless: bool = True,
        browser: str = "chromium",
        viewport: dict[str, int] | None = None,
        screenshots: bool = False,
        screenshot_dir: str | Path = "screenshots",
    ) -> None:
        """Create a new player session.

        Args:
            headless: Run browser without visible UI (default ``True``).
            browser: Browser engine — ``"chromium"``, ``"firefox"``, or ``"webkit"``.
            viewport: Optional ``{"width": N, "height": N}`` dict.
            screenshots: If ``True``, take a screenshot after **every** step
                (not just on error).
            screenshot_dir: Directory for screenshot output. Created automatically.
        """
        self.headless: bool = headless
        self.browser_name: str = browser
        self._viewport: dict[str, int] = viewport or {"width": 1920, "height": 1080}
        self._screenshots_enabled: bool = screenshots
        self._screenshot_dir: Path = Path(screenshot_dir)

        self._playwright: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # -- Public API -----------------------------------------------------------

    def play(self, macro: dict[str, Any]) -> PlayResult:
        """Execute every step in *macro* and return a ``PlayResult``.

        Args:
            macro: A validated macro dictionary (see ``MACRO_SCHEMA``).

        Returns:
            ``PlayResult`` with success flag and any per-step errors.
        """
        validate_macro(macro)  # defensive: re-validate before execution

        errors: list[PlayError] = []
        steps: list[dict[str, Any]] = macro.get("steps", [])

        print(f"[player] Macro '{macro['metadata']['name']}' — {len(steps)} step(s)")
        print(f"[player] Browser: {self.browser_name} (headless={self.headless})")

        self._setup_screenshot_dir()
        self._launch()

        try:
            for step in steps:
                step_id: int = step["id"]
                action: str = step["action"]
                desc: str = step.get("description", f"Step {step_id}: {action}")

                print(f"  [{step_id}/{len(steps)}] {action} — {desc}")

                try:
                    self._execute_step_with_retry(step)
                except Exception as exc:
                    err = self._capture_error(step_id, action, exc)
                    errors.append(err)
                    print(f"    [ERROR] {err.message}")

                # Optional screenshot after every step
                if self._screenshots_enabled and self._page:
                    with suppress(Exception):
                        path = self._screenshot_dir / f"step_{step_id:03d}_{action}.png"
                        self._page.screenshot(path=str(path))

        finally:
            self._shutdown()

        total = len(steps)
        print(
            f"[player] Done: {total - len(errors)}/{total} steps OK, "
            f"{len(errors)} error(s)."
        )
        return PlayResult(
            success=(len(errors) == 0),
            steps_executed=total,
            errors=errors,
        )

    # -- Step execution with retry --------------------------------------------

    def _execute_step_with_retry(self, step: dict[str, Any]) -> None:
        """Run a single step with up to ``MAX_RETRIES`` retries on error.

        Uses exponential backoff between attempts.
        """
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._execute_one_step(step)
                return  # success — done
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                    print(f"    [retry {attempt}/{MAX_RETRIES}] {exc} — waiting {delay:.1f}s")
                    time.sleep(delay)

        # All retries exhausted
        raise last_exc  # type: ignore[misc]

    def _execute_one_step(self, step: dict[str, Any]) -> None:
        """Dispatch a single step to the correct handler based on ``action``."""
        if self._page is None:
            raise RuntimeError("Browser page is not available.")

        action: str = step["action"]
        page = self._page

        if action == "navigate":
            url: str = step.get("url", "")
            if not url:
                raise ValueError("navigate step missing 'url' field")
            page.goto(url, timeout=30000)
            # Auto-wait for network idle after navigation
            with suppress(Exception):
                page.wait_for_load_state("networkidle", timeout=15000)

        elif action == "click":
            selector: str = step.get("selector", "")
            if not selector:
                raise ValueError("click step missing 'selector' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            page.wait_for_selector(selector, timeout=timeout)
            page.click(selector, timeout=timeout)

        elif action == "click_text":
            text: str = step.get("text", "")
            if not text:
                raise ValueError("click_text step missing 'text' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            locator = page.get_by_text(text, exact=True).first
            locator.wait_for(timeout=timeout)
            locator.click(timeout=timeout)

        elif action == "type":
            selector = step.get("selector", "")
            value: str = step.get("value", step.get("text", ""))
            if not selector:
                raise ValueError("type step missing 'selector' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            page.wait_for_selector(selector, timeout=timeout)
            page.fill(selector, value, timeout=timeout)

        elif action == "type_into":
            placeholder: str = step.get("placeholder", "")
            text = step.get("text", step.get("value", ""))
            if not placeholder:
                raise ValueError("type_into step missing 'placeholder' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            locator = page.get_by_placeholder(placeholder).first
            locator.wait_for(timeout=timeout)
            locator.fill(text, timeout=timeout)

        elif action == "wait":
            selector = step.get("selector", "")
            if not selector:
                raise ValueError("wait step missing 'selector' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            page.wait_for_selector(selector, timeout=timeout)

        elif action == "wait_for_text":
            text = step.get("text", "")
            if not text:
                raise ValueError("wait_for_text step missing 'text' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            locator = page.get_by_text(text).first
            locator.wait_for(timeout=timeout)

        elif action == "screenshot":
            path = step.get("path", "")
            if not path:
                path = str(self._screenshot_dir / f"screenshot_{step['id']:03d}.png")
            page.screenshot(path=path, full_page=True)

        elif action == "assert_visible":
            selector = step.get("selector", "")
            if not selector:
                raise ValueError("assert_visible step missing 'selector' field")
            timeout = (step.get("timeout", 5.0) or 5.0) * 1000
            el = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if el is None or not el.is_visible():
                raise AssertionError(f"Element '{selector}' is not visible")

        elif action == "assert_text":
            text = step.get("text", "")
            if not text:
                raise ValueError("assert_text step missing 'text' field")
            # Check both specific selector text and full page content
            selector = step.get("selector", "")
            if selector:
                content = page.text_content(selector, timeout=10000) or ""
            else:
                content = page.content()
            if text not in content:
                raise AssertionError(f"Text '{text[:80]}' not found on page")

        elif action == "sleep":
            seconds: float = step.get("seconds", step.get("timeout", 1.0)) or 1.0
            time.sleep(seconds)

        elif action == "hover":
            selector = step.get("selector", "")
            if not selector:
                raise ValueError("hover step missing 'selector' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            page.wait_for_selector(selector, timeout=timeout)
            page.hover(selector, timeout=timeout)

        elif action == "select_option":
            selector = step.get("selector", "")
            value = step.get("value", "")
            if not selector:
                raise ValueError("select_option step missing 'selector' field")
            timeout = (step.get("timeout", 10.0) or 10.0) * 1000
            page.wait_for_selector(selector, timeout=timeout)
            page.select_option(selector, value, timeout=timeout)

        elif action == "press_key":
            key: str = step.get("key", "")
            if not key:
                raise ValueError("press_key step missing 'key' field")
            page.keyboard.press(key)

        elif action == "scroll":
            direction: str = step.get("direction", "down")
            amount: int = 300  # default scroll amount
            if direction == "down":
                page.evaluate(f"window.scrollBy(0, {amount})")
            else:
                page.evaluate(f"window.scrollBy(0, -{amount})")

        else:
            raise ValueError(f"Unknown action: '{action}'")

    # -- Error capture --------------------------------------------------------

    def _capture_error(self, step_id: int, action: str, exc: Exception) -> PlayError:
        """Take a failure screenshot and return a ``PlayError``."""
        screenshot_path: str | None = None
        if self._page:
            with suppress(Exception):
                ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                path = self._screenshot_dir / f"error_step{step_id:03d}_{action}_{ts}.png"
                self._page.screenshot(path=str(path))
                screenshot_path = str(path)

        return PlayError(
            step_id=step_id,
            action=action,
            message=f"Step {step_id} ({action}): {exc}",
            screenshot=screenshot_path,
        )

    # -- Browser lifecycle ----------------------------------------------------

    def _launch(self) -> None:
        """Start Playwright, launch browser, and open a page."""
        self._playwright = sync_playwright().start()
        launcher = getattr(self._playwright, self.browser_name)
        self._browser = launcher.launch(headless=self.headless)
        self._context = self._browser.new_context(viewport=self._viewport)
        self._page = self._context.new_page()

    def _shutdown(self) -> None:
        """Close browser, context, and stop Playwright cleanly."""
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

    def _setup_screenshot_dir(self) -> None:
        """Ensure the screenshot directory exists."""
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def play_macro(
    macro: dict[str, Any],
    headless: bool = True,
    browser: str = "chromium",
    screenshots: bool = False,
) -> PlayResult:
    """One-liner: load & replay a macro with sensible defaults.

    Args:
        macro: Validated macro dict (from ``schema.load_macro``).
        headless: Run headless (default ``True``).
        browser: Browser engine (``chromium``, ``firefox``, ``webkit``).
        screenshots: Capture screenshot after every step.

    Returns:
        ``PlayResult``.
    """
    player = MacroPlayer(headless=headless, browser=browser, screenshots=screenshots)
    return player.play(macro)


# ---------------------------------------------------------------------------
# CLI entry-point: python -m testsimulator.player
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ME4 TestSimulator — Macro Player")
    parser.add_argument(
        "file", nargs="?", default="macros/test-recording.json",
        help="Macro JSON file to replay (default: macros/test-recording.json)",
    )
    parser.add_argument(
        "--headless", action="store_true", default=True,
        help="Run browser headless (default: True)",
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Show browser UI",
    )
    parser.add_argument(
        "--browser", "-b", default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser engine (default: chromium)",
    )
    parser.add_argument(
        "--screenshots", "-s", action="store_true",
        help="Take screenshot after every step",
    )

    args = parser.parse_args()

    headless = not args.no_headless

    from .schema import load_macro

    path = Path(args.file)
    if not path.is_file():
        print(f"[player] File not found: {path}")
        sys.exit(1)

    macro = load_macro(path)
    result = play_macro(
        macro,
        headless=headless,
        browser=args.browser,
        screenshots=args.screenshots,
    )

    if not result.success:
        print(f"\n[player] {result.error_count} error(s):")
        for err in result.errors:
            print(f"  - Step {err.step_id} ({err.action}): {err.message}")
            if err.screenshot:
                print(f"    Screenshot: {err.screenshot}")
        sys.exit(1)
