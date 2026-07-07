"""VendorGuard AI — Streamlit triage portal.

Upload a questionnaire (JSON or CSV with a `question` column), watch the
agent fleet answer each item live, review low-confidence answers in the
Human-in-the-Loop tab, and export the final report.

Run:  streamlit run ui/streamlit_app.py
"""

import io
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from app.pipeline import answer_question
from app.tools.confidence_evaluator import CONFIDENCE_THRESHOLD

st.set_page_config(page_title="VendorGuard AI", page_icon="🛡️", layout="wide")

st.title("🛡️ VendorGuard AI")
st.caption("Autonomous multi-agent fleet for enterprise security questionnaires — "
           "answers in minutes, not weeks.")

if "results" not in st.session_state:
    st.session_state.results = []


def _parse_upload(uploaded) -> list:
    name = uploaded.name.lower()
    if name.endswith(".json"):
        data = json.load(uploaded)
        items = data.get("questions", data) if isinstance(data, dict) else data
        return [q["question"] if isinstance(q, dict) else str(q) for q in items]
    df = pd.read_csv(uploaded)
    col = next((c for c in df.columns if c.strip().lower() == "question"), df.columns[0])
    return df[col].dropna().astype(str).tolist()


tab_run, tab_hitl, tab_export = st.tabs(
    ["▶️ Run Questionnaire", "🧑‍⚖️ Human-in-the-Loop Triage", "📤 Export Report"]
)

with tab_run:
    uploaded = st.file_uploader("Upload questionnaire (JSON or CSV)", type=["json", "csv"])
    use_sample = st.checkbox("Use bundled sample questionnaire", value=uploaded is None)

    if st.button("🚀 Run agent fleet", type="primary"):
        if uploaded:
            questions = _parse_upload(uploaded)
        elif use_sample:
            sample = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "data", "sample_questionnaire.json")
            with open(sample, encoding="utf-8") as f:
                questions = [q["question"] for q in json.load(f)["questions"]]
        else:
            st.warning("Upload a questionnaire or tick the sample checkbox.")
            st.stop()

        st.session_state.results = []
        progress = st.progress(0.0, text="Dispatching agents…")
        for i, q in enumerate(questions):
            progress.progress((i) / len(questions), text=f"Q{i+1}/{len(questions)}: {q[:80]}")
            result = answer_question(q)
            result["question"] = q
            result.setdefault("edited", False)
            st.session_state.results.append(result)

            with st.expander(f"Q{i+1}: {q}", expanded=False):
                for step in result.get("trace", []):
                    st.markdown(f"**🤖 {step['agent']}**")
                    st.text(step["text"][:1200])
                score = result["confidence_score"]
                badge = "✅ AUTO-APPROVED" if result["verdict"] == "AUTO_APPROVED" \
                    else "🟠 REQUIRES HUMAN REVIEW"
                st.markdown(f"**Answer:** {result['final_answer']}")
                st.markdown(f"**Confidence: {score}/100** &nbsp; {badge} &nbsp; "
                            f"(mode: `{result.get('mode', '?')}`, "
                            f"redactions: {result.get('redactions', 0)})")
        progress.progress(1.0, text="Fleet complete ✔")

        approved = sum(1 for r in st.session_state.results if r["verdict"] == "AUTO_APPROVED")
        flagged = len(st.session_state.results) - approved
        c1, c2, c3 = st.columns(3)
        c1.metric("Questions answered", len(st.session_state.results))
        c2.metric("Auto-approved", approved)
        c3.metric("Flagged for human review", flagged)

with tab_hitl:
    flagged = [r for r in st.session_state.results if r["verdict"] == "REQUIRES_HUMAN_REVIEW"]
    if not st.session_state.results:
        st.info("Run a questionnaire first.")
    elif not flagged:
        st.success("Nothing to triage — every answer cleared the "
                   f"{CONFIDENCE_THRESHOLD}% confidence threshold. 🎉")
    else:
        st.warning(f"{len(flagged)} answer(s) below the {CONFIDENCE_THRESHOLD}% threshold "
                   "need human sign-off.")
        for idx, r in enumerate(st.session_state.results):
            if r["verdict"] != "REQUIRES_HUMAN_REVIEW":
                continue
            with st.container(border=True):
                st.markdown(f"**{r['question']}**")
                st.caption(f"Confidence {r['confidence_score']}/100 — " +
                           "; ".join(r.get("reasons", [])[:3]))
                new_answer = st.text_area("Edit answer", r["final_answer"], key=f"edit_{idx}")
                if st.button("✅ Approve", key=f"approve_{idx}"):
                    r["final_answer"] = new_answer
                    r["verdict"] = "HUMAN_APPROVED"
                    r["edited"] = True
                    st.rerun()

with tab_export:
    if not st.session_state.results:
        st.info("Run a questionnaire first.")
    else:
        df = pd.DataFrame([{
            "question": r["question"],
            "answer": r["final_answer"],
            "confidence": r["confidence_score"],
            "status": r["verdict"],
            "human_edited": r.get("edited", False),
        } for r in st.session_state.results])
        st.dataframe(df, use_container_width=True)
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button("⬇️ Download CSV report", csv_buf.getvalue(),
                           "vendorguard_report.csv", "text/csv")
        st.download_button("⬇️ Download JSON report",
                           json.dumps(df.to_dict(orient="records"), indent=2),
                           "vendorguard_report.json", "application/json")
