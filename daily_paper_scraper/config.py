from __future__ import annotations
from pathlib import Path
import yaml
import os


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    # Env vars override yaml values if set
    if os.environ.get("NOTION_TOKEN"):
        cfg.setdefault("notion", {})["token"] = os.environ["NOTION_TOKEN"]
    if os.environ.get("NOTION_DATABASE_ID"):
        cfg.setdefault("notion", {})["database_id"] = os.environ["NOTION_DATABASE_ID"]
    return cfg


def get_project_root() -> Path:
    return Path(__file__).parent.parent
