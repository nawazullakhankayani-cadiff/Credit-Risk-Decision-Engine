"""Lightweight model registry: versioned, immutable, auditable artifacts.

Each trained bundle (model + feature pipeline + calibrator + metrics + metadata)
is written to ``models/registry/<version>/`` with a content hash and a JSON
manifest. ``latest.json`` points at the production version. This is a minimal,
self-contained stand-in for MLflow / SageMaker Model Registry that needs no
external services and gives full lineage for model-risk governance.
"""
from __future__ import annotations
import json, hashlib, datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:12]


class ModelRegistry:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, bundle: Dict[str, Any], metrics: Dict[str, Any],
             metadata: Dict[str, Any]) -> str:
        payload = json.dumps(bundle, sort_keys=True).encode()
        version = f"{_now()}-{_hash(payload)}"
        vdir = self.root / version
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "bundle.json").write_bytes(payload)
        (vdir / "metrics.json").write_text(json.dumps(metrics, indent=2))
        manifest = {
            "version": version,
            "created_utc": _now(),
            "content_hash": _hash(payload),
            "model_name": bundle.get("model", {}).get("name", "unknown"),
            "metrics": metrics,
            **metadata,
        }
        (vdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (self.root / "latest.json").write_text(json.dumps({"version": version}, indent=2))
        return version

    def latest_version(self) -> Optional[str]:
        p = self.root / "latest.json"
        if not p.exists():
            return None
        return json.loads(p.read_text())["version"]

    def load(self, version: Optional[str] = None) -> Dict[str, Any]:
        version = version or self.latest_version()
        if version is None:
            raise FileNotFoundError("no model registered yet — run training first")
        vdir = self.root / version
        bundle = json.loads((vdir / "bundle.json").read_bytes())
        manifest = json.loads((vdir / "manifest.json").read_text())
        return {"version": version, "bundle": bundle, "manifest": manifest}

    def list_versions(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir()
                      if p.is_dir() and (p / "manifest.json").exists())
