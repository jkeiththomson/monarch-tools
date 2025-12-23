from __future__ import annotations

import argparse

def cmd_extract(_: argparse.Namespace) -> int:
    print("extract: stub (Phase 1)")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m monarch_tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract transactions from a statement PDF (stub for now)")
    p_extract.set_defaults(func=cmd_extract)

    return p

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
