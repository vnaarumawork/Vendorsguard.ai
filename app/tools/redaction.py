"""In-agent PII / IP redaction tool.

This is the "Security & Guardrail" tool exposed to the Guardrail Agent.
It strips personally identifiable information and intellectual-property
markers (internal hostnames, secrets, keys) from a drafted answer BEFORE
the answer can leave the system.
"""

import re

# Each rule: (label, compiled regex, replacement token)
_REDACTION_RULES = [
    ("EMAIL", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[REDACTED_EMAIL]"),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"), "[REDACTED_API_KEY]"),
    ("GENERIC_SECRET", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"]?[A-Za-z0-9\-_/+]{8,}['\"]?"),
        "[REDACTED_SECRET]"),
    ("PRIVATE_KEY_BLOCK", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]"),
    ("INTERNAL_HOSTNAME", re.compile(
        r"\b[a-z0-9\-]+\.(internal|corp|local|intra)\.[a-z0-9\-.]+\b", re.IGNORECASE),
        "[REDACTED_INTERNAL_HOST]"),
    ("US_SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    ("PHONE", re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]


def redact_sensitive_content(text: str) -> dict:
    """Redact PII and intellectual property from a drafted questionnaire answer.

    Args:
        text: The drafted answer text to sanitize.

    Returns:
        dict with keys:
            redacted_text: the sanitized answer.
            redaction_count: total number of substitutions made.
            categories: list of redaction categories that fired.
    """
    redacted = text
    categories = []
    total = 0
    for label, pattern, replacement in _REDACTION_RULES:
        redacted, n = pattern.subn(replacement, redacted)
        if n:
            categories.append(label)
            total += n
    return {
        "redacted_text": redacted,
        "redaction_count": total,
        "categories": categories,
    }
