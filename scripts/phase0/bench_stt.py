"""Phase 0, step 3: which speech recognizer hears *you* best, and how fast?

Runs your recordings through Parakeet TDT 0.6B v3 (CPU, via onnx-asr) and/or
Whisper large-v3-turbo (GPU, via faster-whisper), prints each transcript next to
what you meant to say, and saves a CSV in output/.

Usage:
  python scripts/phase0/bench_stt.py                       # both engines
  python scripts/phase0/bench_stt.py --engine parakeet
  python scripts/phase0/bench_stt.py --engine whisper --whisper-device cpu
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections.abc import Callable
from pathlib import Path

import soundfile as sf

from companion.metrics import summarize, word_error_rate
from companion.system import gpu_used_mib

# A hint for Whisper that the speech mixes English and Spanish. Try with and without.
DEFAULT_PROMPT = "Hello! Hola, ¿cómo estás? I'm learning Spanish: yo quiero un café, por favor."


def load_parakeet() -> Callable[[Path], str]:
    import onnx_asr

    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3")
    return lambda path: model.recognize(str(path))


def load_whisper(device: str, prompt: str | None) -> Callable[[Path], str]:
    from faster_whisper import WhisperModel

    compute = "int8_float16" if device == "cuda" else "int8"
    model = WhisperModel("large-v3-turbo", device=device, compute_type=compute)

    def run(path: Path) -> str:
        segments, info = model.transcribe(
            str(path), language=None, beam_size=1, initial_prompt=prompt
        )
        text = " ".join(s.text.strip() for s in segments)
        return f"{text}  [{info.language} {info.language_probability:.2f}]"

    return run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", choices=["parakeet", "whisper", "both"], default="both")
    parser.add_argument("--recordings", type=Path, default=Path("recordings"))
    parser.add_argument("--whisper-device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--no-prompt", action="store_true", help="Run Whisper without the hint")
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    manifest = args.recordings / "manifest.tsv"
    if not manifest.exists():
        print(f"No {manifest}. Run record_samples.py first.")
        return 1
    items = [line.split("\t", 1) for line in manifest.read_text("utf-8").splitlines() if line]
    if not items:
        print(f"{manifest} is empty. Record some sentences first.")
        return 1

    engines = ["parakeet", "whisper"] if args.engine == "both" else [args.engine]
    args.out.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    for engine in engines:
        vram_before = gpu_used_mib()
        t0 = time.perf_counter()
        if engine == "parakeet":
            recognize = load_parakeet()
        else:
            recognize = load_whisper(
                args.whisper_device, None if args.no_prompt else DEFAULT_PROMPT
            )
        load_s = time.perf_counter() - t0
        vram_after = gpu_used_mib()
        vram = (
            f"{vram_after - vram_before:,} MiB VRAM"
            if None not in (vram_before, vram_after)
            else "VRAM unknown"
        )
        print(f"\n=== {engine}: loaded in {load_s:.1f} s, {vram} ===")

        recognize(args.recordings / items[0][0])  # warm-up, not timed
        latencies, rtfs, wers = [], [], []
        for name, expected in items:
            path = args.recordings / name
            seconds = sf.info(str(path)).duration
            t0 = time.perf_counter()
            heard = recognize(path)
            took = time.perf_counter() - t0
            wer = word_error_rate(expected, heard.split("  [")[0])
            latencies.append(took)
            rtfs.append(took / seconds)
            wers.append(wer)
            results.append(
                {
                    "engine": engine,
                    "file": name,
                    "audio_s": round(seconds, 2),
                    "took_s": round(took, 3),
                    "wer": round(wer, 3),
                    "expected": expected,
                    "heard": heard,
                }
            )
            print(f"{name} {took:5.2f}s  WER {wer:4.0%}\n   said:  {expected}\n   heard: {heard}")

        print(f"\n{engine} summary")
        print(f"  time per sentence: {summarize(latencies)} s")
        print(f"  real-time factor:  {summarize(rtfs)} (below 0.2 is comfortable)")
        print(f"  word error rate:   {summarize(wers)}")

    out_file = args.out / "stt_results.csv"
    with out_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nSaved {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
