import argparse
from pathlib import Path

def cmd_extract(args: argparse.Namespace) -> int:
    pdf_path = Path(args.account_pdf)
    out_path = pdf_path.with_name(f"{pdf_path.stem}.extracted.csv")

    print("extract: stub (Phase 1)")
    print(f"  account_type: {args.account_type}")
    print(f"  account_pdf:  {pdf_path}")
    print(f"  would write:  {out_path}")
    return 0
