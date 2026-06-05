"""Streamlit front-end: single-applicant scoring, batch CSV scoring, and a live
monitoring dashboard (decision mix, latency, LLM cost, PSI drift).

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from credit_risk.config import PATHS
from credit_risk.data.schema import FEATURES
from credit_risk.data.ingest import ingest
from credit_risk.predictor import CreditRiskScorer
from credit_risk.reporting.report import (
    _score_frame, _aggregate_drivers, _fig_decision_donut, _fig_grade_bar,
    _fig_pd_hist, _fig_pd_vs_amount, _fig_drivers, build_report_html)
from credit_risk.web import auth

st.set_page_config(page_title="Credit Risk Decision Engine", layout="wide")


@st.cache_resource
def load_scorer():
    return CreditRiskScorer.from_registry()


# --------------------------------------------------------------------------- #
# Authentication gate — shares the same user store as the FastAPI website.
# --------------------------------------------------------------------------- #
auth.init_db()


def _login_gate():
    if st.session_state.get("user"):
        return
    st.title("Credit Risk Decision Engine")
    st.caption("Sign in with your Employer ID or company name.")
    with st.form("login"):
        ident = st.text_input("Employer ID or company name", placeholder="EMP001 or Acme Lending")
        pw = st.text_input("Password", type="password")
        c1, c2 = st.columns(2)
        submit = c1.form_submit_button("Sign in", type="primary", use_container_width=True)
        register = c2.form_submit_button("Create account", use_container_width=True)
    if submit:
        try:
            user = auth.authenticate(ident, pw)
            st.session_state["user"] = user
            st.session_state["token"] = auth.start_session(user.employer_id, "streamlit")
            st.rerun()
        except auth.AuthError as e:
            st.error(str(e))
    if register:
        st.session_state["show_register"] = True
    if st.session_state.get("show_register"):
        with st.form("register"):
            st.subheader("Create account")
            co = st.text_input("Company name")
            eid = st.text_input("Employer ID")
            name = st.text_input("Your name")
            email = st.text_input("Work email")
            rpw = st.text_input("Password", type="password", key="rpw")
            if st.form_submit_button("Register", type="primary"):
                try:
                    user = auth.register_user(eid, co, rpw, email=email, full_name=name)
                    st.session_state["user"] = user
                    st.session_state["token"] = auth.start_session(user.employer_id, "streamlit")
                    st.rerun()
                except auth.AuthError as e:
                    st.error(str(e))
    st.info("Demo logins (password `demo1234`): **EMP001** Acme Lending · "
            "**EMP002** Northwind Finance · **EMP003** Sterling Credit Union")
    st.stop()


_login_gate()
_user = st.session_state["user"]
with st.sidebar:
    st.markdown(f"### 👤 {_user.full_name}")
    st.caption(f"{_user.company_name} · {_user.employer_id}")
    last = auth.last_login(_user.employer_id, exclude_token=st.session_state.get("token"))
    st.caption(f"Last login: {last or 'first time'}")
    if st.button("Log out", use_container_width=True):
        auth.end_session(st.session_state.get("token"))
        for k in ("user", "token", "show_register"):
            st.session_state.pop(k, None)
        st.rerun()

st.title(f"Welcome, {_user.full_name}")
st.caption("Explainable, governed probability-of-default scoring with AI credit memos.")

try:
    scorer = load_scorer()
    st.success(f"Loaded model version `{scorer.version}`")
except Exception as e:
    st.error(f"No trained model found. Run `python -m credit_risk.train` first. ({e})")
    st.stop()

tab_single, tab_batch, tab_monitor = st.tabs(
    ["Single applicant", "Batch scoring", "Monitoring"])

with tab_single:
    c1, c2, c3 = st.columns(3)
    rec = {}
    rec["loan_amount"] = c1.number_input("Loan amount (GBP)", 500, 100000, 15000, step=500)
    rec["annual_income"] = c1.number_input("Annual income (GBP)", 1000, 5000000, 42000, step=1000)
    rec["employment_length"] = c1.number_input("Employment length (yrs)", 0.0, 60.0, 4.0)
    rec["debt_to_income"] = c1.slider("Debt-to-income", 0.0, 2.5, 0.30)
    rec["credit_utilization"] = c2.slider("Credit utilisation", 0.0, 1.8, 0.45)
    rec["num_delinquencies_2y"] = c2.number_input("Delinquencies (2y)", 0, 50, 0)
    rec["num_open_accounts"] = c2.number_input("Open accounts", 0, 100, 8)
    rec["credit_history_length"] = c2.number_input("Credit history (yrs)", 0.0, 80.0, 8.0)
    rec["num_recent_inquiries"] = c3.number_input("Recent inquiries (6m)", 0, 50, 1)
    rec["loan_term_months"] = c3.selectbox("Loan term (months)", [36, 60], 0)
    rec["interest_rate"] = c3.slider("Interest rate (APR %)", 3.0, 35.0, 12.5)
    rec["home_ownership_code"] = c3.selectbox(
        "Home ownership", [0, 1, 2],
        format_func=lambda x: {0: "Rent", 1: "Mortgage", 2: "Own"}[x])
    want_memo = st.checkbox("Generate AI credit memo", value=True)

    if st.button("Score applicant", type="primary"):
        r = scorer.score(rec, with_memo=want_memo)
        d = r["decision"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Decision", d["decision"])
        m2.metric("Risk grade", d["risk_grade"])
        m3.metric("PD", f"{d['pd']:.1%}")
        m4.metric("Confidence", f"{d['confidence']:.0%}")
        if d["human_review"]:
            st.warning("Near a decision boundary — routed for human review.")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.subheader("Increases risk")
            st.table(pd.DataFrame(r["reasons"]["increases_risk"])[["label", "value", "impact"]]
                     if r["reasons"]["increases_risk"] else pd.DataFrame())
        with cc2:
            st.subheader("Reduces risk")
            st.table(pd.DataFrame(r["reasons"]["reduces_risk"])[["label", "value", "impact"]]
                     if r["reasons"]["reduces_risk"] else pd.DataFrame())
        if want_memo:
            st.subheader(f"Credit memo  ·  source: {r['credit_memo']['source']}")
            st.write(r["credit_memo"]["memo"])

with tab_batch:
    st.write("Upload **any** applicant file (CSV or Excel). Columns are auto-detected, "
             "cleaned and mapped to the model schema — messy headers, currency symbols, "
             "percentages and text values are handled for you.")
    st.caption("Recognised fields: " + ", ".join(FEATURES))
    up = st.file_uploader("Applicant file", type=["csv", "xlsx", "xls"])

    @st.cache_data(show_spinner="Cleaning, scoring and building report…")
    def _process(file_bytes: bytes, name: str):
        import io
        buf = io.BytesIO(file_bytes); buf.name = name
        df_clean, rep = ingest(buf)
        scored = _score_frame(df_clean, scorer)
        drivers = _aggregate_drivers(df_clean, scorer, sample=600)
        html_doc = build_report_html(scored, rep, drivers, scorer.version,
                                     source_name=name)
        return df_clean, rep, scored, drivers, html_doc

    if up is not None:
        df_clean, rep, scored, drivers, html_doc = _process(up.getvalue(), up.name)
        rd = rep.to_dict()

        # --- cleaning summary -------------------------------------------------
        st.success(f"Cleaned **{rd['rows_out']:,}** rows · auto-mapped "
                   f"**{rd['features_mapped']}/{rd['features_total']}** columns · "
                   f"data-quality score **{rd['quality_score']:.0f}/100**")
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Rows scored", f"{rd['rows_out']:,}")
        q2.metric("Missing imputed", f"{sum(rd['missing_filled'].values()):,}")
        q3.metric("Out-of-range clipped", f"{sum(rd['clipped'].values()):,}")
        q4.metric("Text values parsed", f"{sum(rd['coerced_text'].values()):,}")
        for w in rep.warnings:
            st.warning(w)
        with st.expander("Column mapping & cleaning detail"):
            st.json(rd)

        # --- decision KPIs ----------------------------------------------------
        n = len(scored); dec = scored["decision"].value_counts()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Applicants", f"{n:,}")
        k2.metric("Approve", f"{dec.get('APPROVE',0)/n*100:.0f}%")
        k3.metric("Refer", f"{dec.get('REFER',0)/n*100:.0f}%")
        k4.metric("Decline", f"{dec.get('DECLINE',0)/n*100:.0f}%")

        # --- high-quality charts ---------------------------------------------
        c1, c2 = st.columns(2)
        c1.plotly_chart(_fig_decision_donut(scored), use_container_width=True)
        c2.plotly_chart(_fig_grade_bar(scored), use_container_width=True)
        c3, c4 = st.columns(2)
        c3.plotly_chart(_fig_pd_hist(scored), use_container_width=True)
        c4.plotly_chart(_fig_pd_vs_amount(scored), use_container_width=True)
        fig_drv = _fig_drivers(drivers)
        if fig_drv is not None:
            st.plotly_chart(fig_drv, use_container_width=True)

        # --- downloads --------------------------------------------------------
        st.subheader("Export")
        d1, d2 = st.columns(2)
        d1.download_button("⬇ Download interactive HTML report", html_doc,
                           "credit_risk_report.html", "text/html",
                           use_container_width=True,
                           help="Self-contained — open anywhere or publish to GitHub Pages.")
        out_csv = scored.drop(columns=[c for c in ["__target__"] if c in scored.columns])
        d2.download_button("⬇ Download scored CSV", out_csv.to_csv(index=False),
                           "scored_applicants.csv", "text/csv", use_container_width=True)
        st.dataframe(scored.head(200), use_container_width=True)

with tab_monitor:
    tel = PATHS.data / "telemetry.jsonl"
    if not tel.exists():
        st.info("No telemetry yet — score some applicants to populate this dashboard.")
    else:
        rows = [json.loads(l) for l in tel.read_text().splitlines() if l.strip()]
        tdf = pd.DataFrame(rows)
        scores = tdf[tdf["event"] == "score"]
        st.subheader("Throughput & latency")
        a, b, c = st.columns(3)
        a.metric("Decisions scored", len(scores))
        if len(scores):
            b.metric("p50 latency (ms)", round(scores["latency_ms"].median(), 2))
            c.metric("p95 latency (ms)", round(scores["latency_ms"].quantile(0.95), 2))
        if "cost_usd" in tdf:
            st.metric("Cumulative LLM cost (USD)", round(tdf["cost_usd"].sum(), 4))
        if "grade" in scores and len(scores):
            st.subheader("Decision mix")
            st.bar_chart(scores["grade"].value_counts().sort_index())

    ref_path = PATHS.data / "reference_sample.csv"
    st.subheader("Input drift (PSI vs. training reference)")
    drift_file = st.file_uploader("Upload a recent batch CSV to check drift", type=["csv"],
                                  key="drift")
    if drift_file is not None and ref_path.exists():
        from credit_risk.monitoring import drift as D
        ref = pd.read_csv(ref_path)
        cur = pd.read_csv(drift_file)
        report = D.feature_drift(ref, cur, [c for c in FEATURES if c in cur.columns])
        st.write("Overall:", D.overall_status(report))
        st.dataframe(pd.DataFrame(report).T)
