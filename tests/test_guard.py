import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import (  # noqa: E402
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
)
from pipecat.tests.utils import run_test  # noqa: E402

from companion.services.guard import CorrectVerdictGuard  # noqa: E402


def reply(*tokens):
    return [
        LLMFullResponseStartFrame(),
        *(LLMTextFrame(t) for t in tokens),
        LLMFullResponseEndFrame(),
    ]


async def spoken(frames):
    down, _ = await run_test(CorrectVerdictGuard(), frames_to_send=frames)
    return "".join(f.text for f in down if isinstance(f, LLMTextFrame))


async def test_padding_after_correct_is_dropped():
    text = await spoken(reply("Correct", ".", " Great job", "! What's the next phrase?"))
    assert text == "Correct."


async def test_padding_in_the_same_chunk_is_cut():
    assert await spoken(reply("Correct. Great", " job!")) == "Correct."


async def test_other_replies_pass_untouched_and_state_resets():
    frames = reply("Correct", ".", " Nice!") + reply(
        "Almost: ", "<es>hace calor</es>.", " Calor is heat."
    )
    assert await spoken(frames) == "Correct.Almost: <es>hace calor</es>. Calor is heat."
