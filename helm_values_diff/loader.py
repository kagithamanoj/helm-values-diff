"""Load a Helm values file (YAML) into a plain Python tree."""

from __future__ import annotations

import yaml


class ValuesError(ValueError):
    """Raised when a values file cannot be loaded or is not a mapping."""


def load_values(path: str) -> dict:
    """Parse a values YAML file. An empty file means an empty mapping.
    Multi-document files and non-mapping top levels are rejected: Helm
    values files are a single mapping.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise ValuesError(f"cannot read {path}: {exc}") from exc
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as exc:
        raise ValuesError(f"{path} is not valid YAML: {exc}") from exc
    docs = [doc for doc in docs if doc is not None]
    if len(docs) > 1:
        raise ValuesError(f"{path} has {len(docs)} YAML documents; "
                          "a values file must hold a single mapping")
    if not docs:
        return {}
    top = docs[0]
    if not isinstance(top, dict):
        raise ValuesError(f"{path} must hold a YAML mapping at the top "
                          f"level, not {type(top).__name__}")
    return top
