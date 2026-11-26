"""Splitting the model's replies into English and Spanish parts.

The language model is asked to wrap every Spanish word or phrase in <es>...</es> tags,
for example: "Nice! In Spanish that's <es>muchas gracias</es>."
Each part is then spoken by a voice for its own language, so Spanish sounds Spanish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TAG = re.compile(r"<\s*(/?)\s*es\s*>", re.IGNORECASE)


@dataclass(frozen=True)
class Segment:
    lang: str  # "en" or "es"
    text: str


def split_languages(text: str, default: str = "en") -> list[Segment]:
    """Split text with <es>...</es> tags into ordered language segments.

    Forgiving on purpose, because small models are not always tidy:
    an unclosed <es> runs to the end, a stray </es> is ignored, and
    empty or whitespace-only parts are dropped.
    """
    segments: list[Segment] = []
    lang = default
    pos = 0

    def emit(chunk: str, chunk_lang: str) -> None:
        chunk = " ".join(chunk.split())
        if not chunk:
            return
        if segments and segments[-1].lang == chunk_lang:
            segments[-1] = Segment(chunk_lang, f"{segments[-1].text} {chunk}")
        else:
            segments.append(Segment(chunk_lang, chunk))

    for match in _TAG.finditer(text):
        emit(text[pos : match.start()], lang)
        closing = match.group(1) == "/"
        lang = default if closing else "es"
        pos = match.end()
    emit(text[pos:], lang)
    return segments


def strip_tags(text: str) -> str:
    """Remove the language tags, for subtitles and logs."""
    return " ".join(_TAG.sub(" ", text).split())
