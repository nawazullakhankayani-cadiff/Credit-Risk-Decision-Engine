"""LLM credit-memo generation with a deterministic template fallback.

Production path calls an LLM (OpenAI or Anthropic) to turn the structured
decision + reason codes into a concise, audit-friendly credit memo. When no API
key/library is present, a template memo is produced from the same structured
inputs, so the engine is fully functional offline and in CI. The LLM is *never*
the decision-maker — it only narrates the model's already-made, governed decision.
This separation is deliberate for model-risk governance.
"""
from __future__ import annotations
import os, time
from typing import Dict, Optional
from pathlib import Path

SYSTEM_PROMPT = (
    "You are a credit risk analyst assistant. Write a concise, factual credit "
    "memo (max 150 words) explaining a lending decision that has ALREADY been "
    "made by a governed model. Use only the structured facts provided. Do not "
    "invent figures. Be neutral and professional. State the decision, the key "
    "drivers, and any recommended conditions or human-review note."
)


def _template_memo(payload: Dict) -> str:
    d = payload["decision"]
    inc = payload["reasons"]["increases_risk"]
    dec = payload["reasons"]["reduces_risk"]
    up = ", ".join(r["label"] for r in inc[:3]) or "no material adverse factors"
    down = ", ".join(r["label"] for r in dec[:3]) or "limited mitigating factors"
    review = (" This case falls near a decision boundary and is referred for "
              "human review.") if d["human_review"] else ""
    return (
        f"Decision: {d['decision']} (risk grade {d['risk_grade']}, "
        f"PD {d['pd']:.1%}, confidence {d['confidence']:.0%}).\n\n"
        f"The application was assessed by the credit-risk model. The primary "
        f"factors increasing estimated default risk were {up}. "
        f"Factors reducing risk included {down}.{review}\n\n"
        f"This memo narrates a model-generated decision and does not constitute "
        f"financial advice; all declines are subject to the firm's adverse-action "
        f"and appeals process."
    )


def _build_user_prompt(payload: Dict) -> str:
    import json
    return ("Produce the credit memo from these facts as JSON:\n"
            + json.dumps(payload, default=str))


def generate_memo(payload: Dict, cfg=None, cost_log_path: Optional[Path] = None) -> Dict:
    """Return {'memo': str, 'source': 'openai'|'anthropic'|'template', ...}."""
    from credit_risk.config import LLM as DEFAULT_LLM
    cfg = cfg or DEFAULT_LLM
    provider = cfg.provider
    t0 = time.time()
    memo, source, in_tok, out_tok = None, "template", 0, 0

    def _log(src, it, ot):
        if cost_log_path is not None:
            from credit_risk.monitoring.cost_log import log_event
            log_event(cost_log_path, "llm_memo", (time.time() - t0) * 1000,
                      model=cfg.model, in_tokens=it, out_tokens=ot,
                      extra={"source": src})

    try:
        if provider in ("auto", "openai") and os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=cfg.model, temperature=cfg.temperature, max_tokens=cfg.max_tokens,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": _build_user_prompt(payload)}],
            )
            memo = resp.choices[0].message.content.strip()
            source = "openai"
            u = getattr(resp, "usage", None)
            if u:
                in_tok, out_tok = u.prompt_tokens, u.completion_tokens
        elif provider in ("auto", "anthropic") and os.getenv("ANTHROPIC_API_KEY"):
            import anthropic
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=cfg.model, max_tokens=cfg.max_tokens, temperature=cfg.temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_user_prompt(payload)}],
            )
            memo = "".join(b.text for b in resp.content).strip()
            source = "anthropic"
            in_tok, out_tok = resp.usage.input_tokens, resp.usage.output_tokens
    except Exception as e:  # never fail a decision because the LLM is down
        memo, source = None, "template"

    if not memo:
        memo, source = _template_memo(payload), "template"
    _log(source, in_tok, out_tok)
    return {"memo": memo, "source": source,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "tokens": {"in": in_tok, "out": out_tok}}
