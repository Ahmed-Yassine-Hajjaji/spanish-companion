"""Small measurement helpers used by the benchmarks."""

from __future__ import annotations

import re
import statistics
import unicodedata

_PUNCT = re.compile(r"[^\w\s']", re.UNICODE)


def normalize(text: str, keep_accents: bool = True) -> list[str]:
    """Lowercase, drop punctuation (including ¿ and ¡) and split into words."""
    text = unicodedata.normalize("NFC", text.lower())
    if not keep_accents:
        text = "".join(
            c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
        )
    return _PUNCT.sub(" ", text).split()


def word_error_rate(reference: str, hypothesis: str, keep_accents: bool = True) -> float:
    """Word error rate: (substitutions + deletions + insertions) / words in the reference."""
    ref = normalize(reference, keep_accents)
    hyp = normalize(hypothesis, keep_accents)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, start=1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


def summarize(values: list[float]) -> str:
    """'median 0.42 (min 0.30, max 0.61)' for a list of seconds or rates."""
    if not values:
        return "no data"
    return f"median {statistics.median(values):.2f} (min {min(values):.2f}, max {max(values):.2f})"
