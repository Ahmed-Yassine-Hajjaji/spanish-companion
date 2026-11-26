"""Phase 1: a live voice call with the Spanish companion, fully local.

Pipeline, in order:
  browser mic -> voice detection + Smart Turn -> Parakeet (CPU) -> Qwen 3.5 9B
  (llama.cpp, GPU) -> Pocket TTS (CPU) -> browser speaker

Run it (with llama-server already running, see docs/phase1.md):
    python -m companion.bot
then open http://localhost:7860 and press Connect.
"""

from __future__ import annotations

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
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
from pipecat.workers.runner import WorkerRunner

from companion import models
from companion.config import VOICES, Settings
from companion.prompts import GREETING, PERSONA
from companion.services.stt import ParakeetSTTService
from companion.services.tts import BilingualPocketTTSService

TRANSPORT_PARAMS = {
    "webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
}


def build_llm(settings: Settings) -> OpenAILLMService:
    """The language model client, talking to the local llama.cpp server."""
    return OpenAILLMService(
        base_url=settings.llm_url,
        api_key="not-needed",
        settings=OpenAILLMService.Settings(
            model="local",
            system_instruction=PERSONA,
            temperature=0.7,
            max_tokens=settings.llm_max_tokens,
            # Qwen-style models: no "thinking" in a live call, it adds seconds of delay.
            extra={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
        ),
    )


async def switch_voice(params: FunctionCallParams, voice: str):
    """Switch the companion's speaking voice.

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


def new_context() -> LLMContext:
    return LLMContext(tools=[switch_voice])


async def run_call(transport: BaseTransport, settings: Settings, handle_sigint: bool) -> None:
    stt = ParakeetSTTService(model=models.parakeet(settings.stt_model))
    llm = build_llm(settings)
    tts = BilingualPocketTTSService(
        models=models.pocket_models(), states=models.voice_states(), voice=settings.voice
    )
    context = new_context()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Call started")
        await worker.queue_frames(
            [LLMMessagesAppendFrame(messages=[{"role": "user", "content": GREETING}], run_llm=True)]
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Call ended")
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
