#!/usr/bin/env python3
"""Read a text file aloud with Kokoro and save it as a WAV file.

  speak.py script.txt out.wav VOICE SPEED    a blank VOICE means am_echo
  speak.py --check                           is everything installed?

The main program runs this as a separate program, with its own packages. It's
also the example to copy for another voice. The rules are in the README.
"""

import sys
from pathlib import Path

DEFAULT_VOICE = "am_echo"
RATE = 24_000           # Kokoro's sample rate
PAUSE_SECONDS = 0.3     # silence between passages
LONGEST_PATH = 159      # Kokoro's pronunciation library can't read a longer folder path


def check():
    """Stop with a message if Kokoro can't run. Downloads nothing."""
    try:
        import en_core_web_sm, kokoro, numpy, soundfile  # noqa: E401, F401
    except ImportError:
        sys.exit("Kokoro isn't installed yet. See \"Install Kokoro\" in the README.")
    for data in Path(sys.prefix).glob("lib/python*/site-packages/espeakng_loader/espeak-ng-data"):
        if len(str(data)) > LONGEST_PATH:
            sys.exit(f"Kokoro's folder path is {len(str(data))} characters and the limit is {LONGEST_PATH}, "
                     "so move the project to a shorter path and install Kokoro again.")


def speak(text_path, wav_path, voice, speed):
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    text = Path(text_path).read_text(encoding="utf-8")
    voice = voice or DEFAULT_VOICE
    pause = np.zeros(int(PAUSE_SECONDS * RATE), dtype=np.float32)
    # The first letter of a voice name is its language: a = American English.
    pipeline = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")
    with sf.SoundFile(wav_path, "w", samplerate=RATE, channels=1) as wav:
        for _, _, sound in pipeline(text, voice=voice, speed=float(speed)):
            wav.write(np.asarray(sound))
            wav.write(pause)


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check()
    else:
        speak(*sys.argv[1:5])
