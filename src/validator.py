"""Strict validation layer for MCX commodity derivatives data.

Provides:
- Explicit date parsing without ambiguous silent guessing
- Symbol cleaning and root symbol extraction
- Price and volume sanity verification
- Detection of missing values and duplicate records
- Comprehensive DataQualityReport with actionable diagnostics
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from src.contract_specs import GLOBAL_REGISTRY, ContractRegistry


EXPLICIT_DATE_FORMATS = [
    "%d-%b-%Y",  # 15-OCT-2024 / 15-Oct-2024
    "%d-%B-%Y",  # 15-October-2024
    "%d %b %Y",  # 20 Oct 2026
    "%d %B %Y",  # 20 October 2026
    "%d%b%Y",  # 04DEC2026 / 31DEC2026
    "%d%B%Y",  # 04DECEMBER2026
    "%Y-%m-%d",  # 2024-10-15
    "%d-%m-%Y",  # 15-10-2024
    "%d/%m/%Y",  # 15/10/2024
    "%Y/%m/%d",  # 2024/10/15
]


def parse_date_explicitly(val: Any) -> Optional[datetime.date]:
    """Parse a date value strictly using predefined formats without guessing.

    Rejects invalid types or unrecognized strings. Returns None on failure.
    """
    if val is None or pd.isna(val):
        return None

    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, pd.Timestamp):
        return val.date()

    val_str = str(val).strip()
    if not val_str:
        return None

    # Try original string, title-cased string, and upper-cased string
    candidates = [val_str, val_str.title(), val_str.upper()]
    for candidate in candidates:
        for fmt in EXPLICIT_DATE_FORMATS:
            try:
                return datetime.datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    # Attempt regex normalization for split-separated dates (e.g. 15-oct-2024)
    try:
        parts = [p.capitalize() for p in re.split(r"[-/\s]", val_str) if p]
        if len(parts) == 3:
            normalized_hyphen = "-".join(parts)
            normalized_space = " ".join(parts)
            for norm_str in [normalized_hyphen, normalized_space]:
                for fmt in ["%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y"]:
                    try:
                        return datetime.datetime.strptime(norm_str, fmt).date()
                    except ValueError:
                        continue
    except Exception:
        pass

    return None



def clean_symbol(val: Any) -> Tuple[str, str]:
    """Clean symbol string, stripping whitespace and isolating base commodity symbol.

    Returns:
        (clean_symbol, raw_description)
    """
    if val is None or pd.isna(val):
        return "", ""

    raw_str = str(val).strip()
    norm = raw_str.upper()

    # Match known root symbols at the start of a token (e.g. GOLDM24NOVFUT -> GOLDM, GOLDM 05NOV2024 -> GOLDM)
    for root in ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL", "GOLD"]:
        if re.match(rf"^{root}\b", norm) or norm.startswith(root):
            return root, raw_str

    # Fallback to first alphanumeric token
    tokens = re.findall(r"[A-Z0-9]+", norm)
    base = tokens[0] if tokens else norm
    return base, raw_str


@dataclass
class ValidationIssue:
    """Record of a single data validation failure or warning."""

    level: str  # 'ERROR' or 'WARNING'
    category: str
    message: str
    row_index: Optional[int] = None
    contract: Optional[str] = None


@dataclass
class DataQualityReport:
    """Aggregated data quality audit for an ingested dataset."""

    total_rows_ingested: int = 0
    valid_rows_retained: int = 0
    dropped_rows_count: int = 0
    duplicate_rows_count: int = 0

    date_range: Optional[Tuple[datetime.date, datetime.date]] = None
    unique_trade_dates: List[datetime.date] = field(default_factory=list)
    is_single_date: bool = True

    supported_symbols_found: List[str] = field(default_factory=list)
    unsupported_symbols_found: List[str] = field(default_factory=list)

    missing_values_by_column: Dict[str, int] = field(default_factory=dict)
    issues: List[ValidationIssue] = field(default_factory=list)

    date_match_verified: Optional[bool] = None
    expected_date: Optional[datetime.date] = None

    @property
    def has_errors(self) -> bool:
        return any(i.level == "ERROR" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "WARNING")


def validate_market_data(
    df: pd.DataFrame,
    expected_date: Optional[datetime.date] = None,
    registry: Optional[ContractRegistry] = None,
) -> Tuple[pd.DataFrame, DataQualityReport]:
    """Validate, clean, and filter an ingested market dataset.

    Enforces:
    - Non-null required fields
    - Explicit date parsing for Date and ExpiryDate
    - Logical date order: ExpiryDate >= Date
    - Symbol normalization and support categorization
    - Strict positive price rules (Open, High, Low, Close > 0)
    - Price envelope consistency (High >= Open, Close, Low; Low <= Open, Close)
    - Non-negative volume and open interest (>= 0)
    - Deduplication of (Symbol, Date, ExpiryDate)
    - Optional validation that data dates match expected_date
    """
    reg = registry or GLOBAL_REGISTRY
    report = DataQualityReport(
        total_rows_ingested=len(df),
        expected_date=expected_date,
    )

    if df.empty:
        report.issues.append(
            ValidationIssue(
                level="ERROR",
                category="EMPTY_DATASET",
                message="Uploaded dataset is empty (0 rows).",
            )
        )
        return pd.DataFrame(), report

    # 1. Missing canonical columns check
    required_cols = ["Symbol", "Date", "ExpiryDate", "Open", "High", "Low", "Close", "Volume", "OpenInterest"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        report.issues.append(
            ValidationIssue(
                level="ERROR",
                category="SCHEMA_MISSING_COLUMNS",
                message=f"Missing required canonical columns: {', '.join(missing_cols)}",
            )
        )
        return pd.DataFrame(), report

    # 2. Track missing values per column
    for col in required_cols:
        null_count = int(df[col].isna().sum())
        report.missing_values_by_column[col] = null_count
        if null_count > 0:
            report.issues.append(
                ValidationIssue(
                    level="WARNING",
                    category="MISSING_VALUES",
                    message=f"Column '{col}' has {null_count} null / missing values.",
                )
            )

    # 3. Clean and parse row by row
    valid_rows: List[dict] = []
    supported_symbols_set: Set[str] = set()
    unsupported_symbols_set: Set[str] = set()
    supported_list = set(reg.list_supported_symbols())

    for idx, row in df.iterrows():
        # Symbol cleaning
        raw_sym = row.get("Symbol")
        sym, descr = clean_symbol(raw_sym)
        if not sym:
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="INVALID_SYMBOL",
                    message=f"Row {idx}: Missing or blank symbol.",
                    row_index=int(idx),
                )
            )
            report.dropped_rows_count += 1
            continue

        if sym in supported_list:
            supported_symbols_set.add(sym)
        else:
            unsupported_symbols_set.add(sym)

        # Date parsing
        trade_date = parse_date_explicitly(row.get("Date"))
        if trade_date is None:
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="INVALID_TRADE_DATE",
                    message=f"Row {idx}: Unparseable trade date '{row.get('Date')}'. Must match supported explicit formats.",
                    row_index=int(idx),
                    contract=sym,
                )
            )
            report.dropped_rows_count += 1
            continue

        expiry_date = parse_date_explicitly(row.get("ExpiryDate"))
        if expiry_date is None:
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="INVALID_EXPIRY_DATE",
                    message=f"Row {idx}: Unparseable expiry date '{row.get('ExpiryDate')}'. Ambiguous or invalid format rejected.",
                    row_index=int(idx),
                    contract=sym,
                )
            )
            report.dropped_rows_count += 1
            continue

        if expiry_date < trade_date:
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="EXPIRY_BEFORE_TRADE",
                    message=f"Row {idx}: Expiry date ({expiry_date}) cannot precede trade date ({trade_date}).",
                    row_index=int(idx),
                    contract=sym,
                )
            )
            report.dropped_rows_count += 1
            continue

        # Numeric price parsing
        try:
            o_val = float(row.get("Open"))
            h_val = float(row.get("High"))
            l_val = float(row.get("Low"))
            c_val = float(row.get("Close"))
        except (ValueError, TypeError):
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="INVALID_PRICE_NUMERIC",
                    message=f"Row {idx}: Non-numeric OHLC price values.",
                    row_index=int(idx),
                    contract=sym,
                )
            )
            report.dropped_rows_count += 1
            continue

        if min(o_val, h_val, l_val, c_val) <= 0:
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="NON_POSITIVE_PRICE",
                    message=f"Row {idx}: Price values must be strictly positive. Got Open={o_val}, High={h_val}, Low={l_val}, Close={c_val}.",
                    row_index=int(idx),
                    contract=sym,
                )
            )
            report.dropped_rows_count += 1
            continue

        if h_val < l_val or h_val < o_val or h_val < c_val or l_val > o_val or l_val > c_val:
            report.issues.append(
                ValidationIssue(
                    level="WARNING",
                    category="OHLC_ENVELOPE_ANOMALY",
                    message=f"Row {idx}: Inconsistent OHLC envelope (H={h_val}, L={l_val}, O={o_val}, C={c_val}).",
                    row_index=int(idx),
                    contract=sym,
                )
            )

        # Volume & Open Interest parsing
        try:
            vol_val = float(row.get("Volume", 0))
            if np.isnan(vol_val) or vol_val < 0:
                vol_val = 0.0
        except (ValueError, TypeError):
            vol_val = 0.0

        try:
            oi_val = float(row.get("OpenInterest", 0))
            if np.isnan(oi_val) or oi_val < 0:
                oi_val = 0.0
        except (ValueError, TypeError):
            oi_val = 0.0

        valid_rows.append(
            {
                "Symbol": sym,
                "ContractDescription": descr,
                "Date": trade_date,
                "ExpiryDate": expiry_date,
                "Open": o_val,
                "High": h_val,
                "Low": l_val,
                "Close": c_val,
                "Volume": int(vol_val),
                "OpenInterest": int(oi_val),
            }
        )

    clean_df = pd.DataFrame(valid_rows)

    if clean_df.empty:
        report.valid_rows_retained = 0
        report.issues.append(
            ValidationIssue(
                level="ERROR",
                category="ZERO_VALID_ROWS",
                message="All rows were dropped due to validation failures.",
            )
        )
        return clean_df, report

    # Deduplication on (Symbol, Date, ExpiryDate)
    init_clean_len = len(clean_df)
    clean_df = clean_df.drop_duplicates(subset=["Symbol", "Date", "ExpiryDate"], keep="last")
    dups = init_clean_len - len(clean_df)
    report.duplicate_rows_count = dups
    if dups > 0:
        report.issues.append(
            ValidationIssue(
                level="WARNING",
                category="DUPLICATE_RECORDS",
                message=f"Removed {dups} duplicate records matching the same (Symbol, Date, ExpiryDate).",
            )
        )

    report.valid_rows_retained = len(clean_df)
    report.supported_symbols_found = sorted(list(supported_symbols_set))
    report.unsupported_symbols_found = sorted(list(unsupported_symbols_set))

    # Dates audit
    unique_dates = sorted(clean_df["Date"].unique().tolist())
    report.unique_trade_dates = unique_dates
    report.is_single_date = len(unique_dates) == 1
    if unique_dates:
        report.date_range = (unique_dates[0], unique_dates[-1])

    # Date match verification
    if expected_date is not None:
        if expected_date in unique_dates:
            report.date_match_verified = True
        else:
            report.date_match_verified = False
            report.issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="DATE_MISMATCH",
                    message=f"Dataset dates ({report.date_range}) do not contain the requested date {expected_date}.",
                )
            )

    return clean_df, report
