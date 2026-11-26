# Phase 0 results

Measured on 2026-11-26 on the target PC: Windows 10, AMD Ryzen 7 X3D, RTX 4060 8 GB
(driver 621.40), 64 GB DDR4. All numbers are medians, with the range in brackets.

## Language model

Qwen 3.5 9B, Q4_K_M text-only GGUF, llama.cpp b12751 (CUDA), `-ngl 99 -c 8192`.

| Measure | Result | Target |
| --- | --- | --- |
| Time to first token | 0.12 s (0.11 to 0.52) | |
| Time to first sentence | 0.22 s (0.14 to 0.60) | under 0.8 s |
| Generation speed | 42.6 tokens/s (40.7 to 43.3) | 35 or more |
| VRAM with model loaded | 6,279 MiB used, 1,678 MiB free | about 1 GB free |

No reasoning leaked into replies, `<es>` tags were used correctly, and it corrected
"Yo tener un perro" to "Tengo un perro".

## Voice (Kokoro 82M)

| Device | First audio | Real-time factor | VRAM |
| --- | --- | --- | --- |
| CPU | 0.40 s (0.38 to 0.57) | 0.24 | none |
| GPU | 0.09 s (0.05 to 0.11) | 0.06 | 421 MiB |

## More natural voices

Kokoro sounded robotic, so three more voice models were tested with the language model
loaded, one voice for both languages:

| Model | Runs on | First audio | Real-time factor | VRAM | Verdict |
| --- | --- | --- | --- | --- | --- |
| Pocket TTS (Kyutai, ~100M per language) | CPU | 0.08 s (0.07 to 0.09) | 0.26 | none | **Pick**: natural, real streaming |
| Pocket TTS | GPU | 0.04 s | 0.17 | 842 MiB | Not needed |
| Kokoro 82M | GPU | 0.09 s | 0.06 | 421 MiB | Fast fallback, robotic |
| Chatterbox Multilingual | GPU | 1.79 s (1.33 to 3.17) | 0.88 | 3.4 GB | Too slow; pushes the model out of VRAM |
| Qwen3-TTS 0.6B CustomVoice | GPU | about 8 s | about 2.0 | 1.1 to 2.3 GB | Far too slow without streaming |

Notes: Chatterbox and Qwen3-TTS have no real streaming in their pip packages, and take one
language per call or need their own environment because of pinned dependencies.
Chatterbox output is watermarked by design. Pocket TTS custom voice cloning needs
accepting Kyutai's terms on Hugging Face; the built-in catalog voices do not.

## Speech recognition (20 mixed English/Spanish/French recordings)

| Engine | Time per sentence | Real-time factor | Median WER (max) | VRAM |
| --- | --- | --- | --- | --- |
| Parakeet TDT 0.6B v3, CPU | 0.17 s (0.14 to 0.30) | 0.05 | 0% (75%) | none |
| Whisper large-v3-turbo, GPU | 0.46 s (0.45 to 0.50) | 0.13 | 0% (57%) | 1.1 GB |

Notable misses:

- **Parakeet:** "Hoy hace" heard as "Oh, ya ha"; "ser and estar" as "Sir and Star";
  a repeated "yo tener".
- **Whisper:** translated the French sentence into English, wrote "veinte" as "20",
  and heard "Hola" as "Hello". Those rewrites are worse for a tutor than plain
  mishearing, because they hide what the learner actually said.

## Decisions for phase 1

- **Speech recognition: Parakeet on the CPU.** It is faster, costs no VRAM and keeps
  what you said instead of translating or normalizing it.
- **Voice: Pocket TTS on the CPU.** More natural than Kokoro, streams its first audio in
  0.08 s, and uses no VRAM, so the GPU keeps about 1.7 GB of headroom.
- **One voice for both languages.** Each language has its own model, but both use the
  same catalog voice ("eve", chosen by ear), so English and Spanish are spoken by the same person.
- **Language model: Qwen 3.5 9B as planned.** It is faster than the 35 to 45 tokens/s
  estimate.

Estimated time from end of speech to first word: about 0.25 s turn detection +
0.17 s recognition + 0.22 s first sentence + 0.08 s first audio = **about 0.75 s**.
