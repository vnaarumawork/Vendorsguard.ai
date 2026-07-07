"""VendorGuard AI — ADK multi-agent fleet.

Pipeline (SequentialAgent as the Orchestrator):

    PolicyResearchAgent  ──►  AnswerDrafterAgent  ──►  GuardrailAgent
    (reads policy docs         (writes enterprise-      (redacts PII/IP,
     via the Filesystem         grade answer from        scores confidence,
     MCP server)                MCP evidence)            emits verdict)

State flows between agents through session state via `output_key`:
    policy_evidence  →  draft_answer  →  final JSON verdict

Run locally with:  adk web   (from the repo root)  and select `vendorguard`.
"""

import os

from google.adk.agents import LlmAgent, SequentialAgent

from app.tools.redaction import redact_sensitive_content
from app.tools.confidence_evaluator import evaluate_answer_confidence

MODEL = os.getenv("VENDORGUARD_MODEL", "gemini-2.0-flash")
KNOWLEDGE_DIR = os.getenv(
    "VENDORGUARD_KNOWLEDGE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge"),
)


def _build_mcp_toolset():
    """Connect to the Filesystem MCP server scoped to the knowledge folder.

    The agent can ONLY see the mock policy folder — this is the security
    boundary: no arbitrary filesystem access. Requires `npx` on PATH.
    Returns None if MCP deps are unavailable so the app degrades gracefully.
    """
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
        try:  # ADK >= 1.x style
            from google.adk.tools.mcp_tool.mcp_session_manager import (
                StdioConnectionParams,
            )
            from mcp import StdioServerParameters

            conn = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-filesystem", KNOWLEDGE_DIR],
                )
            )
        except ImportError:  # older ADK style
            from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters

            conn = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", KNOWLEDGE_DIR],
            )
        return MCPToolset(connection_params=conn)
    except Exception:
        return None


_mcp_toolset = _build_mcp_toolset()

# ── Agent 1: Policy Research ────────────────────────────────────────────────
policy_research_agent = LlmAgent(
    name="PolicyResearchAgent",
    model=MODEL,
    description="Retrieves relevant security-policy evidence via the Filesystem MCP server.",
    instruction=(
        "You are a compliance research analyst. You receive ONE enterprise security "
        "questionnaire question. Use your filesystem tools to list and read the policy "
        "documents available to you (security policy, architecture overview, SOC 2 summary). "
        "Extract only the passages relevant to the question. "
        "Output format:\n"
        "EVIDENCE:\n- <verbatim or tightly paraphrased passage> (source: <filename>)\n"
        "If no document covers the question, output exactly: EVIDENCE: NONE_FOUND"
    ),
    tools=[_mcp_toolset] if _mcp_toolset else [],
    output_key="policy_evidence",
)

# ── Agent 2: Answer Drafter ─────────────────────────────────────────────────
answer_drafter_agent = LlmAgent(
    name="AnswerDrafterAgent",
    model=MODEL,
    description="Drafts a professional enterprise-grade answer from the retrieved evidence.",
    instruction=(
        "You are a senior security engineer answering an enterprise vendor questionnaire. "
        "Question and retrieved evidence are below.\n\n"
        "EVIDENCE:\n{policy_evidence}\n\n"
        "Write a concise, professional answer (2-5 sentences) grounded ONLY in the evidence. "
        "Cite the source document inline, e.g. 'per our Security Policy (security_policy.md)'. "
        "If evidence is NONE_FOUND, state that the item requires confirmation from the "
        "security team — do NOT invent controls we do not have."
    ),
    output_key="draft_answer",
)

# ── Agent 3: Security & Guardrail Evaluation ────────────────────────────────
guardrail_agent = LlmAgent(
    name="GuardrailAgent",
    model=MODEL,
    description="Redacts PII/IP and assigns a confidence score via the evaluator skill.",
    instruction=(
        "You are the security guardrail auditor. The draft answer is:\n\n"
        "{draft_answer}\n\n"
        "Step 1: Call redact_sensitive_content on the draft to strip PII and internal IP.\n"
        "Step 2: Call evaluate_answer_confidence with the original question and the "
        "REDACTED text to obtain the confidence score and verdict.\n"
        "Step 3: Reply with ONLY this JSON object, no markdown fences:\n"
        '{"final_answer": "<redacted answer>", "confidence_score": <int>, '
        '"verdict": "<AUTO_APPROVED|REQUIRES_HUMAN_REVIEW>", '
        '"redactions": <int>, "reasons": [<scoring notes>]}'
    ),
    tools=[redact_sensitive_content, evaluate_answer_confidence],
    output_key="guardrail_result",
)

# ── Orchestrator ────────────────────────────────────────────────────────────
root_agent = SequentialAgent(
    name="VendorGuardOrchestrator",
    description=(
        "Orchestrates the VendorGuard pipeline: policy research (MCP) → answer "
        "drafting → security guardrail evaluation with HITL routing."
    ),
    sub_agents=[policy_research_agent, answer_drafter_agent, guardrail_agent],
)
