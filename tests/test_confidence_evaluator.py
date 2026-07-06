import pytest
from app.tools.confidence_evaluator import evaluate_answer_confidence
from app.tools.redaction import redact_sensitive_content

def test_strong_cited_answer_auto_approves():
    question = "How is customer data encrypted at rest?"
    # Answer has 16 words, keyword overlap (encrypt, data, rest), control (AES-256), citation (security_policy.md)
    # 1:We 2:encrypt 3:all 4:customer 5:data 6:at 7:rest 8:using 9:AES-256 10:in 11:strict 12:accordance 13:with 14:our 15:security_policy.md 16:document
    answer = "We encrypt all customer data at rest using AES-256 in strict accordance with our security_policy.md document."
    
    result = evaluate_answer_confidence(question, answer)
    assert result["score"] >= 85
    assert result["verdict"] == "AUTO_APPROVED"
    assert result["breakdown"]["keyword_overlap"] == 40
    assert result["breakdown"]["source_citation"] == 25
    assert result["breakdown"]["security_controls"] == 20
    assert result["breakdown"]["hedging_penalty"] == 0
    assert result["breakdown"]["placeholder_penalty"] == 0

def test_hedged_answer_requires_review():
    question = "Do you perform daily scans?"
    # Answer has 16 words but has multiple hedging phrases ("probably", "we believe", "TBD")
    answer = "We probably perform security scans on our systems daily, we believe, although this is TBD."
    
    result = evaluate_answer_confidence(question, answer)
    assert result["score"] < 85
    assert result["verdict"] == "REQUIRES_HUMAN_REVIEW"
    assert result["breakdown"]["hedging_penalty"] < 0

def test_short_answer_is_capped():
    question = "Is Multi-Factor Authentication (MFA) required for all employee access?"
    # Answer is under 15 words (3 words)
    answer = "Yes, we do."
    
    result = evaluate_answer_confidence(question, answer)
    assert result["score"] <= 60
    assert result["verdict"] == "REQUIRES_HUMAN_REVIEW"

def test_redaction_strips_planted_secrets():
    planted_text = (
        "Contact us at admin@company.com. "
        "The internal hostname is server-01.company.local and db.company.corp. "
        "The server is at 192.168.1.100. Key is AKIA1234567890123456. "  # nosemgrep # pragma: allowlist secret
        "Google API key is AIzaSyA123456789012345678901234567890ab. "  # nosemgrep # pragma: allowlist secret
        "password = 'super_secret_value'."  # nosemgrep # pragma: allowlist secret
    )
    
    redacted = redact_sensitive_content(planted_text)
    
    # Check that secrets are redacted
    assert "admin@company.com" not in redacted["redacted_text"]
    assert "server-01.company.local" not in redacted["redacted_text"]
    assert "db.company.corp" not in redacted["redacted_text"]
    assert "192.168.1.100" not in redacted["redacted_text"]
    assert "AKIA1234567890123456" not in redacted["redacted_text"]  # nosemgrep # pragma: allowlist secret
    assert "AIzaSyA123456789012345678901234567890ab" not in redacted["redacted_text"]  # nosemgrep # pragma: allowlist secret
    assert "super_secret_value" not in redacted["redacted_text"]  # nosemgrep # pragma: allowlist secret
    
    assert redacted["redaction_count"] > 0
    assert "email" in redacted["categories"]
    assert "ipv4" in redacted["categories"]
    assert "aws_key" in redacted["categories"]
    assert "google_key" in redacted["categories"]
    assert "secret_assignment" in redacted["categories"]
    assert "internal_hostname" in redacted["categories"]

def test_redaction_leaves_clean_text_untouched():
    clean_text = "This is a clean response with no sensitive credentials or keys."
    redacted = redact_sensitive_content(clean_text)
    
    assert redacted["redacted_text"] == clean_text
    assert redacted["redaction_count"] == 0
    assert len(redacted["categories"]) == 0
