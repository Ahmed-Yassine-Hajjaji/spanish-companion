"""Phase 0, step 5b: a more natural voice that is still fast enough for a live call.

Uses Kyutai's Pocket TTS (about 100M parameters per language, real streaming).
There is one model per language; both use the same catalog voice, so English and
<es>...</es> parts are spoken by the same person. Runs on the CPU by default, leaving
the GPU to the language model.

Measured on an RTX 4060 PC (Ryzen 7 X3D): first audio 0.08 s and real-time factor
0.26 on the CPU, against 0.09 s for Kokoro (more robotic), 1.8 s for Chatterbox and
about 8 s for Qwen3-TTS. See docs/phase0-results.md.

Usage:
  python scripts/phase0/bench_pocket_tts.py                 # voice "eve" (the chosen one), CPU
  python scripts/phase0/bench_pocket_tts.py --voice lola    # a Spanish voice for both
  python scripts/phase0/bench_pocket_tts.py --device cuda
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

LINES = [
    "Hi! Ready for a little Spanish today?",
    "Nice! In Spanish that's <es>muchas gracias</es>.",
    "Close! We say <es>yo tengo un perro</es>, not <es>yo tener</es>. Try again?",
    "How would you say <es>good morning</es>? It's <es>buenos días</es>.",
    "<es>¿Dónde está el baño?</es> means: where is the bathroom?",
    "Remember <es>la cuenta, por favor</es> from last time? You'll need it at a restaurant.",
]
LANGUAGES = {"en": "english", "es": "spanish"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--voice", default="eve", help="Catalog voice, e.g. eve, alba, lola")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    from pocket_tts import TTSModel

    vram_before = gpu_used_mib()
    t0 = time.perf_counter()
    models, states = {}, {}
    for lang, name in LANGUAGES.items():
        model = TTSModel.load_model(language=name)
        if args.device == "cuda":
            model = model.to("cuda")
        models[lang] = model
        states[lang] = model.get_state_for_audio_prompt(args.voice)
    sample_rate = models["en"].sample_rate
    print(f"Loaded both languages with voice '{args.voice}' in {time.perf_counter() - t0:.1f} s")
    if args.device == "cuda" and None not in (vram_before, gpu_used_mib()):
        print(f"VRAM used by the voice: {gpu_used_mib() - vram_before:,} MiB")

    def speak(text: str) -> tuple[np.ndarray, float | None]:
        """Stream one line; return audio and seconds until the first chunk."""
        start, first, parts = time.perf_counter(), None, []
        for seg in split_languages(text):
            for chunk in models[seg.lang].generate_audio_stream(states[seg.lang], seg.text):
                if first is None:
                    first = time.perf_counter() - start
                chunk = chunk.cpu().numpy() if hasattr(chunk, "cpu") else chunk
                parts.append(np.asarray(chunk, dtype="float32").reshape(-1))
        return (np.concatenate(parts) if parts else np.zeros(0, "float32")), first

    speak("Warm up.")  # first call is slower, not timed
    out_dir = args.out / "pocket_tts" / f"{args.voice}_{args.device}"
    out_dir.mkdir(parents=True, exist_ok=True)
    firsts, rtfs = [], []
    for i, line in enumerate(LINES, start=1):
        t0 = time.perf_counter()
        audio, first = speak(line)
        took = time.perf_counter() - t0
        seconds = audio.size / sample_rate
        path = out_dir / f"{i:02d}.wav"
        sf.write(path, audio, sample_rate)
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
    print(f"\nListen to the files in {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
