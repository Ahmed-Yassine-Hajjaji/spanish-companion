"""Bilingual speech synthesis logic, independent of the call framework.

Pocket TTS has one model per language. Each part of a reply is spoken by the model
for its language, always with the same voice, so the companion sounds like one person.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from typing import Any

from companion.text import split_languages

# Pocket TTS model names per language tag.
POCKET_LANGUAGES = {"en": "english", "es": "spanish"}


class VoiceStates:
    """Caches the voice state per (language, voice), so switching voices is instant
    after the first use."""

    def __init__(self, models: Mapping[str, Any]):
        self._models = models
        self._states: dict[tuple[str, str], Any] = {}

    def get(self, lang: str, voice: str) -> Any:
        key = (lang, voice)
        if key not in self._states:
            self._states[key] = self._models[lang].get_state_for_audio_prompt(voice)
        return self._states[key]

    def preload(self, voices: tuple[str, ...]) -> None:
        for lang in self._models:
            for voice in voices:
                self.get(lang, voice)


def iter_bilingual_audio(
    models: Mapping[str, Any],
    get_state: Callable[[str], Any],
    text: str,
) -> Iterator[Any]:
    """Yield audio chunks for a tagged reply, part by part, in order.

    ``get_state(lang)`` returns the voice state for that language's model.
    The call pipeline never splits text inside an <es>...</es> span, so each
    piece of text arrives with its tags complete.
    """
    for seg in split_languages(text):
        model = models[seg.lang]
        yield from model.generate_audio_stream(get_state(seg.lang), seg.text, copy_state=True)
