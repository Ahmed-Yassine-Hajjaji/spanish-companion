"""Check how the real model handles rehearsal mode, without a call.

Sends a few presentation phrases to the running llama-server with the same system
prompt as a call, and prints each raw reply with a pass/fail against what Sol should
do. Useful after any prompt change.

Usage (with llama-server running):
    python scripts/checks/rehearsal.py [--url http://127.0.0.1:8080/v1] [--runs 3]
"""

from __future__ import annotations

import argparse
import json
import urllib.request

from pipecat.turns.user_turn_completion import USER_TURN_COMPLETION_INSTRUCTIONS

from companion.prompts import PERSONA

PREFIX = [
    {"role": "assistant", "content": "● Hi! <es>Hola</es>. What would you like to do today?"},
    {
        "role": "user",
        "content": "I have a presentation about daily life in Alicante. "
        "I'll say my phrases one by one, correct me if I'm wrong.",
    },
    {"role": "assistant", "content": "● Sure, go ahead."},
]

# (what the user said, what a good reply starts with)
CASES = [
    ("En Alicante, la playa está en el centro de la", "◐"),
    ("En Alicante, la playa está en el centro de la ciudad.", "● Correct."),
    ("Por la tarde hace mucho color y algunas personas duermen la siesta.", "● Almost:"),
    ("Es un edificio grande y bueno, de hace más de cien años.", "● Correct."),
    ("Se llama la playa del Postiguet.", "● Correct."),
    ("Yo soy estudiante y me gusta mucho los churros.", "● Almost:"),
    ("Otto Milesol.", "● Sorry"),
]


def ask(url: str, text: str) -> tuple[str, str]:
    body = {
        "model": "local",
        "temperature": 0.3,
        "max_tokens": 100,
        "repeat_penalty": 1.1,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": PERSONA + USER_TURN_COMPLETION_INSTRUCTIONS},
            *PREFIX,
            {"role": "user", "content": text},
        ],
    }
    request = urllib.request.Request(
        f"{url}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        choice = json.load(response)["choices"][0]
    return choice["message"]["content"], choice["finish_reason"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    passed = total = 0
    for text, expected in CASES:
        print(f"\n> {text}   (want: {expected})")
        for _ in range(args.runs):
            reply, finish = ask(args.url, text)
            ok = reply.strip().startswith(expected) and finish == "stop"
            passed += ok
            total += 1
            print(f"  {'PASS' if ok else 'FAIL'}  {reply!r}  [{finish}]")
    print(f"\n{passed}/{total} replies as expected")


if __name__ == "__main__":
    main()
