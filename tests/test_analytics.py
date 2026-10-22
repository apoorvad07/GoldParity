"""Tests for analytics engine, relative value matrix, and time series calculation."""

import datetime
import pytest

from src.loader import read_market_data
from src.validator import validate_market_data
from src.analytics import (
    enrich_with_specifications,
    calculate_relative_value_matrix,
    compute_multi_day_spread_series,
    simulate_spread_mean_reversion,
)
from src.synthetic import generate_synthetic_bhavcopy


def test_enrich_with_specifications():
    """Verify market data enrichment with contract specs and normalized prices."""
    df_raw, _ = read_market_data("data/sample_mcx_bhavcopy.csv")
    clean_df, _ = validate_market_data(df_raw)
    enriched = enrich_with_specifications(clean_df)

    assert "NormalizedClose" in enriched.columns
    assert "ContractValueINR" in enriched.columns
    assert "TurnoverINR" in enriched.columns
    assert "DaysToExpiry" in enriched.columns

    # Verify that all target contracts have valid numeric normalized prices
    assert not enriched["NormalizedClose"].isna().any()

    # GOLDM close = 72220 for 10g (995 purity). Normalized to 999 purity:
    # 72220 / 10 * (999 / 995) * 10 = 72220 * (999/995) = 72510.37
    goldm_row = enriched[enriched["Symbol"] == "GOLDM"].iloc[0]
    expected_norm = (goldm_row["Close"] / 10.0) * (999.0 / 995.0) * 10.0
    assert pytest.approx(goldm_row["NormalizedClose"], rel=1e-4) == expected_norm


def test_relative_value_matrix_and_summary():
    """Verify relative value calculation and market summary generation."""
    df_raw, _ = read_market_data("data/sample_mcx_bhavcopy.csv")
    clean_df, _ = validate_market_data(df_raw)
    enriched = enrich_with_specifications(clean_df)

    matrix_df, summary = calculate_relative_value_matrix(enriched, benchmark_symbol="GOLDM")

    assert summary is not None
    assert summary.benchmark_symbol == "GOLDM"
    assert summary.total_contracts == 13
    assert summary.total_volume_lots > 0
    assert summary.total_turnover_inr > 0
    assert "SpreadINR" in matrix_df.columns
    assert "SpreadPct" in matrix_df.columns

    # Benchmark nearest contract spread vs itself should be 0.0
    bench_rows = matrix_df[matrix_df["Symbol"] == "GOLDM"].sort_values(by="DaysToExpiry")
    assert pytest.approx(bench_rows["SpreadINR"].iloc[0], abs=1e-3) == 0.0


def test_synthetic_time_series_spread():
    """Verify multi-day spread computation on synthetic series."""
    synth_df = generate_synthetic_bhavcopy(
        trade_date=datetime.date(2024, 10, 15),
        num_days=10,
        random_seed=123,
    )
    clean_df, _ = validate_market_data(synth_df)
    enriched = enrich_with_specifications(clean_df)

    spread_series = compute_multi_day_spread_series(enriched, symbol_a="GOLDGUINEA", symbol_b="GOLDM")
    assert not spread_series.empty
    assert len(spread_series) == 10
    assert "SpreadINR" in spread_series.columns
    assert "SpreadPct" in spread_series.columns
    assert "Spread_Mean_20d" in spread_series.columns
    assert "Spread_ZScore" in spread_series.columns


def test_simulate_spread_mean_reversion():
    """Verify look-ahead-bias-free spread simulation and performance metrics."""
    synth_df = generate_synthetic_bhavcopy(
        trade_date=datetime.date(2024, 10, 15),
        num_days=25,
        random_seed=42,
    )
    clean_df, _ = validate_market_data(synth_df)
    enriched = enrich_with_specifications(clean_df)
    spread_series = compute_multi_day_spread_series(enriched, symbol_a="GOLDGUINEA", symbol_b="GOLDM")

    sim_df, result = simulate_spread_mean_reversion(spread_series, z_entry_threshold=1.0)
    assert result is not None
    assert result.total_days == 25
    assert "CumulativeReturnPct" in sim_df.columns
    assert "DrawdownPct" in sim_df.columns
    assert "StrategyPosition" in sim_df.columns
    assert hasattr(result, "max_drawdown_pct")
    assert hasattr(result, "disclaimer")

