from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pdfplumber


SPACE_RE = re.compile(r"\s{2,}")
ACCOUNT_SUMMARY_RE = re.compile(r"\bACCOUNT\s+SUMMARY\b", re.IGNORECASE)
ACCOUNT_ACTIVITY_RE = re.compile(r"\bACCOUNT\s+ACTIVITY\b", re.IGNORECASE)
ACCOUNT_ACTIVITY_CONT_RE = re.compile(r"\bACCOUNT\s+ACTIVITY\s*\(CONTINUED\)\b", re.IGNORECASE)

# Example: "Opening/Closing Date: 12/13/17 – 01/12/18"
DATE_RANGE_RE = re.compile(
    r"Opening/Closing\s+Date\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*[–-]\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

ACCOUNT_NUMBER_RE = re.compile(
    r"\bAccount\s+Number\b\s*[:#]?\s*([0-9Xx*\- ]{6,})", re.IGNORECASE
)

# Transaction line: "MM/DD  DESCRIPTION....   $12.34"
TXN_LINE_RE = re.compile(
    r"^\s*(?P<md>\d{1,2}/\d{1,2})\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<amt>[+\-−]?\s*\$?\s*\(?\s*(?:\d[\d,]*|\d)?(?:\.\d{2})\s*\)?)\s*$"
)

SUMMARY_FIELDS_ORDER = [
    "Account Number",
    "Previous Balance",
    "Payment, Credits",
    "Purchases",
    "Cash Advances",
    "Balance Transfers",
    "Fees Charged",
    "Interest Charged",
    "New Balance",
    "Opening/Closing Date",
    "Credit Access Line",
    "Available Credit",
    "Cash Access Line",
    "Available for Cash",
    "Past Due Amount",
    "Balance over the Credit Access Line",
]


def _norm(s: str) -> str:
    s = s.replace("\u2212", "-")  # unicode minus
    s = s.replace("\u2013", "–")  # en dash
    s = s.replace("\u2014", "—")
    s = SPACE_RE.sub(" ", s)
    return s.strip()


def _read_all_pages_text(pdf_path: Path) -> List[str]:
    pages: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            pages.append(_norm(t))
    return pages


def _parse_mmddyyyy(s: str) -> date:
    parts = s.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"bad date: {s}")
    m = int(parts[0])
    d = int(parts[1])
    y = int(parts[2])
    if y < 100:
        y += 2000 if y <= 69 else 1900
    return date(y, m, d)


def _amount_to_decimal(raw: str) -> Decimal:
    """
    Parse to Decimal for totals.
    - Keeps sign semantics:
      - parentheses => negative
      - leading - => negative
      - leading + => positive
      - if no explicit sign, treat as DEBIT => negative (per spec: debits negative, credits positive)
    """
    s = raw.strip().replace(" ", "")
    s = s.replace("\u2212", "-")
    neg = False

    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]

    sign = ""
    if s.startswith("+"):
        sign = "+"
        s = s[1:]
    elif s.startswith("-"):
        sign = "-"
        neg = True
        s = s[1:]
    else:
        # no explicit sign -> treat as debit (negative) per spec
        neg = True

    if s.startswith("$"):
        s = s[1:]
    s = s.replace(",", "")

    # handle ".99" => "0.99"
    if s.startswith("."):
        s = "0" + s

    try:
        val = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"cannot parse amount: {raw!r}")

    return -val if neg else val


