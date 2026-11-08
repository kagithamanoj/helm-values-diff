"""Tests for the text, JSON, and Markdown reports."""

import json

from helm_values_diff.diff import Change
from helm_values_diff.report import format_value, to_json, to_markdown, to_text


def test_text_no_differences():
    assert to_text([]) == "No differences.\n"


def test_text_groups_by_kind():
    changes = [
        Change("b", "removed", old=2),
        Change("a.x", "changed", old=1, new=2),
        Change("c", "added", new=3),
    ]
    text = to_text(changes)
    assert text.startswith(
        "3 change(s): 1 added, 1 removed, 1 changed "
        "across 3 top-level key(s): a, b, c\n")
    assert "\nAdded:\n  + c = 3\n" in text
    assert "\nRemoved:\n  - b was 2\n" in text
    assert "\nChanged:\n  ~ a.x: 1 -> 2\n" in text


def test_text_skips_empty_groups():
    text = to_text([Change("a", "added", new=1)])
    assert "Removed:" not in text
    assert "Changed:" not in text


def test_json_round_trip():
    changes = [Change("a", "changed", old=1, new=2),
               Change("b", "added", new={"x": True})]
    doc = json.loads(to_json(changes))
    assert doc["summary"]["total"] == 2
    assert doc["changes"][0] == {
        "path": "a", "kind": "changed", "old": 1, "new": 2,
    }
    assert doc["changes"][1]["new"] == {"x": True}


def test_markdown_table():
    changes = [Change("a", "changed", old=1, new=2),
               Change("b", "removed", old="x")]
    md = to_markdown(changes)
    assert md.startswith("## Values diff\n")
    assert "| ~ | `a` | 1 | 2 |" in md
    assert "| - | `b` | \"x\" |  |" in md


def test_markdown_no_differences():
    assert to_markdown([]) == "## Values diff\n\nNo differences.\n"


def test_format_value_scalars():
    assert format_value(None) == "null"
    assert format_value(True) == "true"
    assert format_value(3) == "3"
    assert format_value("web") == '"web"'


def test_format_value_truncates_long_strings():
    assert format_value("x" * 500).endswith("...")
    assert len(format_value("x" * 500)) == 200
