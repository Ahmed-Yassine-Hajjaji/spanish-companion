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

- Just chat. Interrupt it mid-sentence: it should stop and listen.
- "How do I say thank you in Spanish?", then try saying it back.
- "Can you switch to Alba?" changes the voice for the rest of the call.
- Start with Alba: `$env:COMPANION_VOICE = "alba"` before step 2.

## Settings

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `COMPANION_VOICE` | `eve` | Voice at the start of a call (`eve` or `alba`) |
| `COMPANION_LLM_URL` | `http://localhost:8080/v1` | llama.cpp server address |
| `COMPANION_LLM_MAX_TOKENS` | `160` | Longest reply, in tokens |
| `COMPANION_STT_MODEL` | `nemo-parakeet-tdt-0.6b-v3` | Speech recognition model |

## Known limits of phase 1

- The transcript on the call page shows the `<es>` tags around Spanish words.
- No memory between calls, no checked corrections yet (phase 2 and 3).
- Interruption can be triggered by loud background noise; a headset helps.

## Done when

You can talk for 5 minutes, interrupt it, and it answers in about a second.
