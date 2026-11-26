"""Hardware checks shared by the scripts."""

from __future__ import annotations

import shutil
import subprocess


def gpu_used_mib() -> int | None:
    """VRAM in use on the first GPU, in MiB, or None if nvidia-smi is missing."""
    if shutil.which("nvidia-smi") is None:
        return None
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
    )
    try:
        return int(out.stdout.strip().splitlines()[0])
    except (IndexError, ValueError):
        return None
