"""Pipeline tests for the local speech services, using fake models (no downloads)."""

import numpy as np
import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import (  # noqa: E402
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.tests.utils import run_test  # noqa: E402

from companion.services.tts import BilingualPocketTTSService, to_pcm16  # noqa: E402
from companion.speech import VoiceStates  # noqa: E402

SAMPLE_RATE = 24_000


class FakePocketModel:
    """Records what it was asked to say; returns 0.1 s of audio per call."""

    sample_rate = SAMPLE_RATE

    def __init__(self, lang, log):
        self.lang, self.log = lang, log

    def get_state_for_audio_prompt(self, voice):
        return voice

    def generate_audio_stream(self, state, text, copy_state=True):
        self.log.append((self.lang, state, text))
        yield np.full(SAMPLE_RATE // 10, 0.1, dtype=np.float32)


def make_tts(log, voice="eve"):
    models = {"en": FakePocketModel("en", log), "es": FakePocketModel("es", log)}
    return BilingualPocketTTSService(models=models, states=VoiceStates(models), voice=voice)


def llm_reply(*tokens):
    return [
        LLMFullResponseStartFrame(),
        *[LLMTextFrame(t) for t in tokens],
        LLMFullResponseEndFrame(),
    ]


async def test_spanish_goes_to_spanish_model_with_same_voice():
    log = []
    down, _ = await run_test(
        make_tts(log),
        frames_to_send=llm_reply(
            "Nice! In Spanish that's ", "<es>muchas ", "gracias</es>. Try it."
        ),
    )
    assert log == [
        ("en", "eve", "Nice!"),
        ("en", "eve", "In Spanish that's"),
        ("es", "eve", "muchas gracias."),
        ("en", "eve", "Try it."),
    ]
    assert any(isinstance(f, TTSAudioRawFrame) for f in down)


async def test_sentence_end_inside_spanish_is_not_split():
    log = []
    await run_test(
        make_tts(log), frames_to_send=llm_reply("Say <es>Hola. ¿Cómo ", "estás?</es> now.")
    )
    assert ("es", "eve", "Hola. ¿Cómo estás?") in log


async def test_voice_switch():
    log = []
    await run_test(
        make_tts(log),
        frames_to_send=[
            TTSUpdateSettingsFrame(delta=BilingualPocketTTSService.Settings(voice="alba")),
            *llm_reply("Hello there."),
        ],
    )
    assert log == [("en", "alba", "Hello there.")]


def test_to_pcm16_clips():
    pcm = np.frombuffer(to_pcm16(np.array([0.0, 2.0, -2.0], dtype=np.float32)), dtype=np.int16)
    assert pcm.tolist() == [0, 32767, -32767]


async def test_parakeet_service_emits_transcription():
    from companion.services.stt import ParakeetSTTService

    class FakeAsr:
        def recognize(self, waveform, sample_rate):
            assert waveform.dtype == np.float32 and sample_rate == 16_000
            return " yo tengo un perro "

    stt = ParakeetSTTService(model=FakeAsr())
    frames = [f async for f in stt.run_stt(np.zeros(1600, dtype=np.int16).tobytes())]
    assert [f.text for f in frames if isinstance(f, TranscriptionFrame)] == ["yo tengo un perro"]
    # One segment = one final transcript, so the turn logic never answers half a sentence.
    assert all(f.finalized for f in frames if isinstance(f, TranscriptionFrame))


async def test_parakeet_service_closes_empty_segments():
    from pipecat.frames.frames import TranscriptionFinalizedFrame

    from companion.services.stt import ParakeetSTTService

    class SilentAsr:
        def recognize(self, waveform, sample_rate):
            return ""

    stt = ParakeetSTTService(model=SilentAsr())
    frames = [f async for f in stt.run_stt(np.zeros(1600, dtype=np.int16).tobytes())]
    assert any(isinstance(f, TranscriptionFinalizedFrame) for f in frames)
    assert not any(isinstance(f, TranscriptionFrame) for f in frames)
