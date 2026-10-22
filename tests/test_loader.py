"""Tests for market data loader and column alias mapping."""

import io
from pathlib import Path
import pandas as pd
import pytest

from src.loader import read_market_data, map_columns, CANONICAL_COLUMNS


def test_map_columns_standard():
    """Verify standard canonical column names map directly to themselves."""
    raw_cols = ["Symbol", "Date", "ExpiryDate", "Open", "High", "Low", "Close", "Volume", "OpenInterest"]
    mapped, unmapped, missing = map_columns(raw_cols)
    assert len(missing) == 0
    assert len(unmapped) == 0
    assert mapped["Symbol"] == "Symbol"
    assert mapped["Close"] == "Close"


def test_map_columns_mcx_aliases():
    """Verify typical exchange variations map to canonical columns."""
    mcx_raw = [
        "SYMBOL",
        "TRADE_DATE",
        "EXPIRY_DT",
        "OPEN_PRICE",
        "HIGH_PRICE",
        "LOW_PRICE",
        "CLOSE_PRICE",
        "NO_OF_CONTRACTS",
        "OPEN_INTEREST",
        "EXTRA_FIELD",
    ]
    mapped, unmapped, missing = map_columns(mcx_raw)
    assert len(missing) == 0
    assert "EXTRA_FIELD" in unmapped
    assert mapped["Symbol"] == "SYMBOL"
    assert mapped["Date"] == "TRADE_DATE"
    assert mapped["ExpiryDate"] == "EXPIRY_DT"
    assert mapped["Volume"] == "NO_OF_CONTRACTS"


def test_read_sample_bhavcopy_file():
    """Verify loading real sample file from data/ directory."""
    sample_path = Path("data/sample_mcx_bhavcopy.csv")
    assert sample_path.exists()

    df, report = read_market_data(sample_path)
    assert report.is_valid_schema
    assert report.raw_row_count == 13
    assert len(report.missing_required_columns) == 0
    assert "Symbol" in df.columns
    assert "Close" in df.columns
    assert "Date" in df.columns
    assert "ExpiryDate" in df.columns


def test_read_bytes_io_stream():
    """Verify loading in-memory buffer (simulating Streamlit file uploader)."""
    csv_text = (
        "Symbol,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,15-Oct-2024,05-Nov-2024,72000,72500,71900,72300,5000,8000\n"
    )
    buffer = io.BytesIO(csv_text.encode("utf-8"))
    df, report = read_market_data(buffer, filename="uploaded.csv")
    assert report.raw_row_count == 1
    assert report.is_valid_schema
    assert df["Symbol"].iloc[0] == "GOLDM"
    assert df["Close"].iloc[0] == 72300


def test_missing_required_columns():
    """Verify detection of missing required canonical columns."""
    csv_text = "Symbol,Date,Close\nGOLDM,2024-10-15,72000\n"
    buffer = io.BytesIO(csv_text.encode("utf-8"))
    _, report = read_market_data(buffer, filename="incomplete.csv")
    assert not report.is_valid_schema
    assert "ExpiryDate" in report.missing_required_columns
    assert "Open" in report.missing_required_columns
    assert "Volume" in report.missing_required_columns