def _format_amount_for_csv(raw: str) -> str:
    """
    Output Amount string preserving $, commas, parentheses and +/- symbols where present.
    If there is no explicit sign, we prefix '-' to enforce 'debits negative' per spec.
    """
    s = raw.strip().replace("\u2212", "-")
    s = re.sub(r"\s+", "", s)

    # normalize ".99" -> "$0.99" only if it appears without $ and without leading 0
    # but keep as close as possible to original: we only fix the numeric part.
    def fix_decimal(token: str) -> str:
        if token.startswith("."):
            return "0" + token
        return token

    # strip outer parentheses, fix decimal inside, then re-wrap
    if s.startswith("(") and s.endswith(")"):
        inner = s[1:-1]
        inner = inner.replace("$", "")
        inner = fix_decimal(inner)
        # preserve parentheses style
        if "$" in s:
            return f"(${inner})" if not inner.startswith("$") else f"({inner})"
        return f"({inner})"

    # detect explicit sign
    explicit = s.startswith(("+", "-")) or s.startswith("$+") or s.startswith("$-")
    if s.startswith("$+") or s.startswith("$-"):
        # move sign to front: $-12.34 -> -$12.34
        sign = s[1]
        rest = s[2:]
        s = sign + "$" + rest
        explicit = True

    # ensure numeric portion ".99" becomes "0.99"
    # keep $ if present
    if s.startswith(("+", "-")):
        sign = s[0]
        rest = s[1:]
        if rest.startswith("$"):
            rest2 = rest[1:]
            rest2 = fix_decimal(rest2)
            s = sign + "$" + rest2
        else:
            rest = fix_decimal(rest)
            s = sign + rest
    elif s.startswith("$"):
        s2 = s[1:]
        s2 = fix_decimal(s2)
        s = "$" + s2
    else:
        s = fix_decimal(s)

    # If no explicit sign and not parentheses => debit negative per spec
    if not explicit and not s.startswith("("):
        if s.startswith("$"):
            s = "-" + s
        else:
            s = "-" + s

    return s


def _extract_summary_block(all_text: str) -> str:
    # return a window of text after ACCOUNT SUMMARY
    m = ACCOUNT_SUMMARY_RE.search(all_text)
    if not m:
        raise ValueError("Could not find ACCOUNT SUMMARY section")
    start = m.start()
    # take a generous slice
    return all_text[start : start + 4000]


def _extract_summary_fields(summary_block: str) -> Tuple[dict, date, int]:
    """
    Returns: (fields dict, closing_date, closing_month)
    """
    fields: dict[str, str] = {}

    # Account number
    m_acct = ACCOUNT_NUMBER_RE.search(summary_block)
    if m_acct:
        fields["Account Number"] = _norm(m_acct.group(1))

    # Date range (must exist to infer year)
    m_range = DATE_RANGE_RE.search(summary_block)
    if not m_range:
        raise ValueError("Could not find Opening/Closing Date in summary")
    open_d = _parse_mmddyyyy(m_range.group(1))
    close_d = _parse_mmddyyyy(m_range.group(2))
    fields["Opening/Closing Date"] = f"{m_range.group(1)} – {m_range.group(2)}"

    # Helper to grab labeled currency lines
    def grab(label: str) -> Optional[str]:
        # match "Label: <value>" or "Label <value>"
        # values may include + - ( ) $ , and decimals
        pat = re.compile(
            rf"\b{re.escape(label)}\b\s*[: ]\s*([+\-−]?\s*\$?\s*\(?\s*(?:\d[\d,]*|\d)?(?:\.\d{{2}})\s*\)?)",
            re.IGNORECASE,
        )
        m = pat.search(summary_block)
        if not m:
            return None
        v = _norm(m.group(1))
        v = v.replace("\u2212", "-")
        # preserve currency symbols + commas, keep leading +
        v = re.sub(r"\s+", "", v)
        # Fix ".99" -> "0.99" in the numeric portion
        if v.startswith(("+", "-")):
            sign = v[0]
            rest = v[1:]
            if rest.startswith("$"):
                rest = "$" + (("0" + rest[1:]) if rest[1:].startswith(".") else rest[1:])
                v = sign + rest
            else:
                v = sign + (("0" + rest) if rest.startswith(".") else rest)
        else:
            if v.startswith("$"):
                v = "$" + (("0" + v[1:]) if v[1:].startswith(".") else v[1:])
            else:
                v = ("0" + v) if v.startswith(".") else v
        return v

    # Map Chase labels to required output field names
    label_map = {
        "Previous Balance": "Previous Balance",
        "Payment, Credits": "Payment, Credits",
        "Purchases": "Purchases",
        "Cash Advances": "Cash Advances",
        "Balance Transfers": "Balance Transfers",
        "Fees Charged": "Fees Charged",
        "Interest Charged": "Interest Charged",
        "New Balance": "New Balance",
        "Credit Access Line": "Credit Access Line",
        "Available Credit": "Available Credit",
        "Cash Access Line": "Cash Access Line",
        "Available for Cash": "Available for Cash",
        "Past Due Amount": "Past Due Amount",
        "Balance over the Credit Access Line": "Balance over the Credit Access Line",
    }

    for out_field, label in label_map.items():
        v = grab(label)
        if v is not None:
            # Purchases must be numeric only (no descriptive text)
            if out_field == "Purchases":
                v2 = v.replace("$", "")
                fields[out_field] = v2
            else:
                fields[out_field] = v

    return fields, close_d, close_d.month


