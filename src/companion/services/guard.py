"""Keep a "Correct." verdict short, even when the model wants to add more.

In rehearsal mode the user wants a one-word verdict for a correct phrase. The
model keeps padding it ("Correct. Great job! What's the next phrase?"), which
slows the rehearsal down and nudges the user. This processor sits between the
language model and the voice: once a reply starts with "Correct.", the rest of
that reply is dropped. Dropped text is never spoken, so it never reaches the
conversation history either, and the model sees itself answering briefly.
"""

from __future__ import annotations

from pipecat.frames.frames import (
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from companion.text import remove_turn_markers

VERDICT = "Correct."


class CorrectVerdictGuard(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reply = ""
        self._done = False

    def _reset(self) -> None:
        self._reply = ""
        self._done = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, (LLMFullResponseStartFrame, InterruptionFrame)):
            self._reset()
        elif isinstance(frame, LLMFullResponseEndFrame):
            self._reset()
        elif isinstance(frame, LLMTextFrame) and direction == FrameDirection.DOWNSTREAM:
            if self._done:
                return  # drop the padding after "Correct."
            self._reply += frame.text
            if remove_turn_markers(self._reply).startswith(VERDICT):
                self._done = True
                # This chunk holds the period that completes "Correct."; anything
                # after it in the same chunk is already padding.
                end = frame.text.find(".") + 1
                if 0 < end < len(frame.text):
                    frame = LLMTextFrame(frame.text[:end])
        await self.push_frame(frame, direction)
