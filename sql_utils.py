import re


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier or ""):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f"`{identifier}`"


def quote_qualified_identifier(identifier: str) -> str:
    parts = identifier.split(".")
    if not 1 <= len(parts) <= 2:
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return ".".join(quote_identifier(part) for part in parts)


def build_placeholders(values) -> str:
    values = list(values)
    if not values:
        raise ValueError("Cannot build SQL placeholders for an empty value list.")
    return ", ".join(["%s"] * len(values))
