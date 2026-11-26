"""End-to-end test of the reply path: language model -> tool call -> voice.

A tiny fake llama.cpp server (OpenAI-compatible, streaming) stands in for Qwen, and
fake Pocket TTS models stand in for the voice, so this runs anywhere in a second.
"""

import json
import socket
import threading
import time

import pytest

pytest.importorskip("pipecat")
uvicorn = pytest.importorskip("uvicorn")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pipecat.frames.frames import LLMMessagesAppendFrame, TTSAudioRawFrame  # noqa: E402
from pipecat.pipeline.pipeline import Pipeline  # noqa: E402
from pipecat.processors.aggregators.llm_response_universal import (  # noqa: E402  # noqa: E402
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.tests.utils import SleepFrame, run_test  # noqa: E402

from companion.bot import build_llm, new_context, turn_strategies  # noqa: E402
from companion.config import Settings  # noqa: E402
from tests.test_services import make_tts  # noqa: E402


def chunk(delta, finish=None):
    body = {
        "id": "x",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "local",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(body)}\n\n"


def fake_server(requests_seen):
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def completions(request: Request):
        body = await request.json()
        requests_seen.append(body)
        has_tool_result = any(m.get("role") == "tool" for m in body["messages"])
        last_user = [m for m in body["messages"] if m["role"] == "user"][-1]["content"]

        def stream():
            if "presentation" in str(last_user):
                # Turn-completion marker first, as the turn protocol asks.
                for token in ["●", " Correct", "."]:
                    yield chunk({"content": token})
                yield chunk({}, "stop")
            elif not has_tool_result:
                call = {
                    "index": 0,
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "switch_voice", "arguments": '{"voice": "alba"}'},
                }
                yield chunk({"role": "assistant", "tool_calls": [call]})
                yield chunk({}, "tool_calls")
            else:
                for token in ["Done! I'm ", "<es>Alba</es> ", "now."]:
                    yield chunk({"content": token})
                yield chunk({}, "stop")
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


@pytest.fixture
def llm_url():
    requests_seen = []
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(fake_server(requests_seen), port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"http://127.0.0.1:{port}/v1", requests_seen
    server.should_exit = True
    thread.join(timeout=5)


async def test_voice_switch_by_request(llm_url):
    url, requests_seen = llm_url
    log = []
    llm = build_llm(Settings(llm_url=url))
    context = new_context()
    _, assistant = LLMContextAggregatorPair(context)
    pipeline = Pipeline([llm, make_tts(log), assistant])

    down, _ = await run_test(
        pipeline,
        frames_to_send=[
            LLMMessagesAppendFrame(
                messages=[{"role": "user", "content": "Can you switch to Alba?"}], run_llm=True
            ),
            SleepFrame(sleep=1.5),
        ],
        start_timeout=5,
    )

    # The persona was sent, the tool was offered, thinking was turned off,
    # and the reply came in Alba's voice.
    assert requests_seen[0]["messages"][0]["role"] == "system"
    assert "Sol" in requests_seen[0]["messages"][0]["content"]
    assert requests_seen[0]["tools"][0]["function"]["name"] == "switch_voice"
    assert requests_seen[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert ("es", "alba", "Alba") in log
    assert all(voice == "alba" for _, voice, _ in log)
    assert any(isinstance(f, TTSAudioRawFrame) for f in down)


async def test_turn_marker_is_not_spoken(llm_url):
    url, requests_seen = llm_url
    log = []
    llm = build_llm(Settings(llm_url=url))
    context = new_context()
    user, assistant = LLMContextAggregatorPair(
        context, user_params=LLMUserAggregatorParams(user_turn_strategies=turn_strategies())
    )
    pipeline = Pipeline([user, llm, make_tts(log), assistant])

    await run_test(
        pipeline,
        frames_to_send=[
            SleepFrame(sleep=0.3),
            LLMMessagesAppendFrame(
                messages=[{"role": "user", "content": "My presentation starts now."}],
                run_llm=True,
            ),
            SleepFrame(sleep=1.5),
        ],
        start_timeout=5,
    )

    # The model was told to judge whether the user finished, and the marker it
    # answered with was not read aloud.
    assert "TURN COMPLETION" in requests_seen[-1]["messages"][0]["content"]
    spoken = " ".join(text for _, _, text in log)
    assert "Correct." in spoken
    assert "●" not in spoken
