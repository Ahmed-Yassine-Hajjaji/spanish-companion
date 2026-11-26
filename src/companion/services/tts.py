"""Bilingual text-to-speech with Kyutai's Pocket TTS, run on the CPU.

The language model wraps Spanish in <es>...</es>. Pipecat normally cuts text into
sentences before speaking; here the cutting never happens inside an <es> span, and
each part goes to the English or Spanish model with the same voice. The voice can
be switched during a call with a TTSUpdateSettingsFrame(delta=...(voice="alba")).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService
from pipecat.utils.text.skip_tags_aggregator import SkipTagsAggregator

from companion.speech import VoiceStates, iter_bilingual_audio
from companion.text import remove_turn_markers

ES_TAGS = ("<es>", "</es>")


def to_pcm16(chunk: Any) -> bytes:
    """Convert a float audio chunk in [-1, 1] (torch tensor or array) to 16-bit PCM."""
    if hasattr(chunk, "detach"):
        chunk = chunk.detach().cpu().numpy()
    samples = np.clip(np.asarray(chunk, dtype=np.float32).reshape(-1), -1.0, 1.0)
    return (samples * 32767).astype(np.int16).tobytes()


@dataclass
class BilingualPocketTTSSettings(TTSSettings):
    """Settings for BilingualPocketTTSService (only ``voice`` is used)."""


class BilingualPocketTTSService(TTSService):
    Settings = BilingualPocketTTSSettings
    _settings: Settings

    def __init__(self, *, models: Mapping[str, Any], states: VoiceStates, voice: str, **kwargs):
        settings = self.Settings(model=None, voice=voice, language=None)
        super().__init__(
            push_start_frame=True,
            push_stop_frames=True,
            settings=settings,
            **kwargs,
        )
        self._models = models
        self._states = states
        self._sample_rate_in = next(iter(models.values())).sample_rate
        # Never end a sentence inside <es>...</es>, so each piece keeps whole tags.
        self._text_aggregator = SkipTagsAggregator(
            [ES_TAGS],
            aggregation_type=self._text_aggregation_mode,
            language=self._text_aggregator.language,
        )

    def can_generate_metrics(self) -> bool:
        return True

    async def _update_settings(self, delta: Settings) -> dict[str, Any]:
        changed = await super()._update_settings(delta)
        if "voice" in changed:
            logger.info(f"Voice switched to {self._settings.voice}")
        return changed

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        voice = str(self._settings.voice)
        text = remove_turn_markers(text)
        if not text:
            return
        chunks = iter_bilingual_audio(
            self._models, lambda lang: self._states.get(lang, voice), text
        )

        def next_chunk():
            return next(chunks, None)

        async def pcm() -> AsyncIterator[bytes]:
            while True:
                chunk = await asyncio.to_thread(next_chunk)
                if chunk is None:
                    return
                yield to_pcm16(chunk)

        try:
            await self.start_tts_usage_metrics(text)
            async for frame in self._stream_audio_frames_from_iterator(
                pcm(), in_sample_rate=self._sample_rate_in, context_id=context_id
            ):
                await self.stop_ttfb_metrics()
                yield frame
        except Exception as e:
            logger.error(f"{self} exception: {e}")
            yield ErrorFrame(error=f"Voice error: {e}")
        finally:
            await self.stop_ttfb_metrics()
