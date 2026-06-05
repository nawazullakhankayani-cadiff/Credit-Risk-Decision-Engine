"""Generate a single, self-contained, shareable HTML report from any applicant file.

`generate_report("loans.csv", "report.html")` will:
  1. auto-ingest + clean the file (see data.ingest),
  2. score every applicant with the registered model (vectorised PD + policy),
  3. aggregate the most common risk drivers across the book,
  4. render a polished, interactive HTML dashboard with high-quality Plotly charts.

The output is ONE `.html` file with Plotly inlined — no internet, no server, no
build step. Open it locally, email it, or drop it in a GitHub repo / GitHub Pages
(rename to `index.html`) and it renders as a website for anyone.
"""
from __future__ import annotations

import argparse
import html as _html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
from plotly.offline import get_plotlyjs

from credit_risk.config import RISK_BANDS
from credit_risk.data.ingest import IngestReport, ingest
from credit_risk.data.schema import FEATURES
from credit_risk.monitoring import metrics as M
from credit_risk.scoring.grade import decide

# ---- palette -------------------------------------------------------------- #
DECISION_COLORS = {"APPROVE": "#1a9850", "REFER": "#f6a020", "DECLINE": "#d6334c"}
GRADE_ORDER = [b[0] for b in RISK_BANDS]
GRADE_COLORS = {
    "A": "#1a9850", "B": "#66bd63", "C": "#f6c344",
    "D": "#f6a020", "E": "#ef6c3e", "F": "#d6334c", "NA": "#9aa3ad",
}
INK = "#0f1f3d"
MUTED = "#5b6675"
PLOT_FONT = dict(family="Inter, -apple-system, Segoe UI, Roboto, sans-serif",
                 color=INK, size=13)

_LAYOUT = dict(
    template="plotly_white",
    font=PLOT_FONT,
    margin=dict(l=50, r=24, t=48, b=44),
    title=dict(font=dict(size=16, color=INK)),
    paper_bgcolor="white",
    plot_bgcolor="white",
    colorway=["#2b6cb0", "#1a9850", "#f6a020", "#d6334c", "#7b61ff"],
)

# Human-readable labels for the schema features.
FEATURE_LABELS = {
    "loan_amount": "Loan amount", "annual_income": "Annual income",
    "employment_length": "Employment length", "debt_to_income": "Debt-to-income",
    "credit_utilization": "Credit utilisation", "num_delinquencies_2y": "Delinquencies (2y)",
    "num_open_accounts": "Open accounts", "credit_history_length": "Credit history",
    "num_recent_inquiries": "Recent inquiries", "loan_term_months": "Loan term",
    "interest_rate": "Interest rate", "home_ownership_code": "Home ownership",
}


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def _score_frame(df: pd.DataFrame, scorer) -> pd.DataFrame:
    """Vectorised PD + per-row policy decision for the whole frame."""
    pd_cal = scorer.predict_pd_frame(df)
    out = df.copy()
    out["pd"] = pd_cal
    decisions = [decide(float(p)) for p in pd_cal]
    out["risk_grade"] = [d["risk_grade"] for d in decisions]
    out["decision"] = [d["decision"] for d in decisions]
    out["confidence"] = [d["confidence"] for d in decisions]
    out["human_review"] = [d["human_review"] for d in decisions]
    return out


