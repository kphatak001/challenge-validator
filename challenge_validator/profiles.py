"""Load vendor profiles from YAML files."""

import os
from pathlib import Path

import yaml

PROFILES_DIR = Path(__file__).parent / "profiles"


def list_profiles() -> list[str]:
    """Return available profile names."""
    return [p.stem for p in PROFILES_DIR.glob("*.yaml")]


def load_profile(name: str) -> dict:
    """Load a vendor profile by name."""
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile '{name}' not found. Available: {list_profiles()}")
    with open(path) as f:
        return yaml.safe_load(f)
