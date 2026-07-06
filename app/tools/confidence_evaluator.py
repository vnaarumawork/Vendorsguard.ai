import re

CONFIDENCE_THRESHOLD = 85

# Constants for scoring
STOPWORDS = {
    "what", "how", "why", "who", "where", "when", "do", "does", "is", "are", 
    "have", "has", "you", "your", "the", "a", "an", "and", "or", "in", "at", 
    "on", "of", "for", "to", "with", "about", "describe", "provide", "please", 
    "we", "our", "us", "it", "its", "that", "this", "they", "them", "their", 
    "any", "all", "some", "every", "can", "could", "should", "would", "will", 
    "shall", "may", "might", "must", "be", "been", "being", "am", "was", "were"
}

SECURITY_CONTROLS = [
    "aes-256", "aes256", "tls 1.2", "tls1.2", "tls 1.3", "tls1.3", 
    "soc 2", "soc2", "iso 27001", "iso27001", "mfa", "rbac", 
    "kms", "gke", "vpc", "mtls"
]

HEDGING_PHRASES = ["we believe", "probably", "tbd"]

PLACEHOLDER_PATTERN = r"\[[^\]]*\]|<[^>]*>|\bTODO\b|__+"
CITATION_PATTERN = r"(?i)\bper\s+[a-zA-Z0-9_\-\s]+policy\b|\b[a-zA-Z0-9_\-]+\.md\b"

def normalize_word(word: str) -> str:
    """
    Normalizes a word for comparison by lowercasing, stripping punctuation, 
    and resolving simple plurals.
    """
    word = word.lower().strip(".,;:?!'\"()[]{}")
    if len(word) <= 3:
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es"):
        if word.endswith("sses"):
            return word[:-2]
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word

def extract_keywords(text: str) -> set:
    """
    Extracts normalized keywords of length >= 3 from a text, ignoring stopwords.
    """
    words = re.findall(r"\b[a-zA-Z0-9_-]+\b", text)
    keywords = set()
    for w in words:
        normalized = normalize_word(w)
        if len(normalized) >= 3 and normalized not in STOPWORDS:
            keywords.add(normalized)
    return keywords

def evaluate_answer_confidence(question: str, answer: str) -> dict:
    """
    Scores the confidence of a security answer on a scale from 0 to 100
    based on overlap, citations, security controls, hedging, and placeholders.

    Returns:
        dict: {
            "score": int (0-100),
            "verdict": str ("AUTO_APPROVED" | "REQUIRES_HUMAN_REVIEW"),
            "breakdown": dict
        }
    """
    score = 0
    breakdown = {
        "keyword_overlap": 0,
        "source_citation": 0,
        "security_controls": 0,
        "hedging_penalty": 0,
        "placeholder_penalty": 0,
        "capped_by_length": False
    }

    # 1. Keyword Overlap (+40 max)
    q_keywords = extract_keywords(question)
    a_keywords = extract_keywords(answer)
    overlap = q_keywords.intersection(a_keywords)
    if overlap:
        score += 40
        breakdown["keyword_overlap"] = 40

    # 2. Source Citation (+25)
    if re.search(CITATION_PATTERN, answer):
        score += 25
        breakdown["source_citation"] = 25

    # 3. Security Controls (+20)
    has_control = any(control in answer.lower() for control in SECURITY_CONTROLS)
    if has_control:
        score += 20
        breakdown["security_controls"] = 20

    # 4. Hedging Phrases (-10 per occurrence, capped at -25)
    hedge_count = sum(answer.lower().count(hedge) for hedge in HEDGING_PHRASES)
    if hedge_count > 0:
        penalty = min(25, hedge_count * 10)
        score -= penalty
        breakdown["hedging_penalty"] = -penalty

    # 5. Unresolved Placeholders (-15)
    if re.search(PLACEHOLDER_PATTERN, answer):
        score -= 15
        breakdown["placeholder_penalty"] = -15

    # 6. Word Count Cap (< 15 words caps score at 60)
    words_count = len(answer.split())
    if words_count < 15:
        if score > 60:
            score = 60
            breakdown["capped_by_length"] = True

    # Bound final score between 0 and 100
    final_score = max(0, min(100, score))
    
    # Verdict determination
    verdict = "AUTO_APPROVED" if final_score >= CONFIDENCE_THRESHOLD else "REQUIRES_HUMAN_REVIEW"

    return {
        "score": final_score,
        "verdict": verdict,
        "breakdown": breakdown
    }
