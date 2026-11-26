"""Qwen's chat template rejects a system/developer message after the first one."""

from pipecat.processors.aggregators.llm_context import LLMContext

from companion.bot import build_llm
from companion.config import Settings


async def test_mid_conversation_developer_notes_are_sent_as_user_messages():
    llm = build_llm(Settings())
    context = LLMContext(
        messages=[
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "developer", "content": "The user may have said something."},
            {"role": "user", "content": "Hello?"},
        ]
    )
    params = await llm.get_llm_adapter().get_llm_invocation_params(
        context,
        system_instruction=llm._settings.system_instruction,
        convert_developer_to_user=not llm.supports_developer_role,
    )
    roles = [m["role"] for m in params["messages"]]
    assert roles[0] == "system"
    assert "system" not in roles[1:] and "developer" not in roles
