# VendorGuard AI — Architecture Deep Dive

## Design principle

**The LLM drafts; deterministic code decides.** Every answer that leaves the
system passes through regex-based redaction and a reproducible 0–100 scoring
skill. Judges and auditors can re-run the guardrails and get identical results
— no LLM-as-judge variance on the security-critical path.

## Agent fleet (ADK)

| Agent | Type | Tools | Input → Output |
|---|---|---|---|
| VendorGuardOrchestrator | `SequentialAgent` | — | question → final JSON |
| PolicyResearchAgent | `LlmAgent` | Filesystem **MCPToolset** | question → `policy_evidence` |
| AnswerDrafterAgent | `LlmAgent` | — | `{policy_evidence}` → `draft_answer` |
| GuardrailAgent | `LlmAgent` | `redact_sensitive_content`, `evaluate_answer_confidence` | `{draft_answer}` → verdict JSON |

State passes between agents through ADK session state via `output_key` —
each agent's instruction template interpolates the previous agent's output
(`{policy_evidence}`, `{draft_answer}`). No shared globals, no prompt
concatenation in application code.

## MCP boundary

The Filesystem MCP server (`@modelcontextprotocol/server-filesystem`) is
scoped to `knowledge/` only. This is a *security boundary*, not a convenience:
the research agent physically cannot read source code, `.env`, or anything
outside the mock policy folder. Swapping the mock folder for a real
compliance-docs bucket (or a codebase MCP server) changes zero agent code.

## Anti-hallucination path

The sample questionnaire ships with Q7 (quantum-resistant crypto roadmap)
that the knowledge base deliberately cannot answer:

1. PolicyResearchAgent returns `EVIDENCE: NONE_FOUND`.
2. AnswerDrafterAgent is instructed to *refuse to invent controls* and states
   the item needs security-team confirmation.
3. The confidence skill scores the hedged, uncited draft far below 85.
4. Verdict `REQUIRES_HUMAN_REVIEW` → the answer lands in the HITL triage tab
   and can only exit via explicit human approval (`HUMAN_APPROVED`).

## Failure-mode engineering

`app/pipeline.py` implements a live/demo dual path. Live mode runs the real
ADK `Runner` (Gemini + MCP). If credentials, quota, or the network fail, the
same request falls through to an offline deterministic pipeline that uses the
*identical* redaction and scoring tools over a keyword-overlap retriever.
The demo cannot crash on stage, and the guardrail behavior shown offline is
byte-for-byte the guardrail behavior in production.

## Security layers (defense in depth)

1. **Shift-left:** pre-commit + detect-secrets + semgrep block secrets before
   they reach git (`semgrep_rules.yml`).
2. **Runtime input boundary:** MCP scoped to the knowledge folder.
3. **Runtime output boundary:** in-agent PII/IP redaction before scoring.
4. **Process boundary:** confidence threshold routes uncertainty to humans.
5. **Deploy boundary:** API key lives in Secret Manager, injected by Cloud Run.
