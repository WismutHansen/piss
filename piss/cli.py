"""`piss` on the command line."""

from __future__ import annotations

import argparse
import sys

from .errors import WaterFault
from .interp import Interpreter
from .parser import parse

VERSION = "0.1.0"

BANNER = "piss {} - the world's most fluid programming language".format(VERSION)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="piss",
        description=BANNER,
        epilog="Water flows downhill, in one direction, and evaporates if you hoard it.",
    )
    parser.add_argument("--version", action="version", version=f"piss {VERSION}")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run a program")
    run.add_argument("file", help="a .piss file, or - for stdin")
    run.add_argument(
        "--decay",
        type=int,
        default=6,
        metavar="N",
        help="statements a binding may go unread before it evaporates (0 disables, default 6)",
    )
    run.add_argument("-q", "--quiet", action="store_true", help="swallow program output")

    check = sub.add_parser("check", help="parse without executing")
    check.add_argument("file")

    return parser


def read_source(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        source = read_source(args.file)
    except OSError as exc:
        print(f"piss: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2

    try:
        program = parse(source)
    except WaterFault as exc:
        print(f"piss: {exc.kind}: {exc}", file=sys.stderr)
        return 1

    if args.command == "check":
        print(f"{args.file}: parses clean ({len(program.body)} top-level statement(s))")
        return 0

    decay = max(0, args.decay)
    interpreter = Interpreter(decay=decay, out=None if args.quiet else sys.stdout)
    try:
        interpreter.run(program)
    except WaterFault as exc:
        sys.stdout.flush()
        print(f"piss: {exc.kind}: {exc}", file=sys.stderr)
        return 1
    except RecursionError:
        sys.stdout.flush()
        print("piss: burst: the drain overflowed (deep recursion)", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
