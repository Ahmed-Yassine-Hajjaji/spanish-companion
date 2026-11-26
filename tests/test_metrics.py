import pytest

from companion.metrics import normalize, summarize, word_error_rate


def test_normalize_spanish_punctuation():
    assert normalize("¿Dónde está el baño?") == ["dónde", "está", "el", "baño"]
    assert normalize("¿Dónde está?", keep_accents=False) == ["donde", "esta"]


def test_wer_perfect_and_errors():
    assert word_error_rate("yo tengo un perro", "Yo tengo un perro.") == 0.0
    assert word_error_rate("yo tengo un perro", "yo tener un perro") == pytest.approx(0.25)
    assert word_error_rate("yo tengo un perro", "tengo perro") == pytest.approx(0.5)


def test_wer_accents_optional():
    assert word_error_rate("café", "cafe") == 1.0
    assert word_error_rate("café", "cafe", keep_accents=False) == 0.0


def test_summarize():
    assert summarize([]) == "no data"
    assert summarize([1.0, 2.0, 3.0]).startswith("median 2.00")
