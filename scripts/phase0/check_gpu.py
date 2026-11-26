"""Phase 0, step 1: show what the GPU has free before loading any model.

Usage:  python scripts/phase0/check_gpu.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys

FIELDS = "name,driver_version,memory.total,memory.used,memory.free"
MODEL_NEEDS_MIB = 6_400  # Qwen 3.5 9B Q4_K_M with 8K context, measured at about 6.2 GB


def main() -> int:
    if shutil.which("nvidia-smi") is None:
        print("nvidia-smi not found. Install the NVIDIA driver first.")
        return 1
    out = subprocess.run(
        ["nvidia-smi", f"--query-gpu={FIELDS}", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    name, driver, total, used, free = [x.strip() for x in out.splitlines()[0].split(",")]
    print(f"GPU:    {name} (driver {driver})")
    print(f"VRAM:   {int(total):,} MiB total, {int(used):,} used, {int(free):,} free")
    if int(free) < MODEL_NEEDS_MIB:
        print(
            f"\nWarning: under {MODEL_NEEDS_MIB:,} MiB free. Close GPU-heavy apps "
            "(games, browsers with many tabs, other AI tools) before a call."
        )
    else:
        print("\nEnough free VRAM for the language model.")

    print("\nTop GPU users right now:")
    apps = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=process_name,used_memory", "--format=csv,noheader"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(apps or "  (no compute processes; Windows desktop use is not listed here)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
