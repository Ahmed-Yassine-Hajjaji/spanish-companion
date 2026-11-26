"""Phase 0, step 2: record yourself saying the test sentences.

Each sentence is saved as a 16 kHz mono WAV in recordings/, with a manifest.tsv
listing what you meant to say, so the recognizers can be scored against it.

Usage:  python scripts/phase0/record_samples.py [--sentences FILE] [--out recordings]
Press Enter to start a sentence, Enter again to stop. Type s + Enter to skip, q + Enter to quit.
"""

from __future__ import annotations

import argparse
import queue
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 16_000
HERE = Path(__file__).parent


def load_sentences(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in lines if s.strip() and not s.lstrip().startswith("#")]


def record_until_enter() -> np.ndarray:
    import sounddevice as sd  # imported here so the rest of the repo works without PortAudio

    chunks: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time, status):  # noqa: ARG001
        chunks.put(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        input("  Recording... press Enter to stop.")
    audio = [chunks.get() for _ in range(chunks.qsize())]
    return np.concatenate(audio)[:, 0] if audio else np.zeros(0, dtype="float32")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sentences", type=Path, default=HERE / "test_sentences.txt")
    parser.add_argument("--out", type=Path, default=Path("recordings"))
    args = parser.parse_args()

    sentences = load_sentences(args.sentences)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = args.out / "manifest.tsv"
    rows: list[str] = []

    print(f"{len(sentences)} sentences. Speak naturally; hesitations are useful data.\n")
    for i, sentence in enumerate(sentences, start=1):
        print(f"[{i}/{len(sentences)}] {sentence}")
        cmd = input("  Enter to start (s = skip, q = quit): ").strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            continue
        audio = record_until_enter()
        if audio.size < SAMPLE_RATE // 4:
            print("  Too short, skipped.")
            continue
        name = f"{i:02d}.wav"
        sf.write(args.out / name, audio, SAMPLE_RATE)
        rows.append(f"{name}\t{sentence}")
        print(f"  Saved {name} ({audio.size / SAMPLE_RATE:.1f} s, peak {np.abs(audio).max():.2f})")
        if np.abs(audio).max() < 0.05:
            print("  Very quiet: check the microphone input level.")

    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"\nWrote {len(rows)} recordings and {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
