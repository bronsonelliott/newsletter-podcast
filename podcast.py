#!/usr/bin/env python3
"""Make a private podcast episode from your newsletters.

  uv run podcast.py check             test the setup without making anything
  uv run podcast.py demo              make an episode from the made-up newsletters
  uv run podcast.py run               make today's episode from your mailbox
  uv run podcast.py serve             let a podcast app on your network play it
  uv run podcast.py schedule 05:00    write a daily Mac schedule (it doesn't start it)
"""

import argparse
import fcntl
import importlib.util
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from newsletter_podcast import PodcastError
from newsletter_podcast import feed, mail, settings, speak, writer

ROOT = Path(__file__).resolve().parent
JOB = "com.example.newsletter-podcast"


def notify(message):
    """Show a Mac notification when an unattended run fails."""
    if shutil.which("osascript"):
        subprocess.run(["osascript", "-e", "on run argv", "-e",
                        'display notification (item 1 of argv) with title "Newsletter podcast"',
                        "-e", "end run", message[:200]], capture_output=True)


def get_issues(config, secrets, args):
    if args.command == "demo":
        return mail.demo_issues(ROOT / "demo"), []
    hours = args.hours or config["mail"]["hours"]
    found = mail.fetch_issues(config["mail"], secrets.get("IMAP_PASSWORD"), hours)
    kept, dropped = mail.choose_issues(found, config["mail"]["skip"])
    if len(kept) < config["mail"]["minimum_issues"]:
        raise PodcastError(f"Only {len(kept)} newsletters in the last {hours} hours "
                           f"(the minimum is {config['mail']['minimum_issues']}). No episode was made.")
    return kept, dropped


def make_episode(config, secrets, args):
    folder = settings.output_folder(config, ROOT, demo=args.command == "demo")
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PodcastError("Another run is still going.")
        date = datetime.now().strftime("%Y-%m-%d")
        script_path, mp3_path = folder / f"episode-{date}.txt", folder / f"episode-{date}.mp3"
        details_path = folder / f"episode-{date}.json"
        if mp3_path.exists() and details_path.exists() and not args.force:
            print(f"Today's episode already exists: {mp3_path}\nUse --force to make it again.")
            return
        no_audio = args.no_audio or config["audio"]["engine"] == "none"
        if no_audio and script_path.exists() and not args.force:
            print(f"Today's script already exists: {script_path}\nUse --force to write it again.")
            return
        missing = [] if no_audio else speak.missing_parts(config["audio"])
        if missing:      # find out before paying for a script
            raise PodcastError(f"Not installed: {', '.join(missing)}. See the README, or add --no-audio.")
        issues, dropped = get_issues(config, secrets, args)
        print(f"{len(issues)} newsletters, {sum(len(i.text) for i in issues):,} characters")
        for issue, reason in dropped:
            print(f"  left out: {issue.sender}: {issue.subject} ({reason})")
        if script_path.exists() and not args.force:
            # The audio step failed last time. Don't pay for the script twice.
            script, usage = script_path.read_text(), {}
            print("Using the script that was already written today")
        else:
            print(f"Writing the script with {config['writer']['model']} ...", flush=True)
            script, usage = writer.write_script((ROOT / "prompt.md").read_text(), config, issues,
                                                secrets.get("ANTHROPIC_API_KEY"))
            feed.write_safely(script_path, script)
            print(f"  {usage['words']:,} words ({usage['input_tokens']:,} tokens in, {usage['output_tokens']:,} out)")
        if no_audio:
            feed.remove_old(folder, config["output"]["keep_days"])
            print(f"Script: {script_path}")
            return
        print(f"Recording with the {config['audio']['engine']} voice ...", flush=True)
        seconds = speak.make_mp3(script, mp3_path, config["audio"])
        feed.save_episode(folder, date, seconds, issues, usage)
        for name in feed.remove_old(folder, config["output"]["keep_days"]):
            print(f"  removed old file {name}")
        feed.build_feed(folder, config)
        print(f"Episode: {mp3_path} ({int(seconds // 60)} min {int(seconds % 60)} s)")


