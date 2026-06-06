"""
ME4 TestSimulator — CLI Interface (click-based)

Provides ``record``, ``replay``, and ``autorun`` commands with i18n support
and structured exit codes for CI integration.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import click

from .i18n import get_text
from .i18n import init as init_i18n

_EXIT_SUCCESS = 0
_EXIT_TEST_FAILED = 1
_EXIT_RUNTIME_ERROR = 2


# ======================================================================
# Main group
# ======================================================================


@click.group()
@click.option(
    "--lang",
    type=click.Choice(["de", "en"]),
    default=None,
    help="Language override (de|en). Default: system default (de).",
)
@click.version_option(
    message="%(prog)s %(version)s",
    package_name="me4-testsimulator",
)
@click.pass_context
def main(ctx: click.Context, lang: str | None) -> None:
    """ME4 TestSimulator — Macro-basierter UI-Test-Simulator.

    Record, replay, and automate browser interactions for ME4 services.

    \b
    Quick start:
      testsimulator record http://localhost:5173
      testsimulator replay macros/my-macro.json
      testsimulator autorun youtube
    """
    ctx.ensure_object(dict)
    ctx.obj["lang"] = lang or "de"
    init_i18n(lang or "de")


# ======================================================================
# record command
# ======================================================================


@main.command()
@click.argument("url", default="http://localhost:5173")
@click.option(
    "--output", "-o",
    default=None,
    help="Output path for the macro JSON (default: macros/macro_YYYYMMDD_HHMMSS.json).",
)
@click.option(
    "--lang",
    type=click.Choice(["de", "en"]),
    default=None,
    help="Language override for this command.",
)
@click.option(
    "--browser", "-b",
    default="chromium",
    type=click.Choice(["chromium", "firefox", "webkit"]),
    help="Browser engine (default: chromium).",
)
@click.option(
    "--headless",
    is_flag=True,
    help="Run browser without visible UI (not recommended for recording).",
)
@click.option(
    "--timeout", "-t",
    type=float,
    default=None,
    help="Maximum recording time in seconds (default: no limit).",
)
@click.pass_context
def record(
    ctx: click.Context,
    url: str,
    output: str | None,
    lang: str | None,
    browser: str,
    headless: bool,
    timeout: float | None,
) -> None:
    """Record user interactions in a browser and save them as a JSON macro.

    Open a browser at URL, interact with the page (click, type, navigate),
    then press Shift+Escape to stop recording. The macro is saved as JSON.

    \b
    Examples:
      testsimulator record http://localhost:5173
      testsimulator record https://example.com -o macros/demo.json
      testsimulator record --browser firefox --headless http://localhost:5173
    """
    from .recorder import RecordSession

    _init_lang(ctx, lang)

    # Generate default output path with timestamp
    if output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"macros/macro_{ts}.json"

    click.echo(f"[TestSimulator] URL: {url}")
    click.echo(f"[TestSimulator] Browser: {browser} (headless={headless})")
    click.echo(
        "[TestSimulator] Interact with the browser, then press Shift+Escape to stop."
    )
    if timeout:
        click.echo(f"[TestSimulator] Timeout: {timeout}s")

    try:
        session = RecordSession(browser=browser, headless=headless)
        session.start_recording(url)
        session.wait_for_stop(timeout=timeout)
        saved = session.save_macro(output)
    except Exception as exc:
        click.echo(f"[TestSimulator] Runtime error: {exc}", err=True)
        sys.exit(_EXIT_RUNTIME_ERROR)

    click.echo(
        get_text("recorder.saved", path=str(saved))
    )
    click.echo(f"[TestSimulator] {len(session._steps)} steps recorded")


# ======================================================================
# replay command
# ======================================================================


@main.command()
@click.argument(
    "macro_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser headless (default: headless) or with visible UI.",
)
@click.option(
    "--screenshots", "-s",
    is_flag=True,
    help="Take a screenshot after every step (stored in screenshots/).",
)
@click.option(
    "--speed",
    type=float,
    default=1.0,
    help="Playback speed factor (1.0 = original speed, 2.0 = double speed).",
)
@click.option(
    "--browser", "-b",
    default="chromium",
    type=click.Choice(["chromium", "firefox", "webkit"]),
    help="Browser engine (default: chromium).",
)
@click.option(
    "--lang",
    type=click.Choice(["de", "en"]),
    default=None,
    help="Language override for this command.",
)
@click.pass_context
def replay(
    ctx: click.Context,
    macro_path: str,
    headless: bool,
    screenshots: bool,
    speed: float,
    browser: str,
    lang: str | None,
) -> None:
    """Replay a recorded macro from a JSON file.

    MACRO_PATH is the path to a previously recorded macro JSON file.

    \b
    Exit codes:
      0 — all steps passed
      1 — assertion failed (test failure)
      2 — runtime error (element not found, timeout, file missing)

    \b
    Examples:
      testsimulator replay macros/my-macro.json
      testsimulator replay macros/test.json --no-headless --screenshots
      testsimulator replay macros/slow.json --speed 2.0
    """
    from .player import MacroPlayer
    from .schema import load_macro

    _init_lang(ctx, lang)

    # Validate speed factor
    if speed <= 0:
        click.echo("[TestSimulator] Error: --speed must be > 0", err=True)
        sys.exit(_EXIT_RUNTIME_ERROR)

    path = Path(macro_path)
    if not path.is_file():
        click.echo(
            get_text("error.file_not_found", path=str(path)), err=True
        )
        sys.exit(_EXIT_RUNTIME_ERROR)

    click.echo(f"[TestSimulator] Loading macro: {path}")

    try:
        macro = load_macro(path)
    except Exception as exc:
        click.echo(
            get_text("error.invalid_macro", error=str(exc)), err=True
        )
        sys.exit(_EXIT_RUNTIME_ERROR)

    click.echo(
        f"[TestSimulator] Macro '{macro['metadata']['name']}' "
        f"({len(macro['steps'])} steps)"
    )
    click.echo(
        f"[TestSimulator] Browser: {browser} "
        f"(headless={headless}, speed={speed}x, screenshots={screenshots})"
    )

    # Apply speed factor to sleep durations in the macro
    if speed != 1.0:
        macro = _apply_speed(macro, speed)

    player = MacroPlayer(
        headless=headless,
        browser=browser,
        screenshots=screenshots,
    )

    try:
        result = player.play(macro)
    except Exception as exc:
        click.echo(f"[TestSimulator] Runtime error: {exc}", err=True)
        sys.exit(_EXIT_RUNTIME_ERROR)

    if result.success:
        click.echo(
            f"[TestSimulator] All {result.steps_executed} steps passed."
        )
        sys.exit(_EXIT_SUCCESS)
    else:
        click.echo(
            f"[TestSimulator] {result.error_count} error(s) "
            f"in {result.steps_executed} steps:",
            err=True,
        )
        for err in result.errors:
            click.echo(
                f"  - Step {err.step_id} ({err.action}): {err.message}",
                err=True,
            )
            if err.screenshot:
                click.echo(f"    Screenshot: {err.screenshot}", err=True)

        # Determine exit code: assertion errors -> 1, runtime errors -> 2
        has_assertion = _has_assertion_error(result.errors)
        sys.exit(_EXIT_TEST_FAILED if has_assertion else _EXIT_RUNTIME_ERROR)


# ======================================================================
# autorun command
# ======================================================================


@main.command()
@click.argument("workflow", default="youtube")
@click.option(
    "--youtube",
    default="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    help="YouTube URL for the SMproducer YouTube workflow.",
)
@click.option(
    "--channel",
    default="technews",
    help="Channel prefix for the SMproducer workflow.",
)
@click.option(
    "--headless",
    is_flag=True,
    help="Run browser without visible UI.",
)
@click.option(
    "--checkpoint",
    is_flag=True,
    help="Auto-resume past the decision point (skip human-in-the-loop pause).",
)
@click.option(
    "--lang",
    type=click.Choice(["de", "en"]),
    default=None,
    help="Language override for this command.",
)
@click.pass_context
def autorun(
    ctx: click.Context,
    workflow: str,
    youtube: str,
    channel: str,
    headless: bool,
    checkpoint: bool,
    lang: str | None,
) -> None:
    """Run SMproducer autorun workflow (YouTube -> Topic -> Decision Point).

    WORKFLOW is the workflow name to execute (currently: 'youtube').

    The workflow runs through: select channel -> new project -> add YouTube
    source -> send to AI -> pause at decision point.

    \b
    Examples:
      testsimulator autorun youtube
      testsimulator autorun youtube --channel mychannel
      testsimulator autorun youtube --checkpoint
    """
    from .autorun import run_youtube_workflow

    _init_lang(ctx, lang)

    if workflow != "youtube":
        click.echo(
            f"[TestSimulator] Unknown workflow: '{workflow}'. "
            f"Available: youtube",
            err=True,
        )
        sys.exit(_EXIT_RUNTIME_ERROR)

    click.echo(get_text("autorun.started"))
    click.echo(f"[TestSimulator] Workflow: {workflow}")
    click.echo(f"[TestSimulator] YouTube: {youtube}")
    click.echo(f"[TestSimulator] Channel: {channel}")

    try:
        ar = run_youtube_workflow(
            youtube_url=youtube,
            channel=channel,
            headless=headless,
        )

        if checkpoint:
            click.echo("[TestSimulator] Checkpoint mode: auto-resuming past decision...")
            ar.step_continue_after_decision()
            ar.stop()
            click.echo(get_text("autorun.resumed"))
            click.echo("[TestSimulator] Workflow completed (checkpoint mode).")
        else:
            click.echo(get_text("autorun.paused"))
            click.echo(
                "[TestSimulator] Workflow paused at decision point. "
                f"State: {ar.state}"
            )
            click.echo(
                "[TestSimulator] Resume programmatically with: "
                "ar.step_continue_after_decision()"
            )
    except Exception as exc:
        click.echo(f"[TestSimulator] Runtime error: {exc}", err=True)
        sys.exit(_EXIT_RUNTIME_ERROR)


# ======================================================================
# Helpers
# ======================================================================


def _init_lang(ctx: click.Context, lang: str | None) -> None:
    """Resolve language from command-level --lang or group-level --lang."""
    lang = lang or ctx.obj.get("lang", "de")
    init_i18n(lang)


def _apply_speed(macro: dict, speed: float) -> dict:
    """Apply playback speed factor to sleep durations in the macro.

    Modifies the macro in place and returns it. Sleep step durations are
    divided by the speed factor.
    """
    for step in macro.get("steps", []):
        if step.get("action") == "sleep":
            if "seconds" in step:
                step["seconds"] = step["seconds"] / speed
            elif "timeout" in step:
                step["timeout"] = step["timeout"] / speed
    return macro


def _has_assertion_error(errors: list) -> bool:
    """Check if any replay errors are assertion failures."""
    for err in errors:
        # Assertion errors from assert_visible / assert_text
        if err.action in ("assert_visible", "assert_text"):
            return True
        # Generic assertion errors in the message
        msg_lower = err.message.lower()
        if "assertionerror" in msg_lower or "assert" in msg_lower:
            return True
    return False


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    main()
