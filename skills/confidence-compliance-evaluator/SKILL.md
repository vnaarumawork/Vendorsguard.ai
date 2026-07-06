---
name: confidence-compliance-evaluator
description: Evaluate and score the compliance confidence of security responses, identifying sensitive details, hedging phrases, placeholders, and source citations.
---

# Confidence and Compliance Evaluator Skill

This skill outlines the rubric and methodology for evaluating security questionnaire answers against official policy documents.

## Scoring Rubric

The evaluation scores answers on a scale from `0` to `100` based on the following rules:

### Positive Rules
1. **Keyword Overlap (+40 points)**:
   - Awarded if there is a match between the question's and the answer's normalized keywords.
   - Ignore common English stopwords (e.g. `what`, `how`, `the`).
   - Words of length >= 3 are compared after stripping punctuation and resolving simple plurals (e.g., `scans` -> `scan`, `policies` -> `policy`).

2. **Source Citation (+25 points)**:
   - Awarded if the answer cites an official source document.
   - Matches patterns like `"per ...policy"` (case-insensitive) or matches a `.md` filename (e.g., `security_policy.md`).

3. **Security Controls (+20 points)**:
   - Awarded if the answer refers to explicit named security controls (e.g., `AES-256`, `TLS 1.2`, `SOC 2`, `MFA`, `RBAC`, `KMS`, `GKE`, `VPC`, `mTLS`).

### Negative Rules (Penalties)
4. **Hedging Phrases (-10 points per occurrence, capped at -25)**:
   - Penalty applied for words indicating uncertainty like `"we believe"`, `"probably"`, or `"TBD"`.

5. **Placeholders (-15 points)**:
   - Penalty applied if there are unresolved placeholders in the text matching patterns like `[insert...]`, `<placeholder>`, `TODO`, or multiple underscores `__+`.

### Capping Rules
6. **Short Answer Cap (max 60 points)**:
   - If the answer has fewer than `15` words, the maximum score is capped at `60` regardless of the positive points accumulated.

---

## Verdict Determination

The final score determines whether the answer can be automatically submitted or requires human intervention:

- **AUTO_APPROVED**: Final score is equal to or greater than **85**.
- **REQUIRES_HUMAN_REVIEW**: Final score is less than **85**.
