"""Tests for the diff engine."""

from helm_values_diff.diff import Change, diff_values, summarize


def changes(old, new, ignore=()):
    return diff_values(old, new, ignore=ignore)


def test_identical_trees_have_no_changes():
    assert changes({"a": 1}, {"a": 1}) == []


def test_scalar_change():
    assert changes({"image": {"tag": "1.0"}}, {"image": {"tag": "1.1"}}) == [
        Change("image.tag", "changed", old="1.0", new="1.1"),
    ]


def test_added_and_removed_keys():
    result = changes({"a": 1, "b": 2}, {"a": 1, "c": 3})
    assert result == [
        Change("b", "removed", old=2),
        Change("c", "added", new=3),
    ]


def test_added_subtree_is_one_change():
    result = changes({}, {"sidecar": {"enabled": True, "image": "x:1"}})
    assert result == [Change("sidecar", "added",
                             new={"enabled": True, "image": "x:1"})]


def test_bool_and_int_are_different():
    assert changes({"flag": True}, {"flag": 1}) == [
        Change("flag", "changed", old=True, new=1),
    ]


def test_int_and_float_with_same_value_are_equal():
    assert changes({"replicas": 2}, {"replicas": 2.0}) == []


def test_null_to_value_is_a_change():
    assert changes({"token": None}, {"token": "abc"}) == [
        Change("token", "changed", old=None, new="abc"),
    ]


def test_scalar_replaced_by_mapping():
    result = changes({"a": "x"}, {"a": {"b": 1}})
    assert result == [Change("a", "changed", old="x", new={"b": 1})]


def test_plain_list_diff_is_index_based():
    result = changes({"hosts": ["a", "b"]}, {"hosts": ["a", "c", "d"]})
    assert result == [
        Change("hosts[1]", "changed", old="b", new="c"),
        Change("hosts[2]", "added", new="d"),
    ]


def test_list_shrink_reports_removed_tail():
    result = changes({"hosts": ["a", "b", "c"]}, {"hosts": ["a"]})
    assert result == [
        Change("hosts[1]", "removed", old="b"),
        Change("hosts[2]", "removed", old="c"),
    ]


def test_named_list_matches_by_name_not_position():
    old = {"env": [{"name": "A", "value": "1"},
                   {"name": "B", "value": "2"}]}
    new = {"env": [{"name": "B", "value": "20"},
                   {"name": "A", "value": "1"},
                   {"name": "C", "value": "3"}]}
    result = changes(old, new)
    assert result == [
        Change("env[name=B].value", "changed", old="2", new="20"),
        Change("env[name=C]", "added", new={"name": "C", "value": "3"}),
    ]


def test_named_list_removed_item():
    old = {"env": [{"name": "A", "value": "1"}]}
    result = changes(old, {"env": []})
    assert result == [Change("env[name=A]", "removed",
                             old={"name": "A", "value": "1"})]


def test_duplicate_names_fall_back_to_index_diff():
    old = {"env": [{"name": "A", "value": "1"},
                   {"name": "A", "value": "2"}]}
    new = {"env": [{"name": "A", "value": "9"},
                   {"name": "A", "value": "2"}]}
    assert changes(old, new) == [
        Change("env[0].value", "changed", old="1", new="9"),
    ]


def test_list_of_scalars_without_name_is_index_based():
    old = {"ports": [{"port": 80}, {"port": 443}]}
    new = {"ports": [{"port": 443}, {"port": 80}]}
    assert changes(old, new) == [
        Change("ports[0].port", "changed", old=80, new=443),
        Change("ports[1].port", "changed", old=443, new=80),
    ]


def test_nested_change_path():
    result = changes(
        {"a": {"b": {"c": {"d": 1}}}}, {"a": {"b": {"c": {"d": 2}}}})
    assert result == [Change("a.b.c.d", "changed", old=1, new=2)]


def test_ignore_subtree():
    old = {"image": {"tag": "1.0"}, "replicas": 1}
    new = {"image": {"tag": "2.0"}, "replicas": 2}
    assert changes(old, new, ignore=("image",)) == [
        Change("replicas", "changed", old=1, new=2),
    ]


def test_ignore_leaf_path():
    old = {"a": {"b": 1, "c": 2}}
    new = {"a": {"b": 9, "c": 2}}
    assert changes(old, new, ignore=("a.b",)) == []


def test_ignore_named_list_item():
    old = {"env": [{"name": "A", "value": "1"}]}
    new = {"env": [{"name": "A", "value": "2"}]}
    assert changes(old, new, ignore=("env[name=A]",)) == []


def test_summarize_counts():
    result = changes({"a": 1, "b": 2}, {"a": 9, "c": 3, "d": {"e": 4}})
    info = summarize(result)
    assert info["total"] == 4
    assert info["by_kind"] == {"added": 2, "removed": 1, "changed": 1}
    assert info["by_top_key"] == {"a": 1, "b": 1, "c": 1, "d": 1}
