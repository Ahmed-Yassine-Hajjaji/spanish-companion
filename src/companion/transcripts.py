"""Save each call's conversation so mistakes can be reviewed in later phases.

One JSON file per call in data/calls/ (git-ignored, stays on this PC). Each turn
keeps the raw text with <es> tags, so later phases can tell which parts were
Spanish.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from companion.text import remove_turn_markers


def call_turns(messages: Iterable[Mapping[str, Any]], skip: Iterable[str] = ()) -> list[dict]:
    """The spoken turns of a call: user and assistant text only, in order.

    Tool calls, tool results and instruction messages listed in ``skip`` are left out.
    """
    skipped = set(skip)
    turns = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role not in ("user", "assistant") or not content:
            continue
        if isinstance(content, list):  # OpenAI-style content parts
            content = " ".join(p.get("text", "") for p in content if isinstance(p, Mapping))
        text = str(content).strip()
        if role == "assistant":
            text = remove_turn_markers(text)
        if text and text not in skipped:
            turns.append({"role": role, "text": text})
    return turns


def save_call(
    messages: Iterable[Mapping[str, Any]],
    calls_dir: str | Path,
    *,
    started: datetime,
    skip: Iterable[str] = (),
) -> Path | None:
    """Write the call to ``calls_dir/<start time>.json``. Returns None for an empty call."""
    turns = call_turns(messages, skip)
    if not any(t["role"] == "user" for t in turns):
        return None
    folder = Path(calls_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{started:%Y-%m-%d_%H-%M-%S}.json"
    record = {
        "started": started.isoformat(timespec="seconds"),
        "ended": datetime.now().isoformat(timespec="seconds"),
        "turns": turns,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
