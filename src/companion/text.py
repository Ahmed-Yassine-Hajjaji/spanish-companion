"""Splitting the model's replies into English and Spanish parts.

The language model is asked to wrap every Spanish word or phrase in <es>...</es> tags,
for example: "Nice! In Spanish that's <es>muchas gracias</es>."
Each part is then spoken by a voice for its own language, so Spanish sounds Spanish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TAG = re.compile(r"<\s*(/?)\s*es\s*>", re.IGNORECASE)
# Closing punctuation at the start of a part belongs to the part before it
# ("<es>gracias</es>." -> "gracias."). Opening marks like ¿ and ¡ stay where they are.
_LEADING_PUNCT = re.compile(r"^[.,;:!?…)\]\"'»]+")
# The model sometimes forgets the tags around a Spanish question or exclamation, such
# as "¡Hola!" or "¿Cómo estás?". Only Spanish opens a sentence with ¿ or ¡, so a span
# from ¿/¡ to its closing ?/! in untagged text is treated as Spanish.
_UNTAGGED_SPANISH = re.compile(r"[¿¡][^¿¡?!]*[?!]")


@dataclass(frozen=True)
class Segment:
    lang: str  # "en" or "es"
    text: str


def split_languages(text: str, default: str = "en") -> list[Segment]:
    """Split text with <es>...</es> tags into ordered language segments.

    Forgiving on purpose, because small models are not always tidy:
    an unclosed <es> runs to the end, a stray </es> is ignored, and
    empty or whitespace-only parts are dropped. Punctuation right after a tag
    is kept with the part before it, so no part is punctuation only (some
    voice models crash on those).
    """
    segments: list[Segment] = []
    lang = default
    pos = 0

    def emit(chunk: str, chunk_lang: str) -> None:
        chunk = " ".join(chunk.split())
        punct = _LEADING_PUNCT.match(chunk)
        if punct and segments:
            last = segments[-1]
            segments[-1] = Segment(last.lang, last.text + punct.group())
            chunk = chunk[punct.end() :].strip()
        if not chunk:
            return
        if segments and segments[-1].lang == chunk_lang:
            segments[-1] = Segment(chunk_lang, f"{segments[-1].text} {chunk}")
        else:
            segments.append(Segment(chunk_lang, chunk))

    def emit_part(chunk: str, chunk_lang: str) -> None:
        if chunk_lang == "es" or default == "es":
            emit(chunk, chunk_lang)
            return
        start = 0
        for spanish in _UNTAGGED_SPANISH.finditer(chunk):
            emit(chunk[start : spanish.start()], chunk_lang)
            emit(spanish.group(), "es")
            start = spanish.end()
        emit(chunk[start:], chunk_lang)

    for match in _TAG.finditer(text):
        emit_part(text[pos : match.start()], lang)
        closing = match.group(1) == "/"
        lang = default if closing else "es"
        pos = match.end()
    emit_part(text[pos:], lang)
    return segments


def strip_tags(text: str) -> str:
    """Remove the language tags, for subtitles and logs."""
    return " ".join(_TAG.sub(" ", text).split())


# Turn-completion markers the language model starts its replies with (see
# companion.bot.turn_strategies). The model sometimes repeats one ("● ● Correct."),
# so remove them anywhere before speaking or saving a reply.
TURN_MARKERS = "●◐○"
_MARKERS = re.compile(f"[{TURN_MARKERS}]")


def remove_turn_markers(text: str) -> str:
    """Drop turn-completion markers and the spaces they leave behind."""
    return " ".join(_MARKERS.sub(" ", text).split())
