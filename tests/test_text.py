from companion.text import Segment, split_languages, strip_tags


def test_plain_english():
    assert split_languages("Hello there!") == [Segment("en", "Hello there!")]


def test_mixed():
    out = split_languages("Nice! In Spanish that's <es>muchas gracias</es>. Try it.")
    assert out == [
        Segment("en", "Nice! In Spanish that's"),
        Segment("es", "muchas gracias."),
        Segment("en", "Try it."),
    ]


def test_punctuation_only_part_is_merged():
    assert split_languages("Say <es>hola</es>!") == [Segment("en", "Say"), Segment("es", "hola!")]


def test_spanish_opening_marks_stay():
    assert split_languages("Ask: <es>¿Dónde está?</es>") == [
        Segment("en", "Ask:"),
        Segment("es", "¿Dónde está?"),
    ]


def test_unclosed_tag_runs_to_end():
    assert split_languages("Say <es>buenos días") == [
        Segment("en", "Say"),
        Segment("es", "buenos días"),
    ]


def test_stray_closing_tag_and_case():
    assert split_languages("Hi </es> <ES>hola</Es>") == [Segment("en", "Hi"), Segment("es", "hola")]


def test_adjacent_same_language_merged():
    assert split_languages("<es>uno</es><es>dos</es>") == [Segment("es", "uno dos")]


def test_strip_tags():
    assert strip_tags("Say <es>hola</es>!") == "Say hola !"
