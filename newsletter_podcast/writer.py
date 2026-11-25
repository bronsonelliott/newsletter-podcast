"""Send the newsletters to Claude and get the script back.

Claude gets text and nothing else: no tools, no files, no web, no passwords.
A newsletter with hidden instructions in it could change the words of one
episode, but it has nothing to act with."""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime

from . import PodcastError

WORDS_PER_MINUTE = 180      # measured from the demo episode, pauses included
MAX_OUTPUT_TOKENS = 64_000


def target_words(config):
    return round(config["show"]["minutes"] * WORDS_PER_MINUTE / 50) * 50 or 50


def defuse(text):
    """Stop a newsletter from closing its own tag and posing as instructions, and
    from using @ to pull in a file: Claude Code reads the file after an @ sign.
    The look-alike character means the same thing to a reader."""
    return re.sub(r"<(?=\s*/?\s*newsletter)", "(", text, flags=re.I).replace("@", "\uff20")


def build_prompt(template, config, issues, now=None):
    """Return (instructions, newsletters). Nothing is ever cut to fit."""
    show, limit = config["show"], config["writer"]["max_characters"]
    total = sum(len(issue.text) for issue in issues)
    if total > limit:
        biggest = sorted(issues, key=lambda issue: -len(issue.text))[:3]
        names = "; ".join(f"{issue.sender} ({len(issue.text):,})" for issue in biggest)
        raise PodcastError(f"The newsletters add up to {total:,} characters and the limit is {limit:,}. "
                           f"Raise max_characters or skip some. The longest: {names}")
    topics = ", ".join(show["always_cover"])
    values = {
        "show_name": show["name"],
        "date": (now or datetime.now()).strftime("%A, %B %d, %Y").replace(" 0", " "),
        "listener": show["listener"] or "nothing given.",
        "words": f"{target_words(config):,}",
        "minutes": str(show["minutes"]),
        "always_cover": (f"Give these topics their own section: {topics}. If a topic has no news today, "
                         "say so in one sentence.") if topics else "Go straight from the top stories to the quick items.",
    }
    instructions = re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), template)
    blocks = []
    for number, issue in enumerate(issues, 1):
        safe = [defuse(field) for field in (issue.sender, issue.subject, issue.text)]
        blocks.append(f'<newsletter number="{number}">\nFrom: {safe[0]}\nSubject: {safe[1]}\n\n{safe[2]}\n</newsletter>')
    return instructions, "\n\n".join(blocks)


def ask_api(instructions, newsletters, writer, api_key, client=None):
    """One streaming call to the Anthropic API, with no tools."""
    if not api_key:
        raise PodcastError("ANTHROPIC_API_KEY is missing from .env")
    try:
        import anthropic
    except ImportError:
        raise PodcastError("The anthropic package isn't installed. See the README.")
    client = client or anthropic.Anthropic(api_key=api_key)
    try:
        with client.beta.messages.stream(
            model=writer["model"],
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": writer["effort"]},
            system=instructions,
            messages=[{"role": "user", "content": newsletters}],
            # If a safety filter declines the request (it can happen on days with
            # a lot of security news), the API retries it on another Claude model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            reply = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise PodcastError("Anthropic did not accept ANTHROPIC_API_KEY. Check it in .env.")
    except anthropic.RateLimitError:
        raise PodcastError("Anthropic's rate limit was reached. Try again in a few minutes.")
    except anthropic.APIStatusError as problem:
        raise PodcastError(f"Anthropic returned an error: {problem.message}")
    except anthropic.APIConnectionError:
        raise PodcastError("Could not reach Anthropic. Check your internet connection.")
    if reply.stop_reason != "end_turn":
        raise PodcastError(f"Claude stopped before finishing the script ({reply.stop_reason}).")
    text = "".join(block.text for block in reply.content if block.type == "text")
    usage = reply.usage
    return text, {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "model": reply.model}


def claude_command(instructions, writer):
    return ["claude", "-p", "--safe-mode", "--strict-mcp-config", "--tools", "",
            "--no-session-persistence", "--model", writer["model"], "--effort", writer["effort"],
            "--system-prompt", instructions, "--output-format", "stream-json", "--verbose"]


def ask_claude_code(instructions, newsletters, writer, run=subprocess.run):
    """One run of the claude command, with every tool turned off, from an empty folder."""
    private = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "IMAP_PASSWORD")
    environment = {name: value for name, value in os.environ.items() if name not in private}
    environment["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(MAX_OUTPUT_TOKENS)
    environment["CLAUDE_CODE_DISABLE_ATTACHMENTS"] = "1"      # a second guard against @file
    try:
        with tempfile.TemporaryDirectory() as empty:
            result = run(claude_command(instructions, writer), input=newsletters, capture_output=True,
                         text=True, cwd=empty, env=environment, timeout=3600)
    except FileNotFoundError:
        raise PodcastError("The claude command isn't installed. Install Claude Code or use backend = \"api\".")
    except subprocess.TimeoutExpired:
        raise PodcastError("Claude Code ran for an hour without finishing.")
    text, final = [], None
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "assistant":
            text += [b["text"] for b in event["message"]["content"] if b.get("type") == "text"]
        elif event.get("type") == "result":
            final = event
    if result.returncode != 0 or final is None or final.get("is_error"):
        detail = (final or {}).get("result") or result.stderr or result.stdout
        raise PodcastError(f"Claude Code failed: {str(detail).strip()[-300:]}")
    usage = final.get("usage") or {}
    return "".join(text), {"input_tokens": sum(usage.get(k) or 0 for k in (
        "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
        "output_tokens": usage.get("output_tokens"), "model": writer["model"]}


def clean_script(text):
    """Remove anything that shouldn't be read aloud."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^[ \t]*(#{1,6}|[-*•])[ \t]+", "", text, flags=re.M)
    text = re.sub(r"[*`]+|\b_+|_+\b", "", text).replace("\uff20", "@")
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def write_script(template, config, issues, api_key):
    instructions, newsletters = build_prompt(template, config, issues)
    if config["writer"]["backend"] == "api":
        text, usage = ask_api(instructions, newsletters, config["writer"], api_key)
    else:
        text, usage = ask_claude_code(instructions, newsletters, config["writer"])
    script = clean_script(text)
    words = len(script.split())
    # A refusal or a crash is far shorter than a real episode. This is a crash
    # check, so a light news day still passes.
    if words < min(300, target_words(config) * 0.3):
        raise PodcastError(f"Claude's script is only {words} words, so no episode was made. It said: {script[:200]}")
    return script, {**usage, "words": words}
