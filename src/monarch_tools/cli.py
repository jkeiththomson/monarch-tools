from __future__ import annotations

import argparse
from pathlib import Path

from .extractors.chase import extract_chase_statement_csvs


def cmd_extract(args: argparse.Namespace) -> int:
    pdf_path = Path(args.statement_pdf).expanduser().resolve()
    summary_csv, activity_csv = extract_chase_statement_csvs(pdf_path)

    print(f"Wrote: {summary_csv}")
    print(f"Wrote: {activity_csv}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m monarch_tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract Chase statement summary + activity CSVs")
    p_extract.add_argument("statement_pdf", help="Path to <stem>.statement.pdf (Chase Visa PDF)")
    p_extract.set_defaults(func=cmd_extract)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))