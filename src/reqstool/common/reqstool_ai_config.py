# Copyright © LFV

from pathlib import Path
from typing import Optional

import yaml

CONFIG_FILENAME = ".reqstool-ai.yaml"


def find_config(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from `start` (default cwd) until `.reqstool-ai.yaml` is found.

    Returns the absolute path to the config file, or None if not found.
    """
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def resolve_system_path(config_path: Path) -> Path:
    """Read `system.path` from the config and resolve it against the config's directory.

    Raises ValueError if `system` or `system.path` is missing or not a string.
    """
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    system = data.get("system")
    if not isinstance(system, dict):
        raise ValueError(f"{config_path}: missing required 'system' mapping")

    raw_path = system.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"{config_path}: missing required 'system.path' string")

    return (config_path.parent / raw_path).resolve()
