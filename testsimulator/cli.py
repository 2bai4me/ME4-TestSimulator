"""
ME4 TestSimulator — CLI Interface
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="ME4 TestSimulator")
    sub = parser.add_subparsers(dest="command")
    
    # autorun command
    autorun = sub.add_parser("autorun", help="Run SMproducer autorun workflow")
    autorun.add_argument("--youtube", default="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                         help="YouTube URL")
    autorun.add_argument("--channel", default="technews", help="Channel prefix")
    autorun.add_argument("--headless", action="store_true", help="Run browser headless")
    
    # record command (future)
    sub.add_parser("record", help="Record a new macro")
    
    # replay command (future)
    replay = sub.add_parser("replay", help="Replay a saved macro")
    replay.add_argument("file", help="Macro JSON file to replay")
    
    args = parser.parse_args()
    
    if args.command == "autorun":
        from .autorun import run_youtube_workflow
        ar = run_youtube_workflow(
            youtube_url=args.youtube,
            channel=args.channel,
            headless=args.headless
        )
        print(f"[TestSimulator] Workflow pausiert bei Entscheidungspunkt. State: {ar.state}")
        print("[TestSimulator] Call ar.step_continue_after_decision() to resume.")
    
    elif args.command == "record":
        print("[TestSimulator] Record mode — coming soon.")
    
    elif args.command == "replay":
        print(f"[TestSimulator] Replaying: {args.file} — coming soon.")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
