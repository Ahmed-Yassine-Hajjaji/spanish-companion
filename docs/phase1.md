# Phase 1: the first live call

Goal: talk to the companion in your browser, interrupt it, and hear it answer in
under a second, with Spanish spoken by the same voice as the English.

## What runs where

| Part | Model | Runs on |
| --- | --- | --- |
| Voice detection + end-of-turn | Silero VAD + Smart Turn v3 | CPU |
| Speech recognition | Parakeet TDT 0.6B v3 (`companion/services/stt.py`) | CPU |
| Language model | Qwen 3.5 9B Q4_K_M in llama.cpp | GPU |
| Voice | Pocket TTS, English + Spanish models, voice `eve` or `alba` (`companion/services/tts.py`) | CPU |
| Call page | Pipecat's built-in browser page (local WebRTC) | Browser |

## Setup (once)

From the project folder, in the existing environment:

```powershell
uv pip install -e ".[call,dev]"
```

## Start a call

1. **Start the language model** in its own PowerShell window, and leave it open:

   ```powershell
   C:\tools\llama.cpp\llama-server.exe -m models\Qwen3.5-9B-Q4_K_M.gguf -ngl 99 -c 8192 --jinja --port 8080
   ```

   `--jinja` is needed for the voice-switch tool.

2. **Start the companion** in a second window:

   ```powershell
   .venv\Scripts\python.exe -m companion.bot
   ```

   It loads the speech and voice models first (a few seconds), then prints
   `Bot ready!`.

3. **Open http://localhost:7860** in Chrome or Edge, allow the microphone, and press
   **Connect**. Use a headset, so the companion does not hear itself.

## Things to try

Sol follows your lead: it chats about what you bring up and does not quiz you
unless you ask it to.

- Just chat. Interrupt it mid-sentence: it should stop and listen.
- Rehearse: "I have a presentation about daily life in Alicante. I'll say my phrases
  one by one, correct me if I'm wrong." Then say each phrase. Sol says whether it's
  right, or gives the fix in one sentence, and waits for the next one.
- "What does *la vida diaria* mean?" or "How do I say thank you in Spanish?"
- "Can you switch to Alba?" changes the voice for the rest of the call.
- Start with Alba: `$env:COMPANION_VOICE = "alba"` before step 2.

## Settings

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `COMPANION_VOICE` | `eve` | Voice at the start of a call (`eve` or `alba`) |
| `COMPANION_LLM_URL` | `http://127.0.0.1:8080/v1` | llama.cpp server address (an IP, because `localhost` can stall on IPv6 on Windows) |
| `COMPANION_LLM_MAX_TOKENS` | `160` | Longest reply, in tokens |
| `COMPANION_PAUSE_SECS` | `0.8` | Silence before a pause may end your turn. Raise it (for example `1.2`) if Sol jumps in while you think |
| `COMPANION_CALLS_DIR` | `data\calls` | Where each call's conversation is saved |
| `COMPANION_STT_MODEL` | `nemo-parakeet-tdt-0.6b-v3` | Speech recognition model |

## Known limits of phase 1

- The transcript on the call page shows the `<es>` tags around Spanish words.
- Each call's conversation is saved to `data\calls\<date>.json` on your PC, but the
  companion does not read it back yet: memory and mistake review come in phases 2 and 3.
- Speech recognition sometimes mishears Spanish from a beginner (for example "diaria"
  as "diarrhea"). Sol is told to guess the likely word from context.
- Interruption can be triggered by loud background noise; a headset helps.

## Done when

You can talk for 5 minutes, interrupt it, and it answers in about a second.
