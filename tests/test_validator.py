"""Tests for strict validation layer, date parsing, and quality reporting."""

import datetime
import pandas as pd
import pytest

from src.validator import (
    clean_symbol,
    parse_date_explicitly,
    validate_market_data,
    DataQualityReport,
)
from src.loader import read_market_data


def test_parse_date_explicitly():
    """Verify explicit date parsing across valid Indian market formats."""
    expected = datetime.date(2024, 10, 15)
    assert parse_date_explicitly("15-Oct-2024") == expected
    assert parse_date_explicitly("15-OCT-2024") == expected
    assert parse_date_explicitly("2024-10-15") == expected
    assert parse_date_explicitly("15-10-2024") == expected
    assert parse_date_explicitly("15/10/2024") == expected
    assert parse_date_explicitly(datetime.date(2024, 10, 15)) == expected
    assert parse_date_explicitly(pd.Timestamp("2024-10-15")) == expected


def test_parse_date_rejects_invalid():
    """Verify non-dates or invalid strings return None without guessing."""
    assert parse_date_explicitly("not-a-date") is None
    assert parse_date_explicitly("") is None
    assert parse_date_explicitly(None) is None
    assert parse_date_explicitly(12345) is None


def test_clean_symbol():
    """Verify symbol cleaning and root commodity isolation."""
    sym, desc = clean_symbol("  GOLDM  ")
    assert sym == "GOLDM"

    sym2, desc2 = clean_symbol("GOLDM 05NOV2024")
    assert sym2 == "GOLDM"

    sym3, desc3 = clean_symbol("GOLDGUINEA")
    assert sym3 == "GOLDGUINEA"

    sym4, desc4 = clean_symbol("GOLDPETAL24NOVFUT")
    assert sym4 == "GOLDPETAL"


def test_validate_sample_dataset():
    """Verify that sample MCX Bhavcopy validates cleanly without errors."""
    df_raw, _ = read_market_data("data/sample_mcx_bhavcopy.csv")
    clean_df, report = validate_market_data(df_raw, expected_date=datetime.date(2024, 10, 15))

    assert not report.has_errors
    assert report.valid_rows_retained == 13
    assert report.date_match_verified is True
    assert "GOLDM" in report.supported_symbols_found
    assert "GOLDTEN" in report.supported_symbols_found
    assert "GOLDGUINEA" in report.supported_symbols_found
    assert "GOLDPETAL" in report.supported_symbols_found


def test_validate_rejects_negative_and_zero_prices():
    """Verify that rows with prices <= 0 are rejected."""
    bad_df = pd.DataFrame(
        [
            {
                "Symbol": "GOLDM",
                "Date": "15-Oct-2024",
                "ExpiryDate": "05-Nov-2024",
                "Open": 72000,
                "High": 72500,
                "Low": 71900,
                "Close": -50.0,  # Negative price!
                "Volume": 100,
                "OpenInterest": 200,
            },
            {
                "Symbol": "GOLDTEN",
                "Date": "15-Oct-2024",
                "ExpiryDate": "05-Nov-2024",
                "Open": 72000,
                "High": 72500,
                "Low": 71900,
                "Close": 72400,
                "Volume": 100,
                "OpenInterest": 200,
            },
        ]
    )

    clean_df, report = validate_market_data(bad_df)
    assert len(clean_df) == 1
    assert report.dropped_rows_count == 1
    assert any(i.category == "NON_POSITIVE_PRICE" for i in report.issues)


def test_validate_rejects_expiry_before_trade_date():
    """Verify that expiry date preceding trade date is rejected."""
    bad_df = pd.DataFrame(
        [
            {
                "Symbol": "GOLDM",
                "Date": "15-Oct-2024",
                "ExpiryDate": "10-Oct-2024",  # Already expired 5 days ago!
                "Open": 72000,
                "High": 72500,
                "Low": 71900,
                "Close": 72100,
                "Volume": 100,
                "OpenInterest": 200,
            }
        ]
    )
    clean_df, report = validate_market_data(bad_df)
    assert len(clean_df) == 0
    assert report.dropped_rows_count == 1
    assert any(i.category == "EXPIRY_BEFORE_TRADE" for i in report.issues)


def test_validate_deduplicates_records():
    """Verify that duplicate contract records are removed with a warning."""
    dup_df = pd.DataFrame(
        [
            {
                "Symbol": "GOLDM",
                "Date": "15-Oct-2024",
                "ExpiryDate": "05-Nov-2024",
                "Open": 72000,
                "High": 72500,
                "Low": 71900,
                "Close": 72100,
                "Volume": 100,
                "OpenInterest": 200,
            },
            {
                "Symbol": "GOLDM",
                "Date": "15-Oct-2024",
                "ExpiryDate": "05-Nov-2024",
                "Open": 72000,
                "High": 72500,
                "Low": 71900,
                "Close": 72100,
                "Volume": 100,
                "OpenInterest": 200,
            },
        ]
    )
    clean_df, report = validate_market_data(dup_df)
    assert len(clean_df) == 1
    assert report.duplicate_rows_count == 1
    assert any(i.category == "DUPLICATE_RECORDS" for i in report.issues)
