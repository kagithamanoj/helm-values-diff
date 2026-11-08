"""Command line interface: helm-values-diff OLD.yaml NEW.yaml."""

import argparse
import sys

from .diff import diff_values
from .loader import ValuesError, load_values
from .report import to_json, to_markdown, to_text

FORMATS = ("text", "json", "markdown")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="helm-values-diff",
        description="Diff two Helm values files and show what actually "
                    "changes for a release.",
    )
    parser.add_argument("old", metavar="OLD.yaml",
                        help="current values file")
    parser.add_argument("new", metavar="NEW.yaml",
                        help="new values file")
    parser.add_argument("--format", choices=FORMATS, default="text",
                        help="output format: text, json, or markdown "
                             "(default text)")
    parser.add_argument("--ignore", action="append", default=[],
                        metavar="PATH",
                        help="dotted path to ignore (repeatable, or "
                             "comma-separated); ignores a whole subtree")
    return parser


def _parse_ignores(raw: list[str]) -> tuple:
    ignored: list[str] = []
    for item in raw:
        ignored.extend(part.strip() for part in item.split(",")
                       if part.strip())
    return tuple(ignored)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        old = load_values(args.old)
        new = load_values(args.new)
    except ValuesError as exc:
        print(f"helm-values-diff: {exc}", file=sys.stderr)
        return 2
    changes = diff_values(old, new, ignore=_parse_ignores(args.ignore))
    if args.format == "json":
        print(to_json(changes), end="")
    elif args.format == "markdown":
        print(to_markdown(changes), end="")
    else:
        print(to_text(changes), end="")
    return 1 if changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
