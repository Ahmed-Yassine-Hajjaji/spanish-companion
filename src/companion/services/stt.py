"""Speech recognition with NVIDIA Parakeet TDT 0.6B v3, run on the CPU via onnx-asr.

Parakeet recognizes English, Spanish and French and picks the language by itself.
Pipecat's voice detection cuts the audio into one segment per sentence, and each
segment is transcribed in one call (about 0.17 s per sentence on a Ryzen 7 X3D).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import numpy as np
from loguru import logger
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.utils.time import time_now_iso8601

SAMPLE_RATE = 16_000


class ParakeetSTTService(SegmentedSTTService):
    """Transcribes each spoken segment with a shared, preloaded onnx-asr model."""

    @property
    def wants_wav_segments(self) -> bool:
        """Receive raw 16-bit PCM, which we convert to float ourselves."""
        return False

    @property
    def segment_sample_rate(self) -> int:
        return SAMPLE_RATE

    def __init__(self, *, model: Any, **kwargs):
        super().__init__(**kwargs)
        self._model = model

    def can_generate_metrics(self) -> bool:
        return True

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        await self.start_processing_metrics()
        waveform = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        text = await asyncio.to_thread(self._model.recognize, waveform, sample_rate=SAMPLE_RATE)
        await self.stop_processing_metrics()
        text = (text or "").strip()
        if text:
            logger.debug(f"Heard: [{text}]")
            yield TranscriptionFrame(text, self._user_id, time_now_iso8601(), None)
