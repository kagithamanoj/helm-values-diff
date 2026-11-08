"""Core diff engine: compare two parsed Helm values trees.

A values tree is the nested dict/list/scalar structure you get from
parsing a values.yaml file. The diff walks both trees and reports one
Change per leaf that was added, removed, or changed. Paths use dotted
notation (``image.tag``); list items use ``[n]`` unless the list is a
named list (every item a mapping with a unique ``name`` key), in which
case items are addressed by name, for example ``env[name=LOG_LEVEL]``.
That matches how Helm values usually hold env vars, ports, and
volume mounts, where order does not matter but the name does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MISSING = object()


@dataclass(frozen=True)
class Change:
    """One difference between the old and new values trees."""

    path: str
    kind: str  # "added" | "removed" | "changed"
    old: Any = None
    new: Any = None

    @property
    def top_key(self) -> str:
        """The top-level values key this change belongs to."""
        return self.path.split(".")[0].split("[")[0]


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))


def _scalars_equal(old: Any, new: Any) -> bool:
    # bool is a subclass of int in Python, but in YAML true and 1 are
    # different values, so compare types first for scalars.
    if isinstance(old, bool) or isinstance(new, bool):
        return type(old) is type(new) and old == new
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return old == new
    return type(old) is type(new) and old == new


def _named_list(items: list) -> dict | None:
    """Index a list of mappings by their ``name`` key, or None.

    Returns None when the list is not a named list: any item is not a
    mapping, lacks a string ``name``, or names repeat.
    """
    index: dict = {}
    for item in items:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        if not isinstance(name, str) or name in index:
            return None
        index[name] = item
    return index


def _diff_lists(old: list, new: list, path: str, changes: list,
                ignore: tuple) -> None:
    old_by_name = _named_list(old)
    new_by_name = _named_list(new)
    if old_by_name is not None and new_by_name is not None:
        for name in old_by_name:
            item_path = f"{path}[name={name}]" if path else f"[name={name}]"
            if name not in new_by_name:
                changes.append(Change(item_path, "removed",
                                      old=old_by_name[name]))
            else:
                _diff_any(old_by_name[name], new_by_name[name],
                          item_path, changes, ignore)
        for name in new_by_name:
            if name not in old_by_name:
                item_path = f"{path}[name={name}]" if path else f"[name={name}]"
                changes.append(Change(item_path, "added",
                                      new=new_by_name[name]))
        return
    for index in range(max(len(old), len(new))):
        item_path = f"{path}[{index}]" if path else f"[{index}]"
        if index >= len(old):
            changes.append(Change(item_path, "added", new=new[index]))
        elif index >= len(new):
            changes.append(Change(item_path, "removed", old=old[index]))
        else:
            _diff_any(old[index], new[index], item_path, changes, ignore)


def _ignored(path: str, ignore: tuple) -> bool:
    for prefix in ignore:
        if path == prefix or path.startswith(prefix + ".") \
                or path.startswith(prefix + "["):
            return True
    return False


def _diff_any(old: Any, new: Any, path: str, changes: list,
              ignore: tuple) -> None:
    if _ignored(path, ignore):
        return
    if isinstance(old, dict) and isinstance(new, dict):
        for key in old:
            child = f"{path}.{key}" if path else str(key)
            if key not in new:
                if not _ignored(child, ignore):
                    changes.append(Change(child, "removed", old=old[key]))
            else:
                _diff_any(old[key], new[key], child, changes, ignore)
        for key in new:
            if key not in old:
                child = f"{path}.{key}" if path else str(key)
                if not _ignored(child, ignore):
                    changes.append(Change(child, "added", new=new[key]))
        return
    if isinstance(old, list) and isinstance(new, list):
        _diff_lists(old, new, path, changes, ignore)
        return
    if _is_scalar(old) and _is_scalar(new):
        if not _scalars_equal(old, new):
            changes.append(Change(path, "changed", old=old, new=new))
        return
    # One side is a container and the other is not: a type change.
    changes.append(Change(path, "changed", old=old, new=new))


def diff_values(old: dict, new: dict,
                ignore: tuple = ()) -> list[Change]:
    """Diff two parsed values trees. Returns changes in a stable order:
    removals and changes in old-file order, additions in new-file order.
    """
    changes: list[Change] = []
    _diff_any(old, new, "", changes, tuple(ignore))
    return changes


def summarize(changes: list[Change]) -> dict:
    """Count changes by kind and by top-level key."""
    counts = {"added": 0, "removed": 0, "changed": 0}
    by_top: dict[str, int] = {}
    for change in changes:
        counts[change.kind] += 1
        by_top[change.top_key] = by_top.get(change.top_key, 0) + 1
    return {"total": len(changes), "by_kind": counts, "by_top_key": by_top}
