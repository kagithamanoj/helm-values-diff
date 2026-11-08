"""Tests for the CLI: exit codes, formats, ignores, error handling."""

import json

import pytest

from helm_values_diff.cli import main

OLD = """\
replicas: 2
image:
  repository: myapp
  tag: "1.0"
env:
  - name: LOG_LEVEL
    value: info
"""

NEW = """\
replicas: 3
image:
  repository: myapp
  tag: "1.1"
env:
  - name: LOG_LEVEL
    value: debug
"""


@pytest.fixture
def files(tmp_path):
    old = tmp_path / "old.yaml"
    new = tmp_path / "new.yaml"
    old.write_text(OLD, encoding="utf-8")
    new.write_text(NEW, encoding="utf-8")
    return str(old), str(new)


def test_exit_1_when_differences(files, capsys):
    assert main(list(files)) == 1
    out = capsys.readouterr().out
    assert "3 change(s)" in out
    assert "~ image.tag: \"1.0\" -> \"1.1\"" in out
    assert "~ replicas: 2 -> 3" in out
    assert "~ env[name=LOG_LEVEL].value: \"info\" -> \"debug\"" in out


def test_exit_0_when_identical(files, capsys):
    assert main([files[0], files[0]]) == 0
    assert capsys.readouterr().out == "No differences.\n"


def test_json_format(files, capsys):
    assert main([*files, "--format", "json"]) == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["summary"]["total"] == 3
    assert [c["path"] for c in doc["changes"]] == [
        "replicas", "image.tag", "env[name=LOG_LEVEL].value",
    ]


def test_markdown_format(files, capsys):
    assert main([*files, "--format", "markdown"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("## Values diff\n")
    assert "| ~ | `image.tag` | \"1.0\" | \"1.1\" |" in out


def test_ignore_flag(files, capsys):
    assert main([*files, "--ignore", "image.tag",
                 "--ignore", "env"]) == 1
    out = capsys.readouterr().out
    assert "1 change(s)" in out
    assert "replicas" in out
    assert "image.tag" not in out


def test_ignore_comma_separated(files, capsys):
    assert main([*files, "--ignore", "image.tag,replicas"]) == 1
    out = capsys.readouterr().out
    assert "env[name=LOG_LEVEL].value" in out
    assert "image.tag" not in out


def test_missing_file_is_exit_2(capsys):
    assert main(["nope.yaml", "alsono.yaml"]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_invalid_yaml_is_exit_2(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("a: [unclosed\n", encoding="utf-8")
    good = tmp_path / "good.yaml"
    good.write_text("a: 1\n", encoding="utf-8")
    assert main([str(bad), str(good)]) == 2
    assert "not valid YAML" in capsys.readouterr().err


def test_bad_format_is_exit_2(files):
    with pytest.raises(SystemExit) as exc:
        main([*files, "--format", "yaml"])
    assert exc.value.code == 2