def _aggregate_drivers(df: pd.DataFrame, scorer, sample: int = 1200) -> List[Dict[str, Any]]:
    """How often each feature is a top *risk-increasing* driver across the book."""
    n = min(sample, len(df))
    if n == 0:
        return []
    idx = np.linspace(0, len(df) - 1, n).astype(int)
    counts: Dict[str, int] = {}
    impact: Dict[str, float] = {}
    for _, row in df.iloc[idx].iterrows():
        try:
            res = scorer.score({f: row[f] for f in FEATURES}, with_memo=False)
        except Exception:
            continue
        for item in res["reasons"]["increases_risk"]:
            key = item.get("label", "?")
            counts[key] = counts.get(key, 0) + 1
            impact[key] = impact.get(key, 0.0) + abs(float(item.get("impact", 0) or 0))
    rows = [{"label": k, "freq": v, "share": v / n, "impact": impact.get(k, 0.0)}
            for k, v in counts.items()]
    rows.sort(key=lambda r: r["freq"], reverse=True)
    return rows[:10]


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def _div(fig: go.Figure, div_id: str) -> str:
    fig.update_layout(**_LAYOUT)
    return to_html(fig, include_plotlyjs=False, full_html=False, div_id=div_id,
                   config={"displayModeBar": False, "responsive": True})


