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


def test_remove_turn_markers_handles_repeats():
    from companion.text import remove_turn_markers

    assert remove_turn_markers("● ● Correct.") == "Correct."
    assert remove_turn_markers("◐") == ""
    assert remove_turn_markers("●Almost: <es>Hola</es>.") == "Almost: <es>Hola</es>."


def test_untagged_spanish_questions_and_exclamations_are_spanish():
    from companion.text import Segment, split_languages

    assert split_languages("¡Hola! I'm great. ¿Cómo estás tú hoy? Tell me.") == [
        Segment("es", "¡Hola!"),
        Segment("en", "I'm great."),
        Segment("es", "¿Cómo estás tú hoy?"),
        Segment("en", "Tell me."),
    ]
    # Inside tags nothing changes.
    assert split_languages("Say <es>¡Hola!</es>") == [
        Segment("en", "Say"),
        Segment("es", "¡Hola!"),
    ]
