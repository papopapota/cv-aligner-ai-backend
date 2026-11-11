import re
import unicodedata

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HORIZONTAL_WHITESPACE = re.compile(r"[ \t\f\v]+")


def clean_extracted_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _CONTROL_CHARACTERS.sub("", normalized)

    lines = [
        _HORIZONTAL_WHITESPACE.sub(" ", line).strip()
        for line in normalized.split("\n")
    ]

    cleaned_lines: list[str] = []
    previous_was_blank = False
    for line in lines:
        if line:
            cleaned_lines.append(line)
            previous_was_blank = False
            continue
        if not previous_was_blank:
            cleaned_lines.append("")
            previous_was_blank = True

    return "\n".join(cleaned_lines).strip()