def _fig_decision_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["decision"].value_counts()
    order = [d for d in ["APPROVE", "REFER", "DECLINE"] if d in counts.index]
    fig = go.Figure(go.Pie(
        labels=order, values=[int(counts[d]) for d in order], hole=0.62,
        marker=dict(colors=[DECISION_COLORS[d] for d in order],
                    line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=13),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>", sort=False))
    fig.update_layout(title="Decision mix", showlegend=False, height=330,
                      annotations=[dict(text=f"{len(df):,}<br>applicants", showarrow=False,
                                        font=dict(size=15, color=MUTED))])
    return fig


def _fig_grade_bar(df: pd.DataFrame) -> go.Figure:
    counts = df["risk_grade"].value_counts()
    grades = [g for g in GRADE_ORDER if g in counts.index]
    vals = [int(counts[g]) for g in grades]
    fig = go.Figure(go.Bar(
        x=grades, y=vals, marker_color=[GRADE_COLORS.get(g, "#888") for g in grades],
        text=vals, textposition="outside",
        hovertemplate="Grade %{x}: %{y} applicants<extra></extra>"))
    fig.update_layout(title="Risk-grade distribution", height=330,
                      yaxis_title="Applicants", xaxis_title="Risk grade",
                      bargap=0.25)
    return fig


def _fig_pd_hist(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for dec in ["APPROVE", "REFER", "DECLINE"]:
        sub = df[df["decision"] == dec]
        if len(sub):
            fig.add_trace(go.Histogram(
                x=sub["pd"] * 100, name=dec, marker_color=DECISION_COLORS[dec],
                opacity=0.8, xbins=dict(start=0, end=100, size=2.5),
                hovertemplate=dec + ": %{y} @ %{x:.0f}%<extra></extra>"))
    fig.update_layout(title="Probability-of-default distribution", barmode="stack",
                      height=330, xaxis_title="Calibrated PD (%)", yaxis_title="Applicants",
                      legend=dict(orientation="h", y=1.12, x=0))
    return fig


def _fig_pd_vs_amount(df: pd.DataFrame, max_pts: int = 4000) -> go.Figure:
    plot = df if len(df) <= max_pts else df.iloc[np.linspace(0, len(df) - 1, max_pts).astype(int)]
    fig = go.Figure()
    for dec in ["APPROVE", "REFER", "DECLINE"]:
        sub = plot[plot["decision"] == dec]
        if len(sub):
            fig.add_trace(go.Scattergl(
                x=sub["loan_amount"], y=sub["pd"] * 100, mode="markers", name=dec,
                marker=dict(color=DECISION_COLORS[dec], size=6, opacity=0.55,
                            line=dict(width=0)),
                hovertemplate=dec + "<br>£%{x:,.0f} · PD %{y:.1f}%<extra></extra>"))
    fig.update_layout(title="PD vs. loan amount", height=360,
                      xaxis_title="Loan amount (£)", yaxis_title="Calibrated PD (%)",
                      legend=dict(orientation="h", y=1.1, x=0))
    return fig


def _fig_drivers(drivers: List[Dict[str, Any]]) -> Optional[go.Figure]:
    if not drivers:
        return None
    drivers = list(reversed(drivers))
    fig = go.Figure(go.Bar(
        y=[d["label"] for d in drivers], x=[d["share"] * 100 for d in drivers],
        orientation="h", marker_color="#d6334c",
        text=[f"{d['share']*100:.0f}%" for d in drivers], textposition="outside",
        hovertemplate="%{y}: top risk driver in %{x:.0f}% of cases<extra></extra>"))
    fig.update_layout(title="Most common risk drivers (share of applicants)",
                      height=360, xaxis_title="% of applicants where this raised risk",
                      margin=dict(l=180, r=40, t=48, b=44))
    return fig


def _fig_pd_by_grade(df: pd.DataFrame) -> go.Figure:
    grades = [g for g in GRADE_ORDER if g in set(df["risk_grade"])]
    means = [df.loc[df["risk_grade"] == g, "pd"].mean() * 100 for g in grades]
    fig = go.Figure(go.Bar(
        x=grades, y=means, marker_color=[GRADE_COLORS.get(g, "#888") for g in grades],
        text=[f"{m:.1f}%" for m in means], textposition="outside",
        hovertemplate="Grade %{x}: avg PD %{y:.1f}%<extra></extra>"))
    fig.update_layout(title="Average PD by risk grade", height=330,
                      yaxis_title="Average calibrated PD (%)", xaxis_title="Risk grade")
    return fig


# --------------------------------------------------------------------------- #
# HTML assembly
# --------------------------------------------------------------------------- #
def _kpi(value: str, label: str, accent: str = INK, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{_html.escape(sub)}</div>' if sub else ""
    return (f'<div class="kpi"><div class="kpi-value" style="color:{accent}">{value}</div>'
            f'<div class="kpi-label">{_html.escape(label)}</div>{sub_html}</div>')


def _quality_section(rep: IngestReport) -> str:
    d = rep.to_dict()
    rows = [
        ("Rows read", f"{d['rows_in']:,}"),
        ("Rows scored", f"{d['rows_out']:,}"),
        ("Duplicate rows removed", f"{d['duplicate_rows']:,}"),
        ("Columns auto-mapped", f"{d['features_mapped']} / {d['features_total']}"),
        ("Missing cells imputed", f"{sum(d['missing_filled'].values()):,}"),
        ("Out-of-range cells clipped", f"{sum(d['clipped'].values()):,}"),
        ("Text values parsed", f"{sum(d['coerced_text'].values()):,}"),
        ("Target column detected", d["target_column"] or "—"),
    ]
    cells = "".join(f"<tr><td>{_html.escape(k)}</td><td>{_html.escape(str(v))}</td></tr>"
                    for k, v in rows)

    if rep.column_mapping:
        maps = "".join(
            f'<span class="pill"><b>{_html.escape(src)}</b> → {_html.escape(FEATURE_LABELS.get(f, f))}</span>'
            for src, f in rep.column_mapping.items())
    else:
        maps = '<span class="muted">No source columns matched the schema.</span>'

    synth = ""
    if rep.synthesized_features:
        names = ", ".join(FEATURE_LABELS.get(f, f) for f in rep.synthesized_features)
        synth = (f'<p class="note">⚠ {len(rep.synthesized_features)} feature(s) were not '
                 f'present and were filled from reference defaults: {_html.escape(names)}.</p>')
    warns = "".join(f'<p class="note">⚠ {_html.escape(w)}</p>' for w in rep.warnings)

    return f"""
    <section class="card wide">
      <h2>Data quality &amp; cleaning</h2>
      <p class="muted">Every uploaded file is auto-profiled, mapped to the model schema and
      cleaned before scoring. This is the audit trail of what happened.</p>
      <div class="quality-grid">
        <table class="kv">{cells}</table>
        <div class="mapping">
          <h3>Column mapping</h3>
          <div class="pills">{maps}</div>
          {synth}{warns}
        </div>
      </div>
    </section>"""


def _performance_section(df: pd.DataFrame) -> str:
    if "__target__" not in df.columns:
        return ""
    sub = df.dropna(subset=["__target__"])
    y = sub["__target__"].astype(int).to_numpy()
    if y.sum() == 0 or y.sum() == len(y):
        return ""
    s = M.summary(y, sub["pd"].to_numpy())
    tiles = "".join(_kpi(v, k) for k, v in [
        (f"{s['auc']:.3f}", "AUC"), (f"{s['gini']:.3f}", "Gini"),
        (f"{s['ks']:.3f}", "KS"), (f"{s['default_rate']*100:.1f}%", "Actual default rate")])
    return f"""
    <section class="card wide">
      <h2>Model performance on this file <span class="badge">label column found</span></h2>
      <p class="muted">A <code>{_html.escape(str(s['n']))}</code>-row outcome column was detected,
      so we back-tested the model's calibrated PD against actual outcomes.</p>
      <div class="kpi-row">{tiles}</div>
    </section>"""


def build_report_html(df_scored: pd.DataFrame, rep: IngestReport,
                      drivers: List[Dict[str, Any]], model_version: str,
                      title: str = "Credit Risk Portfolio Report",
                      source_name: str = "uploaded file") -> str:
    n = len(df_scored)
    dec = df_scored["decision"].value_counts()
    appr = int(dec.get("APPROVE", 0))
    refer = int(dec.get("REFER", 0))
    decl = int(dec.get("DECLINE", 0))
    avg_pd = df_scored["pd"].mean()
    review = int(df_scored["human_review"].sum())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    kpis = "".join([
        _kpi(f"{n:,}", "Applicants scored"),
        _kpi(f"{appr/n*100:.0f}%", "Approve", DECISION_COLORS["APPROVE"], f"{appr:,} applicants"),
        _kpi(f"{refer/n*100:.0f}%", "Refer", DECISION_COLORS["REFER"], f"{refer:,} applicants"),
        _kpi(f"{decl/n*100:.0f}%", "Decline", DECISION_COLORS["DECLINE"], f"{decl:,} applicants"),
        _kpi(f"{avg_pd*100:.1f}%", "Average PD"),
        _kpi(f"{rep.quality_score:.0f}", "Data quality", "#2b6cb0", "/ 100"),
    ])

    charts_top = (_div(_fig_decision_donut(df_scored), "c_donut")
                  + _div(_fig_grade_bar(df_scored), "c_grade"))
    charts_mid = (_div(_fig_pd_hist(df_scored), "c_hist")
                  + _div(_fig_pd_by_grade(df_scored), "c_pdgrade"))
    fig_drv = _fig_drivers(drivers)
    charts_bottom = _div(_fig_pd_vs_amount(df_scored), "c_scatter")
    charts_bottom += _div(fig_drv, "c_drv") if fig_drv else ""

    # Sample table of highest-risk applicants.
    show_cols = ["loan_amount", "annual_income", "debt_to_income", "credit_utilization",
                 "num_delinquencies_2y", "pd", "risk_grade", "decision"]
    top = df_scored.sort_values("pd", ascending=False).head(12)[show_cols]
    head = "".join(f"<th>{FEATURE_LABELS.get(c, c.upper())}</th>" for c in show_cols)
    body_rows = []
    for _, r in top.iterrows():
        cells = []
        for c in show_cols:
            if c == "pd":
                cells.append(f"<td>{r[c]*100:.1f}%</td>")
            elif c == "decision":
                cells.append(f'<td><span class="tag" style="background:{DECISION_COLORS.get(r[c],"#888")}">{r[c]}</span></td>')
            elif c == "risk_grade":
                cells.append(f'<td><b style="color:{GRADE_COLORS.get(r[c],"#888")}">{r[c]}</b></td>')
            elif c in ("debt_to_income", "credit_utilization"):
                cells.append(f"<td>{r[c]:.2f}</td>")
            elif c in ("loan_amount", "annual_income"):
                cells.append(f"<td>£{r[c]:,.0f}</td>")
            else:
                cells.append(f"<td>{r[c]:.0f}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    table = f'<table class="data"><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'

    plotlyjs = get_plotlyjs()
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<script>{plotlyjs}</script>
<style>
:root {{ --ink:{INK}; --muted:{MUTED}; --line:#e6e9ef; --bg:#f4f6fb; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; line-height:1.5; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:0 20px 64px; }}
header.hero {{ background:linear-gradient(120deg,#0f1f3d 0%,#1f3a6e 60%,#2b6cb0 100%);
  color:#fff; padding:36px 0 30px; margin-bottom:26px; box-shadow:0 2px 18px rgba(15,31,61,.18); }}
header.hero .wrap {{ padding-bottom:0; }}
header.hero h1 {{ margin:0 0 6px; font-size:30px; letter-spacing:-.5px; }}
header.hero p {{ margin:0; opacity:.85; font-size:14px; }}
.hero-meta {{ margin-top:16px; display:flex; flex-wrap:wrap; gap:10px; }}
.hero-meta span {{ background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.18);
  padding:5px 12px; border-radius:20px; font-size:12.5px; }}
.kpi-row,.kpi-grid {{ display:grid; gap:14px; }}
.kpi-grid {{ grid-template-columns:repeat(6,1fr); margin-bottom:8px; }}
.kpi-row {{ grid-template-columns:repeat(4,1fr); }}
.kpi {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 18px;
  box-shadow:0 1px 3px rgba(15,31,61,.05); }}
.kpi-value {{ font-size:26px; font-weight:700; letter-spacing:-.5px; }}
.kpi-label {{ font-size:12.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.4px; margin-top:2px; }}
.kpi-sub {{ font-size:12px; color:var(--muted); margin-top:3px; }}
section.card {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:8px 18px 16px;
  margin-top:20px; box-shadow:0 1px 3px rgba(15,31,61,.05); }}
.charts {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:20px; }}
.charts > div {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:6px 8px;
  box-shadow:0 1px 3px rgba(15,31,61,.05); overflow:hidden; }}
h2 {{ font-size:18px; margin:14px 4px 4px; }}
h3 {{ font-size:14px; margin:6px 0; color:var(--ink); }}
.muted {{ color:var(--muted); font-size:13px; margin:2px 4px 10px; }}
.quality-grid {{ display:grid; grid-template-columns:minmax(260px,360px) 1fr; gap:24px; align-items:start; }}
table.kv {{ width:100%; border-collapse:collapse; font-size:13px; }}
table.kv td {{ padding:7px 6px; border-bottom:1px solid var(--line); }}
table.kv td:last-child {{ text-align:right; font-weight:600; }}
.pills {{ display:flex; flex-wrap:wrap; gap:7px; }}
.pill {{ background:#eef3fb; border:1px solid #dce6f6; color:#28477e; padding:4px 10px;
  border-radius:8px; font-size:12px; }}
.note {{ background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; padding:8px 12px;
  border-radius:10px; font-size:12.5px; margin:10px 0 0; }}
.badge {{ background:#e6f4ea; color:#1a7f3c; font-size:11px; padding:3px 9px; border-radius:20px;
  vertical-align:middle; margin-left:8px; font-weight:600; }}
table.data {{ width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }}
table.data th {{ text-align:left; padding:8px 8px; border-bottom:2px solid var(--line);
  color:var(--muted); text-transform:uppercase; font-size:11px; letter-spacing:.3px; }}
table.data td {{ padding:7px 8px; border-bottom:1px solid var(--line); }}
.tag {{ color:#fff; padding:2px 9px; border-radius:6px; font-size:11px; font-weight:600; }}
footer {{ color:var(--muted); font-size:12px; margin-top:28px; padding-top:16px; border-top:1px solid var(--line); }}
code {{ background:#eef1f6; padding:1px 6px; border-radius:5px; font-size:12px; }}
@media (max-width:820px) {{ .kpi-grid{{grid-template-columns:repeat(2,1fr);}} .charts{{grid-template-columns:1fr;}}
  .kpi-row{{grid-template-columns:repeat(2,1fr);}} .quality-grid{{grid-template-columns:1fr;}} }}
</style></head>
<body>
<header class="hero"><div class="wrap">
  <h1>{_html.escape(title)}</h1>
  <p>Explainable, governed probability-of-default scoring · auto-cleaned &amp; auto-reported</p>
  <div class="hero-meta">
    <span>📄 Source: {_html.escape(source_name)}</span>
    <span>🧠 Model: {_html.escape(model_version)}</span>
    <span>👥 {n:,} applicants</span>
    <span>🕓 Generated {ts}</span>
    <span>🚦 {review:,} flagged for human review</span>
  </div>
</div></header>
<div class="wrap">
  <div class="kpi-grid">{kpis}</div>
  {_performance_section(df_scored)}
  <div class="charts">{charts_top}</div>
  <div class="charts">{charts_mid}</div>
  <div class="charts">{charts_bottom}</div>
  <section class="card wide">
    <h2>Highest-risk applicants</h2>
    <p class="muted">Top 12 by calibrated probability of default.</p>
    {table}
  </section>
  {_quality_section(rep)}
  <footer>
    Generated by the Credit Risk Decision Engine. Probabilities are calibrated; risk-band
    cut-offs are illustrative and require Credit Risk Committee sign-off. Where source columns
    were missing, values were imputed from reference defaults and flagged above —
    revalidate on governed production data before use.
  </footer>
</div>
</body></html>"""


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def generate_report(source: Any, out_path: str = "report.html",
                    scorer=None, title: str = "Credit Risk Portfolio Report",
                    source_name: Optional[str] = None,
                    driver_sample: int = 1200) -> Dict[str, Any]:
    """Ingest -> score -> render. Writes a self-contained HTML file; returns a summary."""
    if scorer is None:
        from credit_risk.predictor import CreditRiskScorer
        scorer = CreditRiskScorer.from_registry()

    if source_name is None:
        source_name = getattr(source, "name", None) or (
            Path(source).name if isinstance(source, (str, Path)) else "uploaded file")

    df_clean, rep = ingest(source)
    if rep.n_rows_out == 0:
        raise ValueError("No usable rows found in the uploaded file.")

    scored = _score_frame(df_clean, scorer)
    drivers = _aggregate_drivers(df_clean, scorer, sample=driver_sample)
    html_doc = build_report_html(scored, rep, drivers, scorer.version,
                                 title=title, source_name=str(source_name))

    out = Path(out_path)
    out.write_text(html_doc, encoding="utf-8")
    summary = {
        "output": str(out.resolve()),
        "applicants": int(len(scored)),
        "decision_mix": scored["decision"].value_counts().to_dict(),
        "avg_pd": round(float(scored["pd"].mean()), 4),
        "ingest": rep.to_dict(),
    }
    return summary


def _cli() -> None:
    ap = argparse.ArgumentParser(description="Generate a self-contained HTML credit-risk report.")
    ap.add_argument("source", help="Path to an applicant CSV/Excel file.")
    ap.add_argument("-o", "--output", default="report.html", help="Output HTML path.")
    ap.add_argument("-t", "--title", default="Credit Risk Portfolio Report")
    args = ap.parse_args()
    s = generate_report(args.source, args.output, title=args.title)
    print(f"[report] {s['applicants']:,} applicants → {s['output']}")
    print(f"[report] decision mix: {s['decision_mix']}  ·  avg PD {s['avg_pd']*100:.1f}%")


if __name__ == "__main__":
    _cli()
