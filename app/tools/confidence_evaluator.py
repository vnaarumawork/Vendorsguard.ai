"""Confidence & Compliance Evaluator — the custom Agent Skill.

Scores a drafted questionnaire answer 0-100 using deterministic heuristics
so that scoring is reproducible and auditable (a judge can re-run it and get
the same number). Answers scoring below the threshold are routed to the
Human-in-the-Loop triage portal instead of being auto-approved.

Scoring dimensions:
  +40  Grounding    — answer overlaps with the question's key terms
  +25  Citation     — answer references a policy/source document
  +20  Specificity  — concrete controls named (AES-256, TLS 1.2+, SOC 2...)
  -up to 25  Hedging — "we believe", "probably", "not sure", "TODO"
  -15  Placeholder  — unresolved template markers remain
"""

import re

CONFIDENCE_THRESHOLD = 85

_HEDGE_WORDS = [
    "probably", "we believe", "we think", "not sure", "unsure", "might",
    "possibly", "unclear", "unknown", "cannot confirm", "no information",
    "i don't know", "todo", "tbd", "n/a",
]

_SPECIFICITY_MARKERS = [
    "aes-256", "aes 256", "tls 1.2", "tls 1.3", "soc 2", "soc2", "iso 27001",
    "rbac", "mfa", "sso", "saml", "oauth", "kms", "encryption", "penetration test",
    "vulnerability scan", "audit log", "least privilege", "gdpr", "hipaa",
    "backup", "disaster recovery", "rto", "rpo", "incident response",
]

_CITATION_PATTERN = re.compile(r"(per|according to|as documented in|see|source:)\s+[\w\s]*"
                               r"(policy|document|soc\s?2|iso|handbook|\.md)", re.IGNORECASE)

_PLACEHOLDER_PATTERN = re.compile(r"(\[[A-Z_ ]{3,}\]|\{\{.*?\}\}|<insert.*?>|xxx+)", re.IGNORECASE)

_STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "you", "your", "how", "what",
    "when", "where", "which", "of", "in", "on", "at", "to", "for", "and", "or",
    "with", "any", "have", "has", "we", "our", "please", "describe",
}


def _keywords(text: str) -> set:
    words = re.findall(r"[a-z0-9\-]{3,}", text.lower())
    # normalize simple plurals so "scans" matches "scan", "tests" matches "test"
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in words if w not in _STOPWORDS}


def evaluate_answer_confidence(question: str, answer: str) -> dict:
    """Score a drafted security-questionnaire answer from 0 to 100.

    Args:
        question: The original questionnaire question.
        answer: The drafted (already-redacted) answer.

    Returns:
        dict with keys:
            confidence_score: int 0-100.
            verdict: "AUTO_APPROVED" or "REQUIRES_HUMAN_REVIEW".
            reasons: list of human-readable scoring notes.
    """
    reasons = []
    score = 0

    # Grounding: keyword overlap between question and answer
    q_kw, a_kw = _keywords(question), _keywords(answer)
    overlap = len(q_kw & a_kw) / max(len(q_kw), 1)
    grounding = round(40 * min(overlap * 2, 1.0))
    score += grounding
    reasons.append(f"Grounding: {grounding}/40 (keyword overlap {overlap:.0%})")

    # Citation of a source document
    if _CITATION_PATTERN.search(answer):
        score += 25
        reasons.append("Citation: 25/25 (references a policy/source document)")
    else:
        reasons.append("Citation: 0/25 (no source document referenced)")

    # Specificity: named security controls
    hits = [m for m in _SPECIFICITY_MARKERS if m in answer.lower()]
    specificity = min(len(hits) * 7, 20)
    score += specificity
    reasons.append(f"Specificity: {specificity}/20 (controls named: {', '.join(hits[:4]) or 'none'})")

    # Hedging penalty
    hedges = [h for h in _HEDGE_WORDS if h in answer.lower()]
    hedge_penalty = min(len(hedges) * 10, 25)
    if hedge_penalty:
        score -= hedge_penalty
        reasons.append(f"Hedging: -{hedge_penalty} (found: {', '.join(hedges[:3])})")

    # Unresolved placeholders (excluding our own redaction tokens)
    stripped = re.sub(r"\[REDACTED_[A-Z_]+\]", "", answer)
    if _PLACEHOLDER_PATTERN.search(stripped):
        score -= 15
        reasons.append("Placeholder: -15 (unresolved template markers remain)")

    # Very short answers are never high-confidence
    if len(answer.split()) < 15:
        score = min(score, 60)
        reasons.append("Length cap: answer under 15 words capped at 60")

    score = max(0, min(100, score))
    verdict = "AUTO_APPROVED" if score >= CONFIDENCE_THRESHOLD else "REQUIRES_HUMAN_REVIEW"
    return {"confidence_score": score, "verdict": verdict, "reasons": reasons}
