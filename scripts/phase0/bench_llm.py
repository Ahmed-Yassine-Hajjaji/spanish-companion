"""Phase 0, step 4: how fast does the language model answer on your GPU?

Needs a llama.cpp server running locally, for example:
  llama-server -m models/Qwen3.5-9B-Q4_K_M.gguf -ngl 99 -c 8192 --jinja --port 8080

Sends a few typical call turns with the companion persona, streams the replies and
measures, per turn: time to first token, time to the end of the first sentence (when
the voice could start speaking) and generation speed.

Usage:  python scripts/phase0/bench_llm.py [--url http://localhost:8080/v1]
"""

from __future__ import annotations

import argparse
import re
import sys
import time

from companion.metrics import summarize
from companion.prompts import PERSONA
from companion.system import gpu_used_mib

TURNS = [
    "Hi! I'm ready for my first Spanish lesson.",
    "How do I say good morning?",
    "Buenos dias. Did I say it right?",
    "Yo tener un perro.",
    "I'm tired today, I had a long day at school.",
    "What's the difference between ser and estar? Keep it simple.",
]

SENTENCE_END = re.compile(r"[.!?…](\s|$)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8080/v1")
    parser.add_argument(
        "--model", default="local", help="Name sent to the server; llama.cpp ignores it"
    )
    parser.add_argument("--max-tokens", type=int, default=120)
    args = parser.parse_args()

    from openai import OpenAI

    client = OpenAI(base_url=args.url, api_key="not-needed")
    print(f"VRAM in use with the model loaded: {gpu_used_mib() or 'unknown'} MiB\n")

    history = [{"role": "system", "content": PERSONA}]
    first_token, first_sentence, speeds = [], [], []
    for turn in TURNS:
        history.append({"role": "user", "content": turn})
        t0 = time.perf_counter()
        t_first = t_sentence = None
        reply, pieces = "", 0
        stream = client.chat.completions.create(
            model=args.model,
            messages=history,
            stream=True,
            max_tokens=args.max_tokens,
            temperature=0.7,
            # Qwen-style models: turn "thinking" off for live chat, it adds seconds of delay.
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if not delta:
                continue
            now = time.perf_counter()
            pieces += 1
            if t_first is None:
                t_first = now
            reply += delta
            if t_sentence is None and SENTENCE_END.search(reply):
                t_sentence = now
        t_end = time.perf_counter()
        history.append({"role": "assistant", "content": reply})

        if t_first is None:
            print(f"You: {turn}\n  (empty reply)\n")
            continue
        t_sentence = t_sentence or t_end
        gen_speed = (pieces - 1) / (t_end - t_first) if pieces > 1 else 0.0
        first_token.append(t_first - t0)
        first_sentence.append(t_sentence - t0)
        speeds.append(gen_speed)
        print(f"You: {turn}\nSol: {reply.strip()}")
        print(
            f"  first token {t_first - t0:.2f}s | first sentence {t_sentence - t0:.2f}s | "
            f"~{gen_speed:.0f} tokens/s\n"
        )
        if "<think>" in reply:
            print("  Warning: the model is 'thinking'. Check the server's chat template flags.\n")

    print("Summary")
    print(f"  time to first token:    {summarize(first_token)} s")
    print(f"  time to first sentence: {summarize(first_sentence)} s  (target: under 0.8)")
    print(f"  generation speed:       {summarize(speeds)} tokens/s  (estimate: 35 to 45)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