def check(config, secrets):
    """Test each piece and say what to fix. Makes nothing and spends nothing."""
    problems = 0

    def report(good, label, fix=""):
        nonlocal problems
        problems += not good
        print(f"{'OK  ' if good else 'FIX '} {label}{'' if good else ': ' + fix}")

    report(sys.version_info >= (3, 11), "Python 3.11 or newer", f"this is {sys.version.split()[0]}")
    missing = speak.missing_parts(config["audio"])
    report(not missing, f"voice: {config['audio']['engine']}", f"not installed: {', '.join(missing)}")
    if config["writer"]["backend"] == "api":
        report(importlib.util.find_spec("anthropic") is not None, "anthropic", "install the requirements")
        report(bool(secrets.get("ANTHROPIC_API_KEY")), "Anthropic API key", "add ANTHROPIC_API_KEY to .env")
    else:
        report(bool(shutil.which("claude")), "claude command", "install Claude Code")
    try:
        box, count = mail.open_folder(config["mail"], secrets.get("IMAP_PASSWORD"))
        box.logout()
        report(True, f"mail folder \"{config['mail']['folder']}\" ({count} messages)")
    except PodcastError as problem:
        report(False, "mail folder", str(problem))
    print("Ready." if not problems else f"{problems} to fix.")
    return 0 if not problems else 1


def serve(config, args):
    folder = settings.output_folder(config, ROOT, demo=args.demo)
    folder.mkdir(parents=True, exist_ok=True)
    feed.build_feed(folder, config)
    server = feed.make_server(config, folder)
    print(f"Feed: {feed.feed_address(config, folder)}/feed.xml\nAnyone with this address can listen. "
          "Press Control-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def schedule(time_of_day):
    """Write the Mac schedule file. The person starts it themselves."""
    try:
        moment = datetime.strptime(time_of_day, "%H:%M")
    except ValueError:
        raise PodcastError("Write the time like 05:00")
    tools = {str(Path(found).parent) for name in ("ffmpeg", "claude") if (found := shutil.which(name))}
    path = Path.home() / "Library/LaunchAgents" / f"{JOB}.plist"
    if path.exists():
        raise PodcastError(f"{path} already exists. Remove it first.")
    log = str(Path.home() / "Library/Logs/newsletter-podcast.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps({
        "Label": JOB,
        "ProgramArguments": [sys.executable, str(ROOT / "podcast.py"), "run"],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": {"Hour": moment.hour, "Minute": moment.minute},
        "EnvironmentVariables": {"PATH": ":".join(sorted(tools) + ["/usr/bin", "/bin"])},
        "StandardOutPath": log, "StandardErrorPath": log}))
    print(f"Wrote {path}\nStart it with:\n  launchctl bootstrap gui/$(id -u) {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    for name in ("demo", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--no-audio", action="store_true", help="stop after writing the script")
        sub.add_argument("--force", action="store_true", help="make today's episode again")
        if name == "run":
            sub.add_argument("--hours", type=int, help="look back this many hours")
    commands.add_parser("serve").add_argument("--demo", action="store_true", help="serve the demo episode")
    commands.add_parser("schedule").add_argument("time", help="24-hour time, such as 05:00")
    args = parser.parse_args()
    unattended = args.command == "run" and not sys.stdin.isatty()
    try:
        if args.command == "schedule":
            return schedule(args.time)
        config = settings.load_config(ROOT / "config.toml")
        secrets = settings.load_secrets(ROOT / ".env")
        if args.command == "check":
            return check(config, secrets)
        if args.command == "serve":
            return serve(config, args)
        return make_episode(config, secrets, args)
    except PodcastError as problem:
        print(f"STOPPED: {problem}", file=sys.stderr)
        if unattended:
            notify(str(problem))
        return 1
    except Exception:
        if unattended:
            notify("Failed. Details: ~/Library/Logs/newsletter-podcast.log")
        raise


if __name__ == "__main__":
    sys.exit(main())
