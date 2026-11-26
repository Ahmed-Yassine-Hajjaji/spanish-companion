# Architecture

The companion is a pipeline of small, swappable parts. The GPU (8 GB) runs only the
language model; everything else runs on the CPU, because the model alone takes about 6 GB.

```mermaid
flowchart LR
    subgraph Live call
        A[Browser call page<br/>mic, speaker, subtitles] --> B[Turn detection<br/>Silero VAD + Smart Turn, CPU]
        B --> C[Speech recognition<br/>Parakeet 0.6B v3, CPU]
        C --> D[Tutor logic<br/>Python, Pipecat]
        D --> E[Language model<br/>Qwen 3.5 9B, GPU]
        E --> F[Voice<br/>Kokoro 82M, CPU]
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
| Language model, Qwen 3.5 9B Q4_K_M, 8K context | GPU | about 6.2 GB VRAM |
| Windows desktop, browser | GPU | 0.3 to 0.8 GB VRAM |
| Speech recognition, Parakeet 0.6B v3 | CPU | about 2 GB RAM |
| Voice, Kokoro 82M | CPU | under 1 GB RAM |
| Turn detection | CPU | under 100 MB |

## Latency target

End of the user's sentence to the companion's first word: about 1.0 to 1.7 s at first,
under 1.2 s after tuning. The voice starts on the first sentence while the model is still
writing the rest.

## Key design rules

- **The model chooses, the code acts.** The model never writes files or touches the
  database; it asks for a named tool and Python code does the work.
- **Corrections are checked twice.** A separate, structured correction check plus a
  LanguageTool second opinion; if they disagree, no correction is given.
- **Never blame the learner for the recognizer.** Low recognition confidence means
  "say that again", not a correction.
- **Spanish is tagged.** The model wraps Spanish in `<es>...</es>` so each part is spoken
  by a voice for its own language (`companion/text.py`).
