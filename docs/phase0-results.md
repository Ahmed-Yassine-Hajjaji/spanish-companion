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
- **Voice: Kokoro on the GPU.** 421 MiB buys a 4x faster first sound (0.09 s vs 0.40 s).
  Model plus voice use about 6.7 GB, leaving about 1.2 GB free.
- **One voice for both languages.** The Kokoro voice is independent of the language
  pipeline, so English and Spanish are spoken by the same voice.
- **Language model: Qwen 3.5 9B as planned.** It is faster than the 35 to 45 tokens/s
  estimate.

Estimated time from end of speech to first word: about 0.25 s turn detection +
0.17 s recognition + 0.22 s first sentence + 0.09 s first audio = **about 0.75 s**.
