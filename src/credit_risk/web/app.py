"""FastAPI website for the Credit Risk Decision Engine.

A real, multi-page web app: login / register / logout, a personalised dashboard,
manual single-applicant scoring, batch file upload → auto-cleaned, scored and
turned into an interactive report, plus a login/logout session history.

Run:  uvicorn credit_risk.web.app:app --port 8080 --app-dir src
"""
from __future__ import annotations

import io
import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from credit_risk.config import PATHS, RISK_BANDS
from credit_risk.data.schema import FEATURES, validate_record, ValidationError
from credit_risk.web import auth

BASE = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE / "templates"))
REPORTS_DIR = PATHS.data / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Set CREDIT_SECURE_COOKIES=1 in production (behind HTTPS) so the session cookie is
# only ever sent over TLS. Defaults off so the app works over http://localhost in dev.
SECURE_COOKIES = os.getenv("CREDIT_SECURE_COOKIES", "0") == "1"


def _set_session_cookie(resp, token: str) -> None:
    resp.set_cookie(auth.COOKIE_NAME, token, httponly=True, secure=SECURE_COOKIES,
                    samesite="lax", max_age=86400)

app = FastAPI(title="Credit Risk Decision Engine — Web")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

_scorer = None  # lazy singleton


def get_scorer():
    global _scorer
    if _scorer is None:
        from credit_risk.predictor import CreditRiskScorer
        _scorer = CreditRiskScorer.from_registry()
    return _scorer


@app.on_event("startup")
def _startup() -> None:
    auth.init_db()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def current_user(request: Request) -> Optional[auth.User]:
    return auth.session_user(request.cookies.get(auth.COOKIE_NAME))


def _redirect_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


def render(request: Request, template: str, user: auth.User, **ctx) -> HTMLResponse:
    base = {"request": request, "user": user, "features": FEATURES}
    base.update(ctx)
    return TEMPLATES.TemplateResponse(template, base)


# --------------------------------------------------------------------------- #
# Auth routes
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return RedirectResponse("/dashboard" if current_user(request) else "/login", 303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "", info: str = ""):
    if current_user(request):
        return RedirectResponse("/dashboard", 303)
    return TEMPLATES.TemplateResponse(
        "login.html", {"request": request, "error": error, "info": info,
                       "demo": auth.DEMO_USERS})


@app.post("/login")
def login_submit(request: Request, identifier: str = Form(...), password: str = Form(...)):
    try:
        user = auth.authenticate(identifier, password)
    except auth.AuthError as e:
        return TEMPLATES.TemplateResponse(
            "login.html", {"request": request, "error": str(e), "info": "",
                           "demo": auth.DEMO_USERS}, status_code=401)
    token = auth.start_session(user.employer_id, request.client.host if request.client else None)
    resp = RedirectResponse("/dashboard", 303)
    _set_session_cookie(resp, token)
    return resp


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str = ""):
    if current_user(request):
        return RedirectResponse("/dashboard", 303)
    return TEMPLATES.TemplateResponse("register.html", {"request": request, "error": error})


@app.post("/register")
def register_submit(request: Request, employer_id: str = Form(...),
                    company_name: str = Form(...), password: str = Form(...),
                    email: str = Form(""), full_name: str = Form("")):
    try:
        user = auth.register_user(employer_id, company_name, password,
                                  email=email, full_name=full_name)
    except auth.AuthError as e:
        return TEMPLATES.TemplateResponse(
            "register.html", {"request": request, "error": str(e)}, status_code=400)
    token = auth.start_session(user.employer_id, request.client.host if request.client else None)
    resp = RedirectResponse("/dashboard", 303)
    _set_session_cookie(resp, token)
    return resp


@app.get("/logout")
def logout(request: Request):
    auth.end_session(request.cookies.get(auth.COOKIE_NAME))
    resp = RedirectResponse("/login?info=You+have+been+logged+out.", 303)
    resp.delete_cookie(auth.COOKIE_NAME, httponly=True, secure=SECURE_COOKIES, samesite="lax")
    return resp


# --------------------------------------------------------------------------- #
# App pages
# --------------------------------------------------------------------------- #
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    token = request.cookies.get(auth.COOKIE_NAME)
    history = auth.session_history(user.employer_id, limit=5)
    return render(request, "dashboard.html", user,
                  model_version=get_scorer().version,
                  last_login=auth.last_login(user.employer_id, exclude_token=token),
                  history=history, active="dashboard")


