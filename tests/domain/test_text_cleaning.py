from src.domain.text_cleaning import clean_extracted_text


def test_collapses_horizontal_whitespace_and_trims_lines() -> None:
    assert clean_extracted_text("  Hola\t\tmundo  \n   segunda   linea  ") == (
        "Hola mundo\nsegunda linea"
    )


def test_normalizes_windows_and_old_mac_line_endings() -> None:
    assert clean_extracted_text("uno\r\ndos\rtres") == "uno\ndos\ntres"


def test_removes_control_characters() -> None:
    assert clean_extracted_text("uno\x00dos\x07tres\x7f") == "unodostres"


def test_applies_unicode_nfkc_normalization() -> None:
    assert clean_extracted_text("ＡＢＣ ﬁ") == "ABC fi"


def test_converts_non_breaking_spaces_to_regular_spaces() -> None:
    assert clean_extracted_text("Hola\u00a0mundo") == "Hola mundo"


def test_collapses_multiple_blank_lines_into_one() -> None:
    assert clean_extracted_text("uno\n\n\n\ndos") == "uno\n\ndos"


def test_keeps_accents_and_language_characters() -> None:
    assert clean_extracted_text("Ingeniería de software en Perú") == (
        "Ingeniería de software en Perú"
    )


def test_empty_text_stays_empty() -> None:
    assert clean_extracted_text("") == ""
    assert clean_extracted_text("  \n\t \n ") == ""
