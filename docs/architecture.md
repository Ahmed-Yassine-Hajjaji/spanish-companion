# Architecture

The companion is a pipeline of small, swappable parts. The GPU (8 GB) runs the language
model and the voice; speech recognition and turn detection run on the CPU. The split comes
from the [phase 0 measurements](phase0-results.md).

```mermaid
flowchart LR
    subgraph Live call
        A[Browser call page<br/>mic, speaker, subtitles] --> B[Turn detection<br/>Silero VAD + Smart Turn, CPU]
        B --> C[Speech recognition<br/>Parakeet 0.6B v3, CPU]
        C --> D[Tutor logic<br/>Python, Pipecat]
        D --> E[Language model<br/>Qwen 3.5 9B, GPU]
        E --> F[Voice<br/>Kokoro 82M, GPU]
        F --> A
        B -. barge-in: stop talking .-> F
    end
    D --> G[(Memory<br/>SQLite + FSRS)]
    D --> H[Grammar check<br/>LanguageTool]
    D --> I[Notes folder<br/>Markdown, Anki]
```

## Memory budget (RTX 4060, 8 GB)

| Part | Runs on | Memory |
| --- | --- | --- |
| Language model, Qwen 3.5 9B Q4_K_M, 8K context | GPU | 6.3 GB VRAM (measured) |
| Windows desktop, browser | GPU | 0.3 to 0.8 GB VRAM |
| Speech recognition, Parakeet 0.6B v3 | CPU | about 2 GB RAM |
| Voice, Kokoro 82M | GPU | 421 MiB VRAM |
| Turn detection | CPU | under 100 MB |

## Latency target

End of the user's sentence to the companion's first word: about 0.75 s, adding up the
measured stages (turn detection 0.25 s, recognition 0.17 s, first sentence 0.22 s,
first audio 0.09 s). The voice starts on the first sentence while the model is still
writing the rest.

## Key design rules

- **The model chooses, the code acts.** The model never writes files or touches the
  database; it asks for a named tool and Python code does the work.
- **Corrections are checked twice.** A separate, structured correction check plus a
  LanguageTool second opinion; if they disagree, no correction is given.
- **Never blame the learner for the recognizer.** Low recognition confidence means
  "say that again", not a correction.
- **Spanish is tagged.** The model wraps Spanish in `<es>...</es>` so each part goes
  through the right pronunciation pipeline (`companion/text.py`), always in the same voice.
