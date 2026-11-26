import json
from datetime import datetime

from companion.transcripts import call_turns, save_call

MESSAGES = [
    {"role": "user", "content": "Start the call"},
    {"role": "assistant", "content": "Hi! <es>Hola</es>. What shall we do?"},
    {"role": "user", "content": "Correct my presentation phrases."},
    {"role": "assistant", "tool_calls": [{"id": "1"}], "content": None},
    {"role": "tool", "content": '{"ok": true}'},
    {"role": "user", "content": [{"type": "text", "text": "Yo soy estudiante."}]},
    {"role": "assistant", "content": "That's right."},
]


def test_call_turns_keeps_spoken_text_only():
    turns = call_turns(MESSAGES, skip=["Start the call"])
    assert turns == [
        {"role": "assistant", "text": "Hi! <es>Hola</es>. What shall we do?"},
        {"role": "user", "text": "Correct my presentation phrases."},
        {"role": "user", "text": "Yo soy estudiante."},
        {"role": "assistant", "text": "That's right."},
    ]


def test_save_call_writes_json(tmp_path):
    started = datetime(2026, 11, 26, 3, 0, 0)
    path = save_call(MESSAGES, tmp_path / "calls", started=started, skip=["Start the call"])
    assert path.name == "2026-11-26_03-00-00.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["started"] == "2026-11-26T03:00:00"
    assert len(record["turns"]) == 4


def test_save_call_skips_calls_without_user_speech(tmp_path):
    messages = [
        {"role": "user", "content": "Start the call"},
        {"role": "assistant", "content": "Hi"},
    ]
    assert save_call(messages, tmp_path, started=datetime.now(), skip=["Start the call"]) is None
