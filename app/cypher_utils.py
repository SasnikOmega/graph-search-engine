import re

_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def validate_label(name: str) -> str:
    if not _LABEL_RE.match(name):
        raise ValueError(
            f"Invalid label {name!r}: use letters, digits, underscore; start with a letter."
        )
    return name


def validate_rel_type(name: str) -> str:
    if not _LABEL_RE.match(name):
        raise ValueError(
            f"Invalid relationship type {name!r}: use letters, digits, underscore; start with a letter."
        )
    return name


def format_labels_cypher(labels: list[str]) -> str:
    if not labels:
        raise ValueError("At least one label is required.")
    parts = [validate_label(l) for l in labels]
    return ":".join(parts)
