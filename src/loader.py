"""Market data ingestion layer for MCX Bhavcopy datasets.

Supports CSV, XLS, and XLSX file formats with intelligent column alias mapping,
whitespace trimming, and transparent reporting of mapped vs unmapped columns.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Set, Tuple, Union

import pandas as pd


# Canonical column names required for GoldParity analytics
CANONICAL_COLUMNS: List[str] = [
    "Symbol",
    "Date",
    "ExpiryDate",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "OpenInterest",
]

# Alias map for standard variations found in MCX / exchange Bhavcopies
COLUMN_ALIASES: Dict[str, List[str]] = {
    "Symbol": [
        "symbol",
        "commodity",
        "contract",
        "instrument",
        "underlying",
        "symbol_name",
        "contract_descr",
        "contract_name",
        "scrip",
    ],
    "Date": [
        "date",
        "trade_date",
        "tradedate",
        "timestamp",
        "traded_date",
        "mkt_date",
        "dt",
        "date_of_trade",
        "business_date",
    ],
    "ExpiryDate": [
        "expirydate",
        "expiry_date",
        "expiry_dt",
        "expiry",
        "exp_date",
        "maturity_date",
        "contract_expiry",
        "exp_dt",
    ],
    "Open": [
        "open",
        "open_price",
        "openprice",
        "open_rate",
        "first_price",
    ],
    "High": [
        "high",
        "high_price",
        "highprice",
        "high_rate",
        "max_price",
    ],
    "Low": [
        "low",
        "low_price",
        "lowprice",
        "low_rate",
        "min_price",
    ],
    "Close": [
        "close",
        "close_price",
        "closeprice",
        "settlement_price",
        "settle_price",
        "closing_price",
        "last_price",
        "ltp",
    ],
    "Volume": [
        "volume",
        "vol",
        "volume_lots",
        "volumelots",
        "volume_in_lots",
        "traded_qty",
        "traded_volume",
        "contracts_traded",
        "no_of_contracts",
        "qty",
        "total_qty",
    ],
    "OpenInterest": [
        "openinterest",
        "open_interest",
        "open_interest_lots",
        "openinterestlots",
        "oi",
        "open_int",
        "no_of_open_contracts",
        "open_interest_contracts",
    ],
}


@dataclass
class IngestionReport:
    """Diagnostic report generated during file ingestion and column mapping."""

    filename: str
    file_type: str
    raw_row_count: int
    raw_columns: List[str]
    mapped_columns: Dict[str, str]  # canonical_name -> raw_column_name
    unmapped_columns: List[str]
    missing_required_columns: List[str]
    is_valid_schema: bool


def _clean_header(name: str) -> str:
    """Normalize raw header name for fuzzy matching (alphanumeric characters only)."""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())



def map_columns(raw_columns: List[str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Map raw columns to canonical column names using alias definitions.

    Returns:
        (mapped_columns, unmapped_columns, missing_canonical_columns)
    """
    cleaned_to_raw = {_clean_header(c): str(c).strip() for c in raw_columns}
    mapped: Dict[str, str] = {}
    used_raws: Set[str] = set()

    for canonical, aliases in COLUMN_ALIASES.items():
        # Check canonical match first
        canonical_clean = _clean_header(canonical)
        if canonical_clean in cleaned_to_raw:
            raw_col = cleaned_to_raw[canonical_clean]
            mapped[canonical] = raw_col
            used_raws.add(raw_col)
            continue

        # Check aliases in priority order
        for alias in aliases:
            alias_clean = _clean_header(alias)
            if alias_clean in cleaned_to_raw and cleaned_to_raw[alias_clean] not in used_raws:
                raw_col = cleaned_to_raw[alias_clean]
                mapped[canonical] = raw_col
                used_raws.add(raw_col)
                break

    unmapped = [str(c).strip() for c in raw_columns if str(c).strip() not in used_raws]
    missing = [c for c in CANONICAL_COLUMNS if c not in mapped]
    return mapped, unmapped, missing


