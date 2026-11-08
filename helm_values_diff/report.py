"""Render a list of Changes as text, JSON, or Markdown."""

from __future__ import annotations

import json

from .diff import Change, summarize

_MAX_VALUE_LEN = 200


def format_value(value) -> str:
    """Render a value compactly. Long strings and big containers are
    truncated so one change stays on one line in text output.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        rendered = json.dumps(value)
    else:
        rendered = json.dumps(value, default=str)
    if len(rendered) > _MAX_VALUE_LEN:
        rendered = rendered[: _MAX_VALUE_LEN - 3] + "..."
    return rendered


def _summary_line(changes: list[Change]) -> str:
    info = summarize(changes)
    kinds = info["by_kind"]
    if info["total"] == 0:
        return "No differences."
    parts = []
    if kinds["added"]:
        parts.append(f"{kinds['added']} added")
    if kinds["removed"]:
        parts.append(f"{kinds['removed']} removed")
    if kinds["changed"]:
        parts.append(f"{kinds['changed']} changed")
    tops = sorted(info["by_top_key"])
    return (f"{info['total']} change(s): {', '.join(parts)} "
            f"across {len(tops)} top-level key(s): {', '.join(tops)}")


def to_text(changes: list[Change]) -> str:
    """Grouped text report: summary line, then Added/Removed/Changed."""
    lines = [_summary_line(changes)]
    for kind, heading in (("added", "Added"),
                          ("removed", "Removed"),
                          ("changed", "Changed")):
        group = [c for c in changes if c.kind == kind]
        if not group:
            continue
        lines.append("")
        lines.append(f"{heading}:")
        for change in group:
            if kind == "added":
                lines.append(f"  + {change.path} = {format_value(change.new)}")
            elif kind == "removed":
                lines.append(f"  - {change.path} was {format_value(change.old)}")
            else:
                lines.append(f"  ~ {change.path}: "
                             f"{format_value(change.old)} -> "
                             f"{format_value(change.new)}")
    return "\n".join(lines) + "\n"


def to_json(changes: list[Change]) -> str:
    """Machine-readable report: summary plus one object per change."""
    doc = {
        "summary": summarize(changes),
        "changes": [
            {"path": c.path, "kind": c.kind, "old": c.old, "new": c.new}
            for c in changes
        ],
    }
    return json.dumps(doc, indent=2, default=str) + "\n"


def to_markdown(changes: list[Change]) -> str:
    """Markdown report for pasting into a PR description or release note."""
    lines = ["## Values diff", "", _summary_line(changes)]
    if not changes:
        return "\n".join(lines) + "\n"
    lines += ["", "| Change | Path | Old | New |", "| --- | --- | --- | --- |"]
    for change in changes:
        mark = {"added": "+", "removed": "-", "changed": "~"}[change.kind]
        old = "" if change.kind == "added" else format_value(change.old)
        new = "" if change.kind == "removed" else format_value(change.new)
        lines.append(f"| {mark} | `{change.path}` | {old} | {new} |")
    return "\n".join(lines) + "\n"
