"""Tests for local MCX raw repository data loading and multi-file handling."""

import datetime
from pathlib import Path
import pytest
import pandas as pd

from src.loader import load_local_raw_repository, LocalRepoReport
from src.validator import validate_market_data


def test_load_local_raw_repository_excludes_gold_by_default():
    """Verify that by default GOLD (1kg benchmark) is excluded if present, and 4 core contracts are loaded."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw directory not present")

    df, report = load_local_raw_repository("data/raw", include_gold_benchmark=False)

    assert isinstance(report, LocalRepoReport)
    assert report.files_scanned >= 4
    assert report.files_loaded >= 4
    # If 1kg GOLD benchmark file exists, ensure it is safely excluded by default
    has_gold_file = any(Path("data/raw").glob("*GOLD.csv")) or any(
        s.symbol == "GOLD" or "GOLD" in s.symbol.split(", ") for s in report.file_summaries
    )
    if has_gold_file:
        assert report.files_excluded >= 1
    assert "GOLD" not in report.contracts_found

    for expected in ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]:
        assert expected in report.contracts_found

    assert "GOLD" not in df["Symbol"].values
    assert len(df) >= 4 * 80


def test_load_local_raw_repository_with_gold_benchmark():
    """Verify that when opted in, all repository files are loaded without exclusion."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw directory not present")

    df, report = load_local_raw_repository("data/raw", include_gold_benchmark=True)

    assert report.files_loaded >= 4
    assert report.files_excluded == 0
    for expected in ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]:
        assert expected in report.contracts_found


def test_validation_on_loaded_raw_dataset():
    """Verify that loaded raw repository data passes all strict market data validations."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw directory not present")

    df, report = load_local_raw_repository("data/raw", include_gold_benchmark=False)
    clean_df, quality_rep = validate_market_data(df)

    assert not quality_rep.has_errors
    assert quality_rep.error_count == 0
    assert quality_rep.valid_rows_retained == len(df)
    assert len(quality_rep.unique_trade_dates) >= 80

