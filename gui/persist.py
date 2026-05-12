"""Persist server URL and last-used database on disk."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".graph_engine_gui.json"

DEFAULTS: dict = {
    "base_url": "http://127.0.0.1:8000",
    "database": "neo4j",
    "timeout": 45.0,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        out = dict(DEFAULTS)
        out.update({k: v for k, v in data.items() if k in DEFAULTS})
        return out
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save_config(data: dict) -> None:
    merged = dict(DEFAULTS)
    merged.update({k: data[k] for k in DEFAULTS if k in data})
    CONFIG_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
