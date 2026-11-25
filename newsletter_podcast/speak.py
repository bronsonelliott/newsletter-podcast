"""Turn the script into an MP3, with whichever voice the settings name.

The voice runs as a separate program. It is handed the script and nothing else:
no passwords and no settings."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import PodcastError

ROOT = Path(__file__).resolve().parent.parent
LOUDNESS = "loudnorm=I=-16:TP=-1.5:LRA=11"      # the usual podcast level
MAC_WORDS_PER_MINUTE = 175
DEFAULT_KOKORO_VOICE = "am_echo"
MAC_VOICE_SECONDS = 600      # it takes seconds, but now and then it finishes and never exits
LONGEST_PATH = 159      # Kokoro's pronunciation library can't read a longer folder path


class TookTooLong(PodcastError):
    """A program was stopped for running past its limit."""


def kokoro_python(audio):
    """The Python that has Kokoro installed. (Not resolved: that would leave its
    own folder of packages and find the ordinary Python behind it.)"""
    return ROOT / Path(audio["kokoro_python"]).expanduser()


def kokoro_works(python):
    # -I and an empty folder: never import a stray file that happens to have the right name.
    test = [str(python), "-I", "-c", "import kokoro, soundfile, numpy, en_core_web_sm"]
    with tempfile.TemporaryDirectory() as folder:
        return subprocess.run(test, capture_output=True, cwd=folder, env=plain_environment()).returncode == 0


def plain_environment():
    return {name: os.environ[name] for name in ("PATH", "HOME", "LANG", "HF_HOME") if name in os.environ}


def missing_parts(audio):
    """What the chosen voice needs that isn't installed."""
    engine, missing = audio["engine"], []
    if engine == "none":
        return missing
    missing += [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if engine == "mac" and not shutil.which("say"):
        missing.append("the Mac voice (this isn't a Mac)")
    if engine == "kokoro":
        python = kokoro_python(audio)
        if not python.exists() or not kokoro_works(python):
            missing.append(f"Kokoro (looked in {audio['kokoro_python']})")
        else:
            for data in python.parent.parent.glob("lib/python*/site-packages/espeakng_loader/espeak-ng-data"):
                if len(str(data)) > LONGEST_PATH:
                    missing.append(f"a shorter folder path: Kokoro's is {len(str(data))} characters and the limit is "
                                   f"{LONGEST_PATH}, so move the project and install Kokoro again")
    return missing


def voice_command(audio, text_path, sound_path):
    if audio["engine"] == "kokoro":
        return [str(kokoro_python(audio)), "-I", str(ROOT / "voices/kokoro/speak.py"), str(text_path), str(sound_path),
                audio["voice"] or DEFAULT_KOKORO_VOICE, str(audio["speed"])]
    command = ["say", "-f", str(text_path), "-o", str(sound_path), "-r", str(round(MAC_WORDS_PER_MINUTE * audio["speed"]))]
    return command + (["-v", audio["voice"]] if audio["voice"] else [])


def run_tool(command, label, folder, limit=3600):
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True, cwd=folder,
                              env=plain_environment(), timeout=limit)
    except FileNotFoundError:
        raise PodcastError(f"{label} isn't installed. See the README.")
    except subprocess.TimeoutExpired:
        raise TookTooLong(f"{label} ran for {limit // 60} minutes without finishing.")
    except subprocess.CalledProcessError as problem:
        raise PodcastError(f"{label} failed: {problem.stderr.strip()[-300:]}")


def record(audio, text_path, sound_path, folder):
    """Run the voice. The Mac voice gets a second try if it gets stuck."""
    command = voice_command(audio, text_path, sound_path)
    if audio["engine"] != "mac":
        return run_tool(command, "The voice", folder)
    try:
        return run_tool(command, "The voice", folder, MAC_VOICE_SECONDS)
    except TookTooLong:
        print("The Mac voice got stuck. Trying once more ...", flush=True)
        return run_tool(command, "The voice", folder, MAC_VOICE_SECONDS)


def make_mp3(script, mp3_path, audio):
    """Write the MP3 and return its length in seconds."""
    mp3_path = Path(mp3_path)
    part_path = mp3_path.with_suffix(".part.mp3")
    with tempfile.TemporaryDirectory() as folder:
        text_path = Path(folder) / "script.txt"
        # The Mac voice treats [[...]] as commands, so never pass any through.
        text_path.write_text(re.sub(r"\[+", "[", re.sub(r"\]+", "]", script)), encoding="utf-8")
        sound_path = Path(folder) / ("sound.wav" if audio["engine"] == "kokoro" else "sound.aiff")
        record(audio, text_path, sound_path, folder)
        try:
            # Write to a .part file first, so a half-made MP3 never becomes an episode.
            run_tool(["ffmpeg", "-y", "-loglevel", "error", "-i", str(sound_path), "-af", LOUDNESS, "-ar", "44100", "-ac", "1",
                      "-codec:a", "libmp3lame", "-b:a", "96k", "-f", "mp3", str(part_path.resolve())], "ffmpeg", folder)
            length = run_tool(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                               str(part_path.resolve())], "ffprobe", folder)
            try:
                seconds = float(length.stdout)
            except ValueError:
                seconds = 0
            if seconds < 1:
                raise PodcastError("The voice produced no sound")
            part_path.replace(mp3_path)
        finally:
            part_path.unlink(missing_ok=True)
    return seconds
