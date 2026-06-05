"""Self-contained HTML reporting for batch credit-risk scoring."""

__all__ = ["build_report_html", "generate_report"]


def __getattr__(name):  # lazy import keeps `python -m ...report` warning-free
    if name in __all__:
        from credit_risk.reporting import report
        return getattr(report, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
