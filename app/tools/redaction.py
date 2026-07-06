import re

def redact_sensitive_content(text: str) -> dict:
    """
    Regex-redacts sensitive content from the input text.
    Redacts:
      - emails
      - IPv4 addresses
      - AWS access keys
      - Google API keys
      - generic secret assignments
      - private-key PEM blocks
      - internal hostnames (.internal/.corp/.local)
      - SSNs
      - phone numbers

    Returns a dict with:
      - redacted_text (str)
      - redaction_count (int)
      - categories (list of str)
    """
    categories = set()
    count = 0
    redacted_text = text

    # Regex patterns
    patterns = {
        "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
        "aws_key": r"\bAKIA[0-9A-Z]{16}\b",
        "google_key": r"\bAIza[0-9A-Za-z-_]{35}\b",
        "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "ipv4": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "internal_hostname": r"\b[a-zA-Z0-9.-]+\.(?:internal|corp|local)\b",
        "secret_assignment": r"(?i)\b(password|passwd|secret|token|api_key|apikey|private_key|privatekey)\s*=\s*(['\"])(.*?)\2"
    }

    # Process each pattern
    for cat, pattern in patterns.items():
        if cat == "secret_assignment":
            matches = re.findall(pattern, redacted_text)
            if matches:
                count += len(matches)
                categories.add(cat)
                redacted_text = re.sub(
                    pattern,
                    lambda m: f"{m.group(1)} = {m.group(2)}[REDACTED_{cat.upper()}]{m.group(2)}",
                    redacted_text
                )
        else:
            matches = re.findall(pattern, redacted_text)
            if matches:
                count += len(matches)
                categories.add(cat)
                redacted_text = re.sub(pattern, f"[REDACTED_{cat.upper()}]", redacted_text)

    return {
        "redacted_text": redacted_text,
        "redaction_count": count,
        "categories": sorted(list(categories))
    }