def _iter_activity_lines(pages_text: List[str]) -> Iterable[str]:
    """
    Yield candidate lines from pages that contain ACCOUNT ACTIVITY headers.
    """
    for page in pages_text:
        if not ACCOUNT_ACTIVITY_RE.search(page):
            continue

        # Split into lines; keep those after the first "ACCOUNT ACTIVITY"
        lines = page.splitlines()

        # Find first activity header line index
        start_idx = 0
        for i, ln in enumerate(lines):
            if ACCOUNT_ACTIVITY_RE.search(ln):
                start_idx = i
                break

        # Yield remaining lines after header
        for ln in lines[start_idx + 1 :]:
            ln = _norm(ln)
            if not ln:
                continue
            yield ln


@dataclass(frozen=True)
class Transaction:
    date_iso: str
    description: str
    amount_str: str
    amount_dec: Decimal


def _parse_transactions(lines: Iterable[str], closing_year: int, closing_month: int) -> List[Transaction]:
    txns: List[Transaction] = []

    for ln in lines:
        m = TXN_LINE_RE.match(ln)
        if not m:
            continue

        md = m.group("md")
        desc = m.group("desc").strip()
        amt_raw = m.group("amt").strip()

        # Remove any leading ampersands from description
        desc = desc.lstrip("&").strip()

        # Infer year using closing month logic
        mm_s, dd_s = md.split("/")
        mm = int(mm_s)
        dd = int(dd_s)
        year = closing_year - 1 if mm > closing_month else closing_year
        date_iso = f"{year:04d}-{mm:02d}-{dd:02d}"

        amt_csv = _format_amount_for_csv(amt_raw)
        amt_dec = _amount_to_decimal(amt_raw)

        txns.append(Transaction(date_iso=date_iso, description=desc, amount_str=amt_csv, amount_dec=amt_dec))

    return txns


def extract_chase_statement_csvs(pdf_path: str | Path) -> Tuple[Path, Path]:
    """
    Extracts:
      - <stem>.summary.csv
      - <stem>.activity.csv (with footer summary)
    Returns (summary_path, activity_path)
    """
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    pages_text = _read_all_pages_text(pdf_path)
    all_text = _norm("\n".join(pages_text))

    summary_block = _extract_summary_block(all_text)
    summary_fields, closing_date, closing_month = _extract_summary_fields(summary_block)

    # Ensure Account Number exists as a field even if not found
    summary_fields.setdefault("Account Number", "")

    # Output paths
    out_dir = pdf_path.parent
    stem = pdf_path.stem
    summary_csv = out_dir / f"{stem}.summary.csv"
    activity_csv = out_dir / f"{stem}.activity.csv"

    # --- Write summary CSV ---
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Field", "Value"])
        for field in SUMMARY_FIELDS_ORDER:
            w.writerow([field, summary_fields.get(field, "")])

    # --- Parse activity ---
    lines = list(_iter_activity_lines(pages_text))
    txns = _parse_transactions(lines, closing_year=closing_date.year, closing_month=closing_month)

    # Totals and counts
    pos = [t for t in txns if t.amount_dec > 0]
    neg = [t for t in txns if t.amount_dec < 0]
    total_pos = sum((t.amount_dec for t in pos), Decimal("0"))
    total_neg = sum((t.amount_dec for t in neg), Decimal("0"))

    # --- Write activity CSV with footer ---
    with activity_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Amount"])
        for t in txns:
            w.writerow([t.date_iso, t.description, t.amount_str])

        # blank row
        w.writerow([])
        # footer rows (keep other columns empty)
        w.writerow(["Credit transactions (count)", "", str(len(pos))])
        w.writerow(["Debit transactions (count)", "", str(len(neg))])
        w.writerow(["Total credits", "", f"{total_pos}"])
        w.writerow(["Total debits", "", f"{total_neg}"])

    # Console log footer too
    print(f"Credit transactions (count),,{len(pos)}")
    print(f"Debit transactions (count),,{len(neg)}")
    print(f"Total credits,,{total_pos}")
    print(f"Total debits,,{total_neg}")

    return summary_csv, activity_csv