"""Phase 1: a live voice call with the Spanish companion, fully local.

Pipeline, in order:
  browser mic -> voice detection + Smart Turn -> Parakeet (CPU) -> Qwen 3.5 9B
  (llama.cpp, GPU) -> verdict guard -> Pocket TTS (CPU) -> browser speaker

Run it (with llama-server already running, see docs/phase1.md):
    python -m companion.bot
then open http://localhost:7860 and press Connect.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMMessagesAppendFrame, TTSUpdateSettingsFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.turns.user_turn_completion import USER_TURN_COMPLETE_MARKER, UserTurnCompletionConfig
from pipecat.turns.user_turn_strategies import FilterIncompleteUserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from companion import models, transcripts
from companion.config import VOICES, Settings
from companion.prompts import GREETING, NUDGE_LONG, NUDGE_SHORT, PERSONA
from companion.services.guard import CorrectVerdictGuard
from companion.services.stt import ParakeetSTTService
from companion.services.tts import BilingualPocketTTSService

TRANSPORT_PARAMS = {
    "webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
}


class LocalLLMService(OpenAILLMService):
    """OpenAI-compatible client for llama.cpp.

    Pipecat sometimes adds "developer" notes in the middle of a conversation (for
    example after an interruption with no words heard). Qwen's chat template only
    accepts a system message at the very start and fails with HTTP 500 otherwise,
    which broke every later turn of the call. Sending those notes as user messages
    avoids that.
    """

    supports_developer_role = False


def build_llm(settings: Settings) -> OpenAILLMService:
    """The language model client, talking to the local llama.cpp server."""
    return LocalLLMService(
        base_url=settings.llm_url,
        api_key="not-needed",
        settings=OpenAILLMService.Settings(
            model="local",
            system_instruction=PERSONA,
            # Low temperature: steadier corrections, no arguing with itself mid-reply.
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
            # Qwen-style models: no "thinking" in a live call, it adds seconds of delay.
            extra={
                "extra_body": {
                    "chat_template_kwargs": {"enable_thinking": False},
                    # llama.cpp: discourage the loops a small model can fall into.
                    "repeat_penalty": 1.1,
                }
            },
        ),
    )


async def switch_voice(params: FunctionCallParams, voice: str):
    """Switch the companion's speaking voice. Only call this when the user clearly
    asks for a different voice by name or says they want another voice.

    Args:
        voice: The voice to use, either "eve" or "alba".
    """
    voice = voice.strip().lower()
    if voice not in VOICES:
        await params.result_callback({"ok": False, "available": list(VOICES)})
        return
    await params.llm.push_frame(
        TTSUpdateSettingsFrame(delta=BilingualPocketTTSService.Settings(voice=voice))
    )
    await params.result_callback({"ok": True, "voice": voice})


def turn_strategies() -> FilterIncompleteUserTurnStrategies:
    """Let the language model judge whether the user finished their sentence.

    Smart Turn decides from the sound when the user paused, but a beginner speaking
    Spanish pauses mid-sentence a lot ("en el centro de la..."). On each pause the
    model first answers with a marker: complete, or cut off and still talking. Only a
    complete turn gets a reply, and the pieces of a cut-off sentence are judged together.
    """
    return FilterIncompleteUserTurnStrategies(
        config=UserTurnCompletionConfig(
            incomplete_short_timeout=6.0,
            incomplete_long_timeout=15.0,
            incomplete_short_prompt=NUDGE_SHORT.format(complete=USER_TURN_COMPLETE_MARKER),
            incomplete_long_prompt=NUDGE_LONG.format(complete=USER_TURN_COMPLETE_MARKER),
        )
    )


def new_context() -> LLMContext:
    return LLMContext(tools=[switch_voice])


async def run_call(transport: BaseTransport, settings: Settings, handle_sigint: bool) -> None:
    stt = ParakeetSTTService(
        model=models.parakeet(settings.stt_model), ttfs_p99_latency=settings.pause_secs + 1.2
    )
    llm = build_llm(settings)
    tts = BilingualPocketTTSService(
        models=models.pocket_models(), states=models.voice_states(), voice=settings.voice
    )
    context = new_context()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=settings.pause_secs)),
            user_turn_strategies=turn_strategies(),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            CorrectVerdictGuard(),
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    started = datetime.now()

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        nonlocal started
        started = datetime.now()
        logger.info("Call started")
        await worker.queue_frames(
            [LLMMessagesAppendFrame(messages=[{"role": "user", "content": GREETING}], run_llm=True)]
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Call ended")
        try:
            path = transcripts.save_call(
                context.get_messages(), settings.calls_dir, started=started, skip=[GREETING]
            )
            if path:
                logger.info(f"Saved the conversation to {path}")
        except OSError as e:
            logger.warning(f"Could not save the conversation: {e}")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=handle_sigint)
    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Entry point called by the Pipecat runner for each new call."""
    transport = await create_transport(runner_args, TRANSPORT_PARAMS)
    await run_call(transport, Settings(), runner_args.handle_sigint)


def main() -> None:
    from pipecat.runner.run import main as run_server

    settings = Settings()
    models.preload(settings.stt_model, VOICES)
    run_server()


if __name__ == "__main__":
    main()
