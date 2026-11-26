"""Settings for a call, read from environment variables with sensible defaults.

Every setting can be changed without touching code, for example in PowerShell:
    $env:COMPANION_VOICE = "alba"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Voices the companion may switch between during a call (Pocket TTS catalog names).
VOICES = ("eve", "alba")


@dataclass(frozen=True)
class Settings:
    # Local llama.cpp server (OpenAI-compatible API).
    llm_url: str = field(
        default_factory=lambda: os.getenv("COMPANION_LLM_URL", "http://localhost:8080/v1")
    )
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("COMPANION_LLM_MAX_TOKENS", "160"))
    )
    # Voice used when a call starts.
    voice: str = field(default_factory=lambda: os.getenv("COMPANION_VOICE", "eve"))
    # Speech recognition model (onnx-asr name).
    stt_model: str = field(
        default_factory=lambda: os.getenv("COMPANION_STT_MODEL", "nemo-parakeet-tdt-0.6b-v3")
    )

    def __post_init__(self) -> None:
        if self.voice not in VOICES:
            raise ValueError(f"COMPANION_VOICE must be one of {VOICES}, got {self.voice!r}")
