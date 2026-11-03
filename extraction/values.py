"""Numbers as written in a filing, scale words, and checking that evidence really supports a value."""

from __future__ import annotations

import re

SCALES = {"units": 1, "thousands": 1e3, "millions": 1e6, "billions": 1e9}
NUMBER = re.compile(r"\(?-?\$?\s?\d[\d,]*(?:\.\d+)?\)?")


def parse_number(raw) -> float:
    if isinstance(raw, (int, float)):
        return raw
    s = str(raw).strip()
    negative = (s.startswith("(") and s.endswith(")")) or s.startswith("-")
    value = float(re.sub(r"[^\d.]", "", s))
    return -value if negative else value


def to_full_units(value: float, scale: str, field: str) -> float:
    """EPS is per share and never scaled; money is multiplied by its stated scale."""
    return value if field == "diluted_eps" else value * SCALES.get(scale, 1)


QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def _squash(s: str) -> str:
    """Whitespace collapsed and curly quotes straightened, so a faithful quote matches the filing."""
    return " ".join(s.translate(QUOTES).split())


def evidence_supports(evidence: str, value_as_written: float, source: str) -> bool:
    """True when the quoted evidence appears in the source text and contains the number itself."""
    if not evidence or _squash(evidence) not in _squash(source):
        return False
    numbers = [abs(parse_number(m)) for m in NUMBER.findall(evidence) if re.search(r"\d", m)]
    return any(abs(n - abs(value_as_written)) <= 1e-9 * max(1.0, abs(n)) for n in numbers)


def appears_in(truth: float, field: str, text: str) -> bool:
    """Whether the true value is printed in the text at any common scale (used to separate retrieval misses)."""
    found = {abs(parse_number(m)) for m in NUMBER.findall(text) if re.search(r"\d", m)}
    if field == "diluted_eps":
        return any(abs(n - abs(truth)) < 0.006 for n in found)
    return any(abs(n * scale - abs(truth)) <= 0.005 * abs(truth) for scale in (1, 1e3, 1e6, 1e9) for n in found)
