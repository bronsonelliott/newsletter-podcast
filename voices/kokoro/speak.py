#!/usr/bin/env python3
"""Read a text file aloud with Kokoro and save it as a WAV file.

  speak.py script.txt out.wav am_echo 1.0

The main program runs this as a separate program, with its own packages.
"""

import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

RATE = 24_000           # Kokoro's sample rate
PAUSE_SECONDS = 0.3     # silence between passages


def main():
    text_path, wav_path, voice, speed = sys.argv[1:5]
    with open(text_path, encoding="utf-8") as file:
        text = file.read()
    pause = np.zeros(int(PAUSE_SECONDS * RATE), dtype=np.float32)
    # The first letter of a voice name is its language: a = American English.
    pipeline = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")
    with sf.SoundFile(wav_path, "w", samplerate=RATE, channels=1) as wav:
        for _, _, sound in pipeline(text, voice=voice, speed=float(speed)):
            wav.write(np.asarray(sound))
            wav.write(pause)


if __name__ == "__main__":
    main()
