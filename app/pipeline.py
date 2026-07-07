"""Pipeline runner used by the Streamlit UI.

Two execution paths:

1. LIVE  — runs the ADK multi-agent fleet (app/agent.py) via the ADK Runner.
           Requires GOOGLE_API_KEY (AI Studio) or Vertex AI credentials.
2. DEMO  — offline deterministic fallback: reads the knowledge folder
           directly, drafts a grounded answer, then runs the SAME redaction
           and confidence-evaluator tools. Guarantees the demo works even
           if the network / quota dies mid-presentation.

Set VENDORGUARD_MODE=live|demo (default: auto — live if credentials exist).
"""

import asyncio
import json
import os
import re

from app.tools.redaction import redact_sensitive_content
from app.tools.confidence_evaluator import evaluate_answer_confidence

_STOP = {"the","a","an","is","are","do","does","you","your","how","what","when",
         "where","which","of","in","on","at","to","for","and","or","with","any",
         "have","has","we","our","please","describe"}

def _keywords(text):
    words = re.findall(r"[a-z0-9\-]{3,}", text.lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in words if w not in _STOP}

KNOWLEDGE_DIR = os.getenv(
    "VENDORGUARD_KNOWLEDGE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge"),
)


def _mode() -> str:
    forced = os.getenv("VENDORGUARD_MODE", "auto").lower()
    if forced in ("live", "demo"):
        return forced
    has_creds = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    return "live" if has_creds else "demo"


# ── LIVE path: ADK Runner ───────────────────────────────────────────────────

async def _run_live_async(question: str) -> dict:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from app.agent import root_agent

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="vendorguard", user_id="analyst"
    )
    runner = Runner(agent=root_agent, app_name="vendorguard", session_service=session_service)

    content = types.Content(role="user", parts=[types.Part(text=f"QUESTION: {question}")])
    final_text = ""
    trace = []
    async for event in runner.run_async(
        user_id="analyst", session_id=session.id, new_message=content
    ):
        author = getattr(event, "author", "agent")
        if event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts)
            if text.strip():
                trace.append({"agent": author, "text": text.strip()})
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)

    result = _parse_guardrail_json(final_text)
    result["trace"] = trace
    result["mode"] = "live"
    return result


def _parse_guardrail_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if "final_answer" in data:
                return data
        except json.JSONDecodeError:
            pass
    # Model didn't emit clean JSON — re-run the deterministic guardrails on raw text
    red = redact_sensitive_content(text)
    ev = evaluate_answer_confidence("", red["redacted_text"])
    return {
        "final_answer": red["redacted_text"],
        "confidence_score": ev["confidence_score"],
        "verdict": ev["verdict"],
        "redactions": red["redaction_count"],
        "reasons": ev["reasons"] + ["Guardrail JSON parse fallback applied"],
    }


# ── DEMO path: offline deterministic pipeline ───────────────────────────────

def _load_knowledge() -> list:
    docs = []
    if os.path.isdir(KNOWLEDGE_DIR):
        for name in sorted(os.listdir(KNOWLEDGE_DIR)):
            if name.endswith(".md"):
                with open(os.path.join(KNOWLEDGE_DIR, name), encoding="utf-8") as f:
                    docs.append((name, f.read()))
    return docs


def _retrieve_evidence(question: str, docs: list) -> list:
    """Score every paragraph in every doc by keyword overlap with the question."""
    q_kw = _keywords(question)
    scored = []
    for name, text in docs:
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if len(para) < 40:
                continue
            overlap = len(q_kw & _keywords(para))
            if overlap >= 3:
                scored.append((overlap, para, name))
    scored.sort(key=lambda t: -t[0])
    return scored[:3]


def _run_demo(question: str) -> dict:
    docs = _load_knowledge()
    evidence = _retrieve_evidence(question, docs)
    trace = [{
        "agent": "PolicyResearchAgent",
        "text": "EVIDENCE:\n" + ("\n".join(f"- {p[:200]}... (source: {src})" for _, p, src in evidence)
                                  if evidence else "NONE_FOUND"),
    }]

    if evidence:
        parts, sources = [], []
        for _, para, src in evidence[:2]:
            parts.append(re.sub(r"^#+\s*.*\n", "", para).replace("\n", " ").strip())
            if src not in sources:
                sources.append(src)
        cite = " and ".join(sources)
        draft = f"{' '.join(parts)} These controls are documented in {cite} (per {sources[0]})."
    else:
        draft = ("We do not currently have documented evidence covering this item. "
                 "This response requires confirmation from the security team before submission.")
    trace.append({"agent": "AnswerDrafterAgent", "text": draft})

    red = redact_sensitive_content(draft)
    ev = evaluate_answer_confidence(question, red["redacted_text"])
    trace.append({"agent": "GuardrailAgent",
                  "text": f"Redactions: {red['redaction_count']} | Score: {ev['confidence_score']} "
                          f"| Verdict: {ev['verdict']}"})
    return {
        "final_answer": red["redacted_text"],
        "confidence_score": ev["confidence_score"],
        "verdict": ev["verdict"],
        "redactions": red["redaction_count"],
        "reasons": ev["reasons"],
        "trace": trace,
        "mode": "demo",
    }


# ── Public entry point ──────────────────────────────────────────────────────

def answer_question(question: str) -> dict:
    """Run one questionnaire question through the VendorGuard pipeline."""
    if _mode() == "live":
        try:
            return asyncio.run(_run_live_async(question))
        except Exception as exc:  # quota, network, auth — fall back, never crash the demo
            result = _run_demo(question)
            result["reasons"].append(f"Live mode failed ({type(exc).__name__}); demo fallback used")
            return result
    return _run_demo(question)
