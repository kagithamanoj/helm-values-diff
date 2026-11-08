"""Tests for the values file loader."""

import pytest

from helm_values_diff.loader import ValuesError, load_values


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_loads_simple_mapping(tmp_path):
    path = write(tmp_path, "v.yaml", "replicas: 3\nimage:\n  tag: \"1.2\"\n")
    assert load_values(path) == {"replicas": 3, "image": {"tag": "1.2"}}


def test_empty_file_is_empty_mapping(tmp_path):
    path = write(tmp_path, "v.yaml", "")
    assert load_values(path) == {}


def test_comment_only_file_is_empty_mapping(tmp_path):
    path = write(tmp_path, "v.yaml", "# nothing here\n")
    assert load_values(path) == {}


def test_missing_file(tmp_path):
    with pytest.raises(ValuesError, match="cannot read"):
        load_values(str(tmp_path / "nope.yaml"))


def test_invalid_yaml(tmp_path):
    path = write(tmp_path, "v.yaml", "a: [unclosed\n")
    with pytest.raises(ValuesError, match="not valid YAML"):
        load_values(path)


def test_multi_document_rejected(tmp_path):
    path = write(tmp_path, "v.yaml", "a: 1\n---\nb: 2\n")
    with pytest.raises(ValuesError, match="single mapping"):
        load_values(path)


def test_non_mapping_top_level_rejected(tmp_path):
    path = write(tmp_path, "v.yaml", "- a\n- b\n")
    with pytest.raises(ValuesError, match="top level"):
        load_values(path)


def test_types_preserved(tmp_path):
    path = write(tmp_path, "v.yaml",
                 "flag: true\ncount: 3\nratio: 1.5\nname: web\nnone: null\n")
    assert load_values(path) == {
        "flag": True, "count": 3, "ratio": 1.5, "name": "web", "none": None,
    }
