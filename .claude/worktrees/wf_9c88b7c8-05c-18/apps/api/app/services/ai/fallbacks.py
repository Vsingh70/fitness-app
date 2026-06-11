"""Load fallback templates from fallbacks.yaml and render with variables."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from string import Formatter
from typing import Any

import yaml

_GENERIC = "Plan updated based on your last session."


@cache
def _templates() -> dict[str, str]:
    path = Path(__file__).with_name("fallbacks.yaml")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise RuntimeError(f"fallbacks.yaml must be a mapping, got {type(data).__name__}")
    return {str(k): str(v) for k, v in data.items()}


def _fields_in(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name}


def render_fallback(rationale_key: str | None, variables: dict[str, Any] | None = None) -> str:
    """Return a friendly one-sentence string for `rationale_key`.

    Unknown keys, missing variables, or missing template -> generic fallback.
    """
    if not rationale_key:
        return _GENERIC
    template = _templates().get(rationale_key)
    if template is None:
        return _GENERIC
    needed = _fields_in(template)
    if not needed:
        return template
    if variables is None or not needed.issubset(variables.keys()):
        return _GENERIC
    return template.format(**variables)
