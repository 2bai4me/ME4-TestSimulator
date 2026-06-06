"""
ME4 TestSimulator — CLI Interface
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="ME4 TestSimulator")
    sub = parser.add_subparsers(dest="command")

    # ---- record command ---------------------------------------------------

    record = sub.add_parser("record", help="Record a new macro")
    record.add_argument("--url", "-u", default="http://localhost:5173",
                        help="Starting URL (default: http://localhost:5173)")
    record.add_argument("--output", "-o", default="macros/recording.json",
                        help="Output path for the macro JSON (default: macros/recording.json)")
    record.add_argument("--name", "-n", default="recorded-macro",
                        help="Macro name for metadata (default: recorded-macro)")
    record.add_argument("--browser", "-b", default="chromium",
                        choices=["chromium", "firefox", "webkit"],
                        help="Browser engine (default: chromium)")
    record.add_argument("--headless", action="store_true",
                        help="Run browser without UI (not recommended for recording)")
    record.add_argument("--timeout", "-t", type=float, default=None,
                        help="Max recording time in seconds (default: no limit)")

    # ---- play command -----------------------------------------------------

    play = sub.add_parser("play", help="Replay a recorded macro")
    play.add_argument("file", help="Macro JSON file to replay")
    play.add_argument("--headless", action="store_true", default=True,
                      help="Run browser headless (default: True)")
    play.add_argument("--no-headless", action="store_true",
                      help="Show browser UI (overrides --headless)")
    play.add_argument("--browser", "-b", default="chromium",
                      choices=["chromium", "firefox", "webkit"],
                      help="Browser engine (default: chromium)")
    play.add_argument("--screenshots", "-s", action="store_true",
                      help="Take a screenshot after every step")

    # ---- autorun command --------------------------------------------------

    autorun = sub.add_parser("autorun", help="Run SMproducer autorun workflow")
    autorun.add_argument("--youtube", default="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                         help="YouTube URL")
    autorun.add_argument("--channel", default="technews", help="Channel prefix")
    autorun.add_argument("--headless", action="store_true", help="Run browser headless")

    args = parser.parse_args()

    if args.command == "record":
        from .recorder import RecordSession

        print(f"[TestSimulator] Recording on {args.url}")
        print(f"[TestSimulator] Browser: {args.browser} (headless={args.headless})")
        print("[TestSimulator] Interact with the browser, then press Shift+Escape to stop.")
        if args.timeout:
            print(f"[TestSimulator] Timeout: {args.timeout}s")

        session = RecordSession(
            browser=args.browser,
            headless=args.headless,
        )
        session.start_recording(args.url, name=args.name)
        session.wait_for_stop(timeout=args.timeout)
        saved = session.save_macro(args.output)

        print(f"[TestSimulator] Recording saved to {saved}")
        print(f"[TestSimulator] {len(session._steps)} steps recorded")

    elif args.command == "play":
        from .player import MacroPlayer
        from .schema import load_macro

        headless = not getattr(args, "no_headless", False)

        print(f"[TestSimulator] Playing macro: {args.file}")
        macro = load_macro(args.file)
        print(f"[TestSimulator] Macro '{macro['metadata']['name']}' "
              f"({len(macro['steps'])} steps)")

        player = MacroPlayer(
            headless=headless,
            browser=args.browser,
            screenshots=args.screenshots,
        )
        result = player.play(macro)

        if result.success:
            print(f"[TestSimulator] All {result.steps_executed} steps passed.")
        else:
            print(f"[TestSimulator] {result.error_count} error(s) "
                  f"in {result.steps_executed} steps:")
            for err in result.errors:
                print(f"  - Step {err.step_id} ({err.action}): {err.message}")
                if err.screenshot:
                    print(f"    Screenshot: {err.screenshot}")

    elif args.command == "autorun":
        from .autorun import run_youtube_workflow
        ar = run_youtube_workflow(
            youtube_url=args.youtube,
            channel=args.channel,
            headless=args.headless,
        )
        print(f"[TestSimulator] Workflow paused at decision point. State: {ar.state}")
        print("[TestSimulator] Call ar.step_continue_after_decision() to resume.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
