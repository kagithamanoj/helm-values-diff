# helm-values-diff

Diff two Helm values files and show what actually changes for a release.

A plain YAML diff shows every line that moved. This shows the keys that
changed, in dotted-path form, so a release review answers one question:
what is different in the values going out. Lists of named items (env
vars, ports, volume mounts) are matched by name, not by position, so
reordering them is not reported as a change.

## Install

```bash
pip install helm-values-diff
```

Or from source:

```bash
pip install -e .
```

## Use

```bash
helm-values-diff values-old.yaml values-new.yaml
helm-values-diff --format json values-old.yaml values-new.yaml
helm-values-diff --ignore image.tag values-old.yaml values-new.yaml
```

Exit code is 0 when the files match, 1 when differences are found, and
2 on usage errors such as a missing file or invalid YAML. That makes it
usable as a CI gate: a non-zero exit from the diff step means the release
actually changes something.

## Example

`examples/values-old.yaml` and `examples/values-new.yaml` differ in a
replica count, an image tag, a CPU limit, one env var, a new env var,
and ingress settings. Running the tool prints:

```
7 change(s): 2 added, 5 changed across 5 top-level key(s): env, image, ingress, replicaCount, resources

Added:
  + env[name=FEATURE_X] = {"name": "FEATURE_X", "value": "true"}
  + ingress.className = "nginx"

Changed:
  ~ replicaCount: 2 -> 3
  ~ image.tag: "1.0" -> "1.1"
  ~ resources.limits.cpu: "500m" -> "1"
  ~ env[name=LOG_LEVEL].value: "info" -> "debug"
  ~ ingress.enabled: false -> true
```

## Options

| Flag | Meaning |
| --- | --- |
| `--format text\|json\|markdown` | Output format (default text). Markdown is meant for pasting into a PR description or release note |
| `--ignore PATH` | Dotted path to ignore, for example `image.tag`. Repeatable, or comma-separated. Ignores a whole subtree |

## How it compares values

| Situation | Handling |
| --- | --- |
| Same key, different scalar | Reported as changed, with old and new values |
| Key only in one file | Reported as added or removed, with the whole subtree as one change |
| Plain lists | Compared position by position; a longer list reports added tail items |
| Named lists (every item a mapping with a unique `name`) | Matched by name, so reordering is not a change and a renamed value shows as one change on that item |
| `true` vs `1` | Different values: YAML booleans and numbers are not the same type |
| `2` vs `2.0` | Equal: numbers compare by value |
| Empty file | Treated as an empty mapping |

A values file must hold a single YAML mapping at the top level. Empty
files and comment-only files count as empty mappings.
