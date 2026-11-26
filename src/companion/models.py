"""Load each model once per process and share it between calls.

Loading takes several seconds (and downloads on first use), so the bot preloads
everything at start-up instead of when you press "Connect".
"""

from __future__ import annotations

from functools import cache
from typing import Any

from loguru import logger

from companion.speech import POCKET_LANGUAGES, VoiceStates


@cache
def parakeet(model_name: str) -> Any:
    import onnx_asr

    logger.info(f"Loading speech recognition model {model_name} (CPU)")
    return onnx_asr.load_model(model_name)


@cache
def pocket_models() -> dict[str, Any]:
    from pocket_tts import TTSModel

    models = {}
    for lang, name in POCKET_LANGUAGES.items():
        logger.info(f"Loading Pocket TTS '{name}' model (CPU)")
        models[lang] = TTSModel.load_model(language=name)
    return models


@cache
def voice_states() -> VoiceStates:
    return VoiceStates(pocket_models())


def preload(stt_model: str, voices: tuple[str, ...]) -> None:
    parakeet(stt_model)
    voice_states().preload(voices)
    logger.info("All models loaded")
