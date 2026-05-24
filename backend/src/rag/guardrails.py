"""
Guardrails — input validation and output quality checks.

Input guardrails:
  - Detect prompt injection attempts (jailbreak patterns)
  - Reject empty or excessively long queries

Output guardrails:
  - Flag low-confidence / hallucination signals ("I don't know", "As an AI…")
  - Truncate runaway responses
"""
import re
from typing import Tuple

# ── Prompt injection / jailbreak patterns ────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+(a|an|the)\s+\w+",
    r"act\s+as\s+(if\s+you\s+(are|were)\s+)?\w+",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+(your\s+)?(system\s+)?prompt",
    r"forget\s+(your\s+)?(previous\s+)?instructions?",
    r"pretend\s+(you\s+are|to\s+be)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# ── Hallucination / low-confidence signals in output ─────────────────────────
_HALLUCINATION_SIGNALS = [
    "i don't actually know",
    "i cannot verify",
    "i'm not sure but",
    "i may be wrong",
    "as of my knowledge cutoff",
    "i don't have access to real-time",
    "i must clarify that i am an ai",
    "as an ai language model",
]

MAX_INPUT_CHARS = 2000
MAX_OUTPUT_CHARS = 8000


def validate_input(text: str) -> Tuple[bool, str]:
    """
    Returns (is_safe, reason).
    is_safe=True means the input passed all checks.
    """
    text = text.strip()

    if not text:
        return False, "Query cannot be empty."

    if len(text) > MAX_INPUT_CHARS:
        return False, f"Query too long ({len(text)} chars). Maximum is {MAX_INPUT_CHARS}."

    if _INJECTION_RE.search(text):
        return False, "Query flagged by input guardrails. Please ask a genuine question."

    return True, ""


def validate_output(text: str) -> Tuple[str, list[str]]:
    """
    Returns (cleaned_text, warnings).
    Truncates runaway responses and flags hallucination signals.
    """
    warnings = []

    # Truncate if absurdly long
    if len(text) > MAX_OUTPUT_CHARS:
        text = text[:MAX_OUTPUT_CHARS] + "\n\n[Response truncated for length.]"
        warnings.append("Response was truncated.")

    # Flag hallucination signals (non-blocking, just annotated)
    lower = text.lower()
    for signal in _HALLUCINATION_SIGNALS:
        if signal in lower:
            warnings.append("Response may contain uncertain or unverifiable content.")
            break

    return text, warnings
