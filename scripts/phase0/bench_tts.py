"""Phase 0, step 5: can the voice speak English and Spanish fast enough?

Uses Kokoro 82M with two voices that share one loaded model: an English voice for
normal text and a Spanish voice for <es>...</es> parts. Measures time to first audio
and real-time factor, and saves each line as a WAV in output/ so you can listen to
the Spanish pronunciation.

Needs espeak-ng installed (Kokoro uses it for Spanish). See docs/phase0.md.

Usage:
  python scripts/phase0/bench_tts.py                 # on the CPU (the plan)
  python scripts/phase0/bench_tts.py --device cuda   # to compare
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from companion.metrics import summarize
from companion.system import gpu_used_mib
from companion.text import split_languages

SAMPLE_RATE = 24_000
LINES = [
    "Hi! Ready for a little Spanish today?",
    "Nice! In Spanish that's <es>muchas gracias</es>.",
    "Close! We say <es>yo tengo un perro</es>, not <es>yo tener</es>. Try again?",
    "How would you say <es>good morning</es>? It's <es>buenos días</es>.",
    "<es>¿Dónde está el baño?</es> means: where is the bathroom?",
    "Remember <es>la cuenta, por favor</es> from last time? You'll need it at a restaurant.",
]
LANG_CODES = {"en": "a", "es": "e"}  # Kokoro: a = American English, e = Spanish


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--en-voice", default="af_heart")
    parser.add_argument("--es-voice", default="ef_dora", help="Also try em_alex")
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    from kokoro import KModel, KPipeline

    vram_before = gpu_used_mib()
    t0 = time.perf_counter()
    model = KModel(repo_id="hexgrad/Kokoro-82M").to(args.device).eval()
    pipelines = {
        lang: KPipeline(lang_code=code, repo_id="hexgrad/Kokoro-82M", model=model)
        for lang, code in LANG_CODES.items()
    }
    voices = {"en": args.en_voice, "es": args.es_voice}
    print(f"Loaded on {args.device} in {time.perf_counter() - t0:.1f} s")
    if args.device == "cuda" and None not in (vram_before, gpu_used_mib()):
        print(f"VRAM used by the voice: {gpu_used_mib() - vram_before:,} MiB")

    def speak(text: str) -> tuple[np.ndarray, float | None]:
        """Synthesize one line; return audio and seconds until the first audio chunk."""
        start, first, parts = time.perf_counter(), None, []
        for seg in split_languages(text):
            for result in pipelines[seg.lang](seg.text, voice=voices[seg.lang]):
                audio = result.audio
                if audio is None:
                    continue
                if first is None:
                    first = time.perf_counter() - start
                audio = audio.cpu().numpy() if hasattr(audio, "cpu") else audio
                parts.append(np.asarray(audio, dtype="float32"))
        return (np.concatenate(parts) if parts else np.zeros(0, "float32")), first

    speak("Warm up.")  # first call is slower, not timed
    args.out.mkdir(parents=True, exist_ok=True)
    firsts, rtfs = [], []
    for i, line in enumerate(LINES, start=1):
        t0 = time.perf_counter()
        audio, first = speak(line)
        took = time.perf_counter() - t0
        seconds = audio.size / SAMPLE_RATE
        path = args.out / f"tts_{args.device}_{i:02d}.wav"
        sf.write(path, audio, SAMPLE_RATE)
        if first is not None and seconds:
            firsts.append(first)
            rtfs.append(took / seconds)
        print(
            f"{path.name}: first audio {first or 0:.2f}s, {seconds:.1f}s of speech in {took:.2f}s"
        )
        print(f"   {line}")

    print("\nSummary")
    print(f"  time to first audio: {summarize(firsts)} s  (target: under 0.2)")
    print(f"  real-time factor:    {summarize(rtfs)}  (below 0.3 is comfortable)")
    print(f"\nListen to the files in {args.out}/: does the Spanish sound right?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