def read_market_data(
    source: Union[str, Path, BinaryIO, io.BytesIO],
    filename: Optional[str] = None,
) -> Tuple[pd.DataFrame, IngestionReport]:
    """Ingest CSV or Excel file, map columns to canonical names, and trim string data.

    Args:
        source: File path, Path object, or file-like binary stream (e.g. Streamlit UploadedFile)
        filename: Optional explicit filename (useful if passing a BytesIO)

    Returns:
        (DataFrame with canonical column names, IngestionReport)
    """
    detected_name = filename or (str(source) if isinstance(source, (str, Path)) else "uploaded_file")
    ext = Path(detected_name).suffix.lower()

    if ext in [".xlsx", ".xls"]:
        df_raw = pd.read_excel(source)
        file_type = "Excel"
    else:
        # Default to CSV with comma or tab separation
        try:
            df_raw = pd.read_csv(source)
            file_type = "CSV"
        except Exception:
            # Fallback attempt if source was seekable
            if hasattr(source, "seek"):
                source.seek(0)
            df_raw = pd.read_csv(source, sep=";")
            file_type = "CSV (semicolon)"

    raw_columns = [str(c).strip() for c in df_raw.columns]
    mapped_cols, unmapped_cols, missing_cols = map_columns(raw_columns)

    # Invert mapped_cols for rename: {raw_col: canonical}
    rename_dict = {raw_col: canon for canon, raw_col in mapped_cols.items()}
    df_renamed = df_raw.rename(columns=rename_dict)

    # Trim leading/trailing whitespace on string/object columns
    for col in df_renamed.select_dtypes(include=["object"]).columns:
        df_renamed[col] = df_renamed[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    # Retain all mapped columns; also keep unmapped columns for inspection
    report = IngestionReport(
        filename=Path(detected_name).name,
        file_type=file_type,
        raw_row_count=len(df_raw),
        raw_columns=raw_columns,
        mapped_columns=mapped_cols,
        unmapped_columns=unmapped_cols,
        missing_required_columns=missing_cols,
        is_valid_schema=len(missing_cols) == 0,
    )

    return df_renamed, report


@dataclass
class LocalFileSummary:
    """Diagnostic summary of an individual file in the local raw repository."""

    filename: str
    file_path: str
    symbol: str
    row_count: int
    date_min: Optional[str]
    date_max: Optional[str]
    expiry_dates: List[str]
    status: str  # e.g., 'Loaded', 'Excluded (1kg Benchmark)', 'Error', 'Empty'


@dataclass
class LocalRepoReport:
    """Aggregated discovery and audit report across all files in data/raw/."""

    raw_dir: str
    files_scanned: int = 0
    files_loaded: int = 0
    files_excluded: int = 0
    total_rows: int = 0
    contracts_found: List[str] = field(default_factory=list)
    date_range: Tuple[Optional[str], Optional[str]] = (None, None)
    file_summaries: List[LocalFileSummary] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def load_local_raw_repository(
    raw_dir: Union[str, Path] = "data/raw",
    include_gold_benchmark: bool = False,
) -> Tuple[pd.DataFrame, LocalRepoReport]:
    """Scan and ingest all MCX commodity datasets located in the local repository.

    Features:
    - Scans directory for CSV and Excel files.
    - Groups files by contract symbol (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL).
    - Supports multiple files per contract (merging and deduplicating).
    - Excludes the standard 1kg 'GOLD' benchmark contract by default, isolating
      the retail/mini contracts unless explicitly requested.
    - Never fabricates or silently substitutes missing data.
    - Generates a full diagnostic LocalRepoReport.

    Args:
        raw_dir: Path to directory containing raw MCX Bhavcopy/historical files.
        include_gold_benchmark: If True, include 1kg GOLD contract records.

    Returns:
        (combined_df, LocalRepoReport)
    """
    from src.validator import clean_symbol, parse_date_explicitly

    raw_path = Path(raw_dir)
    report = LocalRepoReport(raw_dir=str(raw_path))

    if not raw_path.exists() or not raw_path.is_dir():
        report.errors.append(f"Directory '{raw_path}' does not exist or is not a directory.")
        return pd.DataFrame(columns=CANONICAL_COLUMNS), report

    candidate_files = sorted(
        [
            f
            for f in raw_path.iterdir()
            if f.is_file() and f.suffix.lower() in [".csv", ".xlsx", ".xls"]
        ]
    )

    if not candidate_files:
        report.errors.append(f"No CSV or Excel files found in '{raw_path}'.")
        return pd.DataFrame(columns=CANONICAL_COLUMNS), report

    dfs_to_concat: List[pd.DataFrame] = []

    for file_path in candidate_files:
        report.files_scanned += 1
        try:
            df, _ = read_market_data(file_path)
            if df.empty:
                report.file_summaries.append(
                    LocalFileSummary(
                        filename=file_path.name,
                        file_path=str(file_path),
                        symbol="EMPTY",
                        row_count=0,
                        date_min=None,
                        date_max=None,
                        expiry_dates=[],
                        status="Empty File",
                    )
                )
                continue

            # Determine contract symbol(s) in this file
            if "Symbol" in df.columns:
                raw_syms = df["Symbol"].dropna().astype(str).tolist()
                clean_syms = [clean_symbol(s)[0] for s in raw_syms]
                unique_syms = sorted(list(set(clean_syms)))
            else:
                unique_syms = ["UNKNOWN"]

            sym_label = ", ".join(unique_syms) if unique_syms else "UNKNOWN"

            # Parse dates for summary reporting
            d_min_str: Optional[str] = None
            d_max_str: Optional[str] = None
            if "Date" in df.columns:
                parsed_dates = [parse_date_explicitly(d) for d in df["Date"].dropna()]
                valid_dates = [d for d in parsed_dates if d is not None]
                if valid_dates:
                    d_min_str = min(valid_dates).strftime("%d-%b-%Y")
                    d_max_str = max(valid_dates).strftime("%d-%b-%Y")

            exp_strs = (
                sorted([str(x).strip() for x in df["ExpiryDate"].dropna().unique().tolist()])
                if "ExpiryDate" in df.columns
                else []
            )

            # Check for GOLD benchmark exclusion
            is_gold_benchmark = unique_syms == ["GOLD"] or (
                len(unique_syms) > 0 and all(s == "GOLD" for s in unique_syms)
            )

            if is_gold_benchmark and not include_gold_benchmark:
                report.files_excluded += 1
                report.file_summaries.append(
                    LocalFileSummary(
                        filename=file_path.name,
                        file_path=str(file_path),
                        symbol=sym_label,
                        row_count=len(df),
                        date_min=d_min_str,
                        date_max=d_max_str,
                        expiry_dates=exp_strs,
                        status="Excluded (1kg Benchmark)",
                    )
                )
                continue

            # If file has mixed symbols including GOLD, filter out GOLD if not requested
            if not include_gold_benchmark and "GOLD" in unique_syms:
                mask = df["Symbol"].map(lambda x: clean_symbol(x)[0] != "GOLD")
                df = df[mask].copy()
                unique_syms = [s for s in unique_syms if s != "GOLD"]
                sym_label = ", ".join(unique_syms)

            report.files_loaded += 1
            report.file_summaries.append(
                LocalFileSummary(
                    filename=file_path.name,
                    file_path=str(file_path),
                    symbol=sym_label,
                    row_count=len(df),
                    date_min=d_min_str,
                    date_max=d_max_str,
                    expiry_dates=exp_strs,
                    status="Loaded",
                )
            )
            dfs_to_concat.append(df)

        except Exception as exc:
            report.errors.append(f"Error parsing '{file_path.name}': {exc}")
            report.file_summaries.append(
                LocalFileSummary(
                    filename=file_path.name,
                    file_path=str(file_path),
                    symbol="ERROR",
                    row_count=0,
                    date_min=None,
                    date_max=None,
                    expiry_dates=[],
                    status=f"Error: {exc}",
                )
            )

    if dfs_to_concat:
        combined_df = pd.concat(dfs_to_concat, ignore_index=True)
        # Deduplicate multiple files or overlapping dates for the same contract
        subset_cols = [c for c in ["Symbol", "Date", "ExpiryDate"] if c in combined_df.columns]
        if subset_cols:
            combined_df = combined_df.drop_duplicates(subset=subset_cols, keep="last")

        report.total_rows = len(combined_df)

        loaded_symbols: Set[str] = set()
        loaded_d_mins: List[str] = []
        loaded_d_maxs: List[str] = []

        for summ in report.file_summaries:
            if summ.status == "Loaded":
                for s in summ.symbol.split(", "):
                    if s and s != "UNKNOWN":
                        loaded_symbols.add(s)
                if summ.date_min:
                    loaded_d_mins.append(summ.date_min)
                if summ.date_max:
                    loaded_d_maxs.append(summ.date_max)

        report.contracts_found = sorted(list(loaded_symbols))
        if loaded_d_mins and loaded_d_maxs:
            report.date_range = (min(loaded_d_mins), max(loaded_d_maxs))
    else:
        combined_df = pd.DataFrame(columns=CANONICAL_COLUMNS)

    return combined_df, report

