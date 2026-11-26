# Phase 0: test each part on your own machine

Goal: measure every part alone before wiring them together, so the design rests on your
numbers instead of someone else's benchmarks. Expect one or two evenings.

Assumes Windows 11, an NVIDIA RTX 4060 (8 GB) and Python 3.12.

## 1. Install the basics

1. **NVIDIA driver**: a recent Game Ready or Studio driver. Check with `nvidia-smi`.
2. **Python 3.12** from python.org (Kokoro does not support 3.13 yet). Tick "Add to PATH".
3. **uv** (fast Python package manager): `pip install uv`
4. **espeak-ng**: download the `.msi` from the
   [espeak-ng releases](https://github.com/espeak-ng/espeak-ng/releases). Kokoro uses it
   for Spanish pronunciation.
5. **llama.cpp**: download the Windows CUDA build (`llama-*-bin-win-cuda-*-x64.zip`) from the
   [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) and unzip it,
   for example to `C:\tools\llama.cpp`.

## 2. Set up the project

```powershell
git clone https://github.com/Ahmed-Yassine-Hajjaji/spanish-companion
cd spanish-companion
uv venv --python 3.12
.venv\Scripts\activate
uv pip install -e ".[phase0,dev]"
```

For the GPU tests (Whisper on CUDA, `bench_tts.py --device cuda`), swap in the CUDA build
of PyTorch and NVIDIA's libraries:

```powershell
uv pip install torch --index-url https://download.pytorch.org/whl/cu128
uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

Whisper on Windows also needs those libraries' DLL folders on `PATH`
(`.venv\Lib\site-packages\nvidia\*\bin`).

If PowerShell refuses to run `activate`, call `.venv\Scripts\python.exe` directly, or allow
local scripts once with `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

The first runs download models from Hugging Face (Parakeet about 2.5 GB, Whisper turbo
about 1.6 GB, Kokoro about 330 MB). They are cached, and nothing is uploaded.

## 3. Run the checks

```powershell
python scripts/phase0/check_gpu.py        # free VRAM, and what is using it
python scripts/phase0/record_samples.py   # record the 20 test sentences (about 5 minutes)
python scripts/phase0/bench_stt.py        # Parakeet vs Whisper on your voice
python scripts/phase0/bench_tts.py        # Kokoro, English + Spanish voices, on the CPU
python scripts/phase0/bench_tts.py --device cuda
python scripts/phase0/bench_tts.py --device cuda --voice ef_dora   # compare voices
python scripts/phase0/bench_pocket_tts.py                       # the chosen voice, "eve"
```

For the language model, download a **text-only** Qwen 3.5 9B GGUF at `Q4_K_M` (search
Hugging Face for "Qwen3.5-9B GGUF"; avoid builds that bundle the vision projector, which
costs about 1.4 GB extra VRAM) into `models/`, then in a second terminal:

```powershell
C:\tools\llama.cpp\llama-server.exe -m models\Qwen3.5-9B-Q4_K_M.gguf -ngl 99 -c 8192 --jinja --port 8080
```

and back in the first one:

```powershell
python scripts/phase0/check_gpu.py
python scripts/phase0/bench_llm.py
```

## 4. What to look for

| Part | Good result | If not |
| --- | --- | --- |
| Language model | first sentence under 0.8 s, 35+ tokens/s | check it is fully on the GPU (`-ngl 99`) and not thinking |
| Speech recognition | under 0.4 s per sentence, few errors on your Spanish | compare engines; try `--no-prompt` and `--whisper-device cpu` |
| Voice | first audio under 0.2 s, Spanish sounds right | try another `--voice`, or `--device cuda` |
| VRAM | about 1 GB free with the model loaded | shorter context (`-c 4096`), close other GPU apps |

Paste the summary lines from each script (and anything that failed) back into the
project thread, and we will choose the parts for phase 1 from those numbers.
