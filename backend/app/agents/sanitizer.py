"""User content sanitization — prevents prompt injection before LLM context."""

from __future__ import annotations

import html
import re

_MAX_LENGTH = 32_000

_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|prior|all)\s+(instructions?|prompts?|context))"
    r"|(system\s*prompt|jailbreak|DAN\s+mode|developer\s+mode)"
    r"|(</?(system|human|assistant|user)>)"
    r"|(<<SYS>>|<<\/SYS>>|\[INST\]|\[\/INST\])",
    re.IGNORECASE,
)

_HTML_TAG = re.compile(r"<[^>]+>")
_MULTI_WHITESPACE = re.compile(r"\s{3,}")


def sanitize_user_content(text: str) -> str:
    """Strip HTML, detect injection attempts, limit length, normalise whitespace."""
    # 1. HTML-unescape entities first, then strip tags
    text = html.unescape(text)
    text = _HTML_TAG.sub(" ", text)

    # 2. Collapse excessive whitespace
    text = _MULTI_WHITESPACE.sub("  ", text).strip()

    # 3. Detect & neutralise injection patterns by wrapping in angle-brackets
    #    (makes the literal text visible to Claude without executing as instructions)
    def _neutralise(m: re.Match[str]) -> str:
        return f"[USER_TEXT: {m.group(0)}]"

    text = _INJECTION_PATTERNS.sub(_neutralise, text)

    # 4. Hard length cap
    if len(text) > _MAX_LENGTH:
        text = text[:_MAX_LENGTH] + "\n[…truncated]"

    return text