@app.get("/score", response_class=HTMLResponse)
def score_page(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    return render(request, "score.html", user, result=None, active="score",
                  defaults=_DEFAULT_APPLICANT)


@app.post("/score", response_class=HTMLResponse)
async def score_submit(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    form = await request.form()
    record = {f: form.get(f) for f in FEATURES}
    try:
        validate_record(record)
        result = get_scorer().score(record, with_memo=True)
        error = None
    except (ValidationError, Exception) as e:  # noqa: BLE001
        result, error = None, str(e)
    return render(request, "score.html", user, result=result, error=error,
                  active="score", defaults=record)


@app.get("/batch", response_class=HTMLResponse)
def batch_page(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    return render(request, "batch.html", user, summary=None, active="batch")


@app.post("/batch", response_class=HTMLResponse)
async def batch_submit(request: Request, file: UploadFile = File(...)):
    user = current_user(request)
    if not user:
        return _redirect_login()
    from credit_risk.data.ingest import ingest
    from credit_risk.reporting.report import (_score_frame, _aggregate_drivers,
                                              build_report_html)
    try:
        raw = await file.read()
        buf = io.BytesIO(raw)
        buf.name = file.filename or "upload.csv"
        df_clean, rep = ingest(buf)
        if rep.n_rows_out == 0:
            raise ValueError("No usable rows found in the uploaded file.")
        scorer = get_scorer()
        scored = _score_frame(df_clean, scorer)
        drivers = _aggregate_drivers(df_clean, scorer, sample=600)
        html_doc = build_report_html(scored, rep, drivers, scorer.version,
                                     source_name=file.filename or "upload",
                                     title=f"{user.company_name} — Credit Risk Report")
        report_id = secrets.token_urlsafe(8)
        (REPORTS_DIR / f"{report_id}.html").write_text(html_doc, encoding="utf-8")
        dec = scored["decision"].value_counts().to_dict()
        summary = {
            "report_id": report_id,
            "rows": int(len(scored)),
            "quality": rep.quality_score,
            "mapped": rep.n_features_mapped,
            "decisions": {k: int(dec.get(k, 0)) for k in ["APPROVE", "REFER", "DECLINE"]},
            "avg_pd": round(float(scored["pd"].mean()) * 100, 1),
            "ingest": rep.to_dict(),
            "filename": file.filename,
        }
        error = None
    except Exception as e:  # noqa: BLE001
        summary, error = None, str(e)
    return render(request, "batch.html", user, summary=summary, error=error, active="batch")


@app.get("/reports/{report_id}.html", response_class=HTMLResponse)
def view_report(report_id: str, request: Request):
    if not current_user(request):
        return _redirect_login()
    path = REPORTS_DIR / f"{_safe(report_id)}.html"
    if not path.exists():
        return PlainTextResponse("Report not found.", status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/download/{report_id}.html")
def download_report(report_id: str, request: Request):
    if not current_user(request):
        return _redirect_login()
    path = REPORTS_DIR / f"{_safe(report_id)}.html"
    if not path.exists():
        return PlainTextResponse("Report not found.", status_code=404)
    return FileResponse(path, media_type="text/html", filename="credit_risk_report.html")


@app.get("/sessions", response_class=HTMLResponse)
def sessions_page(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    history = auth.session_history(user.employer_id, limit=100)
    return render(request, "sessions.html", user, history=history, active="sessions")


@app.get("/monitoring", response_class=HTMLResponse)
def monitoring_page(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    import json as _json

    mon = {"has_data": False, "scored": 0, "p50": None, "p95": None,
           "cost": 0.0, "decision_counts": {}}
    charts = {"decision_mix": "", "latency": ""}
    try:
        path = PATHS.data / "telemetry.jsonl"
        if path.exists():
            rows = []
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(_json.loads(line))
                except Exception:  # noqa: BLE001
                    continue
            score_rows = [r for r in rows if r.get("event") == "score"]
            latencies = [float(r["latency_ms"]) for r in score_rows
                         if r.get("latency_ms") is not None]
            cost = sum(float(r.get("cost_usd") or 0.0) for r in rows)

            counts: dict = {}
            for r in score_rows:
                key = r.get("grade") or r.get("decision")
                if key is None:
                    continue
                counts[key] = counts.get(key, 0) + 1

            def _pctile(vals, q):
                if not vals:
                    return None
                s = sorted(vals)
                if len(s) == 1:
                    return round(s[0], 2)
                pos = q * (len(s) - 1)
                lo = int(pos)
                hi = min(lo + 1, len(s) - 1)
                frac = pos - lo
                return round(s[lo] + (s[hi] - s[lo]) * frac, 2)

            mon = {
                "has_data": len(score_rows) > 0,
                "scored": len(score_rows),
                "p50": _pctile(latencies, 0.50),
                "p95": _pctile(latencies, 0.95),
                "cost": round(cost, 4),
                "decision_counts": counts,
            }

            if mon["has_data"]:
                import plotly.graph_objects as go
                from plotly.io import to_html

                _COLORS = {
                    "APPROVE": "#1a9850", "REFER": "#f6a020", "DECLINE": "#d6334c",
                    "A": "#1a9850", "B": "#1a9850", "C": "#f6a020", "D": "#f6a020",
                    "E": "#d6334c", "F": "#d6334c",
                }
                labels = list(counts.keys())
                values = [counts[k] for k in labels]
                bar_colors = [_COLORS.get(k, "#2b6cb0") for k in labels]
                fig_mix = go.Figure(go.Bar(x=labels, y=values, marker_color=bar_colors))
                fig_mix.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10), height=300,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8d9ab0", family="Inter, sans-serif"),
                    yaxis=dict(gridcolor="#212b3b"), xaxis=dict(showgrid=False))
                charts["decision_mix"] = to_html(
                    fig_mix, full_html=False, include_plotlyjs=False,
                    config={"displayModeBar": False})

                if latencies:
                    fig_lat = go.Figure(go.Scatter(
                        x=list(range(1, len(latencies) + 1)), y=latencies,
                        mode="lines", line=dict(color="#5b8cff", width=2)))
                    fig_lat.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10), height=300,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#8d9ab0", family="Inter, sans-serif"),
                        yaxis=dict(gridcolor="#212b3b", title="latency (ms)"),
                        xaxis=dict(showgrid=False, title="score #"))
                    charts["latency"] = to_html(
                        fig_lat, full_html=False, include_plotlyjs=False,
                        config={"displayModeBar": False})
    except Exception:  # noqa: BLE001
        mon = {"has_data": False, "scored": 0, "p50": None, "p95": None,
               "cost": 0.0, "decision_counts": {}}
        charts = {"decision_mix": "", "latency": ""}
    return render(request, "monitoring.html", user, mon=mon, charts=charts,
                  active="monitoring")


@app.get("/governance", response_class=HTMLResponse)
def governance_page(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    import json as _json

    manifest = None
    try:
        latest = _json.loads((PATHS.artifacts / "latest.json").read_text(encoding="utf-8"))
        version = latest.get("version")
        if version:
            mpath = PATHS.artifacts / version / "manifest.json"
            manifest = _json.loads(mpath.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        manifest = None

    def _read_doc(rel: str) -> str:
        try:
            return (PATHS.data.parent / rel).read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            return ""

    return render(request, "governance.html", user,
                  manifest=manifest,
                  risk_bands=list(RISK_BANDS),
                  model_card=_read_doc("docs/MODEL_CARD.md"),
                  governance_doc=_read_doc("docs/GOVERNANCE.md"),
                  active="governance")


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    user = current_user(request)
    if not user:
        return _redirect_login()
    endpoints = [
        {"method": "POST", "path": "/score",
         "purpose": "Score a single applicant and return PD, grade and decision."},
        {"method": "POST", "path": "/score/batch",
         "purpose": "Score many applicants from an uploaded batch in one request."},
        {"method": "GET", "path": "/health",
         "purpose": "Liveness/readiness probe for the scoring service."},
        {"method": "GET", "path": "/model",
         "purpose": "Return the active model version and metadata."},
        {"method": "GET", "path": "/monitoring/drift",
         "purpose": "Report feature/score drift metrics for the live model."},
    ]
    return render(request, "about.html", user, endpoints=endpoints, active="about")


def _safe(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "-_")


_DEFAULT_APPLICANT = {
    "loan_amount": 15000, "annual_income": 42000, "employment_length": 4,
    "debt_to_income": 0.30, "credit_utilization": 0.45, "num_delinquencies_2y": 0,
    "num_open_accounts": 8, "credit_history_length": 8, "num_recent_inquiries": 1,
    "loan_term_months": 36, "interest_rate": 12.5, "home_ownership_code": 0,
}
