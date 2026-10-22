"""Analytical engine for MCX Gold relative value, parity normalization, and basis spreads.

Provides:
- Purity and quotation normalization to benchmark standard (e.g. ₹ per 10g of 999 purity)
- Contract notional value and turnover calculations
- Cross-contract basis spreads (₹/10g spread and percentage premium/discount)
- Term structure / curve analysis across contract expiries
- Chronological time-series spread analysis for multi-day datasets
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.contract_specs import GLOBAL_REGISTRY, ContractRegistry, ContractSpec, normalize_price


@dataclass
class MarketSummary:
    """High-level summary of active contracts on a specific date."""

    trade_date: datetime.date
    total_contracts: int
    total_volume_lots: int
    total_open_interest: int
    total_turnover_inr: float
    benchmark_symbol: str
    benchmark_normalized_price: float
    max_premium_contract: Optional[str]
    max_premium_pct: Optional[float]
    max_discount_contract: Optional[str]
    max_discount_pct: Optional[float]


def enrich_with_specifications(
    df: pd.DataFrame,
    registry: Optional[ContractRegistry] = None,
    target_quote_grams: float = 10.0,
    target_purity: float = 999.0,
) -> pd.DataFrame:
    """Enrich validated market data with contract specifications and normalized prices.

    Adds:
    - PurityFineness
    - QuotationBasisGrams
    - TradingUnitGrams
    - PricePerGram
    - NormalizedOpen, NormalizedHigh, NormalizedLow, NormalizedClose (₹ / target_quote_grams of target_purity)
    - ContractValueINR (Notional value in INR)
    - TurnoverINR (Volume * ContractValueINR)
    - DaysToExpiry ((ExpiryDate - Date).days)
    """
    if df.empty:
        return df.copy()

    reg = registry or GLOBAL_REGISTRY
    enriched = df.copy()

    purity_list = []
    quote_grams_list = []
    trade_unit_list = []
    norm_open_list = []
    norm_high_list = []
    norm_low_list = []
    norm_close_list = []
    contract_val_list = []

    for _, row in enriched.iterrows():
        sym = row["Symbol"]
        trade_date = row["Date"]
        try:
            spec = reg.get_spec(sym, as_of_date=trade_date)
            purity_list.append(spec.purity_fineness)
            quote_grams_list.append(spec.quotation_basis_grams)
            trade_unit_list.append(spec.trading_unit_grams)

            norm_open_list.append(normalize_price(row["Open"], spec, target_quote_grams, target_purity))
            norm_high_list.append(normalize_price(row["High"], spec, target_quote_grams, target_purity))
            norm_low_list.append(normalize_price(row["Low"], spec, target_quote_grams, target_purity))
            norm_close_list.append(normalize_price(row["Close"], spec, target_quote_grams, target_purity))

            contract_val_list.append(spec.calculate_contract_value(row["Close"]))
        except (KeyError, ValueError):
            purity_list.append(np.nan)
            quote_grams_list.append(np.nan)
            trade_unit_list.append(np.nan)
            norm_open_list.append(np.nan)
            norm_high_list.append(np.nan)
            norm_low_list.append(np.nan)
            norm_close_list.append(np.nan)
            contract_val_list.append(np.nan)

    enriched["PurityFineness"] = purity_list
    enriched["QuotationBasisGrams"] = quote_grams_list
    enriched["TradingUnitGrams"] = trade_unit_list
    enriched["PricePerGram"] = enriched["Close"] / enriched["QuotationBasisGrams"]

    enriched["NormalizedOpen"] = norm_open_list
    enriched["NormalizedHigh"] = norm_high_list
    enriched["NormalizedLow"] = norm_low_list
    enriched["NormalizedClose"] = norm_close_list

    enriched["ContractValueINR"] = contract_val_list
    enriched["TurnoverINR"] = enriched["Volume"] * enriched["ContractValueINR"]

    # Days to expiry
    enriched["DaysToExpiry"] = enriched.apply(
        lambda r: (r["ExpiryDate"] - r["Date"]).days if pd.notnull(r["ExpiryDate"]) and pd.notnull(r["Date"]) else np.nan,
        axis=1,
    )

    return enriched


def calculate_relative_value_matrix(
    df: pd.DataFrame,
    benchmark_symbol: str = "GOLDM",
    trade_date: Optional[datetime.date] = None,
) -> Tuple[pd.DataFrame, Optional[MarketSummary]]:
    """Compute cross-contract relative value spreads against a selected benchmark contract.

    For each contract:
    - SpreadINR: NormalizedClose - BenchmarkNormalizedClose (in ₹ per 10g of 999 purity)
    - SpreadPct: (SpreadINR / BenchmarkNormalizedClose) * 100
    - PurityArbitrageBasis: Identifies purity premium/discount relative to raw quote
    """
    if df.empty:
        return pd.DataFrame(), None

    date_filter = trade_date or df["Date"].max()
    day_df = df[df["Date"] == date_filter].copy()

    if day_df.empty:
        return pd.DataFrame(), None

    # Find benchmark row (prefer nearest expiry of benchmark symbol)
    bench_rows = day_df[day_df["Symbol"] == benchmark_symbol]
    if bench_rows.empty:
        # Fallback to first available symbol
        benchmark_symbol = day_df["Symbol"].iloc[0]
        bench_rows = day_df[day_df["Symbol"] == benchmark_symbol]

    # Use the nearest expiry of the benchmark for reference
    bench_sorted = bench_rows.sort_values(by="DaysToExpiry")
    benchmark_norm_price = bench_sorted["NormalizedClose"].iloc[0]

    # Calculate spreads
    day_df["BenchmarkSymbol"] = benchmark_symbol
    day_df["BenchmarkPrice"] = benchmark_norm_price
    day_df["SpreadINR"] = day_df["NormalizedClose"] - benchmark_norm_price
    day_df["SpreadPct"] = (day_df["SpreadINR"] / benchmark_norm_price) * 100.0

    # Summary metrics
    valid_spreads = day_df.dropna(subset=["SpreadPct"])
    if not valid_spreads.empty:
        max_prem_row = valid_spreads.loc[valid_spreads["SpreadPct"].idxmax()]
        max_disc_row = valid_spreads.loc[valid_spreads["SpreadPct"].idxmin()]
        max_prem_sym = str(max_prem_row["Symbol"])
        max_prem_pct = float(max_prem_row["SpreadPct"])
        max_disc_sym = str(max_disc_row["Symbol"])
        max_disc_pct = float(max_disc_row["SpreadPct"])
    else:
        max_prem_sym = None
        max_prem_pct = None
        max_disc_sym = None
        max_disc_pct = None

    summary = MarketSummary(
        trade_date=date_filter,
        total_contracts=len(day_df),
        total_volume_lots=int(day_df["Volume"].sum()),
        total_open_interest=int(day_df["OpenInterest"].sum()),
        total_turnover_inr=float(day_df["TurnoverINR"].sum()),
        benchmark_symbol=benchmark_symbol,
        benchmark_normalized_price=float(benchmark_norm_price),
        max_premium_contract=max_prem_sym,
        max_premium_pct=max_prem_pct,
        max_discount_contract=max_disc_sym,
        max_discount_pct=max_disc_pct,
    )

    return day_df, summary


def compute_multi_day_spread_series(
    df: pd.DataFrame,
    symbol_a: str = "GOLDGUINEA",
    symbol_b: str = "GOLDM",
) -> pd.DataFrame:
    """Compute chronological daily spread time series between two contracts (e.g. for backtesting).

    Matches the nearest active expiry for each symbol on each date.
    Calculates:
    - NormalizedClose_A, NormalizedClose_B
    - SpreadINR = NormalizedClose_A - NormalizedClose_B
    - SpreadPct = SpreadINR / NormalizedClose_B * 100
    - Rolling 20-day mean, rolling std, and Z-Score
    """
    if df.empty or len(df["Date"].unique()) < 2:
        return pd.DataFrame()

    records = []
    dates = sorted(df["Date"].unique())

    for dt in dates:
        dt_df = df[df["Date"] == dt]
        rows_a = dt_df[dt_df["Symbol"] == symbol_a].sort_values(by="DaysToExpiry")
        rows_b = dt_df[dt_df["Symbol"] == symbol_b].sort_values(by="DaysToExpiry")

        if rows_a.empty or rows_b.empty:
            continue

        item_a = rows_a.iloc[0]
        item_b = rows_b.iloc[0]

        price_a = item_a["NormalizedClose"]
        price_b = item_b["NormalizedClose"]
        spread_inr = price_a - price_b
        spread_pct = (spread_inr / price_b) * 100.0

        records.append(
            {
                "Date": dt,
                f"{symbol_a}_Expiry": item_a["ExpiryDate"],
                f"{symbol_b}_Expiry": item_b["ExpiryDate"],
                f"{symbol_a}_RawClose": item_a["Close"],
                f"{symbol_b}_RawClose": item_b["Close"],
                f"{symbol_a}_NormClose": price_a,
                f"{symbol_b}_NormClose": price_b,
                "SpreadINR": spread_inr,
                "SpreadPct": spread_pct,
            }
        )

    spread_df = pd.DataFrame(records)
    if spread_df.empty:
        return spread_df

    # Calculate rolling statistics
    spread_df["Spread_Mean_20d"] = spread_df["SpreadINR"].rolling(window=20, min_periods=3).mean()
    spread_df["Spread_Std_20d"] = spread_df["SpreadINR"].rolling(window=20, min_periods=3).std()
    spread_df["Spread_ZScore"] = (spread_df["SpreadINR"] - spread_df["Spread_Mean_20d"]) / spread_df["Spread_Std_20d"]

    return spread_df


@dataclass
class BacktestResult:
    """Quantitative performance statistics for chronological spread evaluation."""

    total_days: int
    total_trades: int
    winning_trades: int
    win_rate_pct: float
    cumulative_return_pct: float
    max_drawdown_pct: float
    spread_volatility_inr: float
    annualized_sharpe: float
    friction_cost_pct: float
    disclaimer: str


def simulate_spread_mean_reversion(
    spread_df: pd.DataFrame,
    z_entry_threshold: float = 1.5,
    friction_bps: float = 3.0,
) -> Tuple[pd.DataFrame, Optional[BacktestResult]]:
    """Simulate a look-ahead bias-free mean-reversion strategy on the parity spread.

    Rules:
    - Signal is derived strictly from lagged Z-Score Z_{t-1} to prevent look-ahead bias.
    - If Z_{t-1} >= z_entry_threshold: Enter Short Spread (Short Leg A, Long Leg B).
    - If Z_{t-1} <= -z_entry_threshold: Enter Long Spread (Long Leg A, Short Leg B).
    - Exit when Z crosses 0 (spread returns to mean) or reverses.
    - Frictions: Deducts round-turn friction_bps whenever position changes.
    """
    if spread_df.empty or "Spread_ZScore" not in spread_df.columns or len(spread_df) < 5:
        return spread_df.copy(), None

    sim_df = spread_df.copy().sort_values(by="Date").reset_index(drop=True)

    # 1. Generate position signal with 1-day lag to prevent look-ahead bias
    positions = []
    current_pos = 0  # -1 for Short Spread, 0 for Flat, +1 for Long Spread

    for i in range(len(sim_df)):
        if i == 0:
            positions.append(0)
            continue

        prev_z = sim_df.loc[i - 1, "Spread_ZScore"]
        if pd.isna(prev_z):
            positions.append(0)
            continue

        if current_pos == 0:
            if prev_z >= z_entry_threshold:
                current_pos = -1  # Short spread
            elif prev_z <= -z_entry_threshold:
                current_pos = 1  # Long spread
        elif current_pos == 1:
            if prev_z >= 0:  # Exited when reverting back to or above mean
                current_pos = 0
            elif prev_z >= z_entry_threshold:
                current_pos = -1
        elif current_pos == -1:
            if prev_z <= 0:  # Exited when reverting back to or below mean
                current_pos = 0
            elif prev_z <= -z_entry_threshold:
                current_pos = 1

        positions.append(current_pos)

    sim_df["StrategyPosition"] = positions

    # 2. Daily price changes and spread return
    sim_df["DailySpreadChange"] = sim_df["SpreadINR"].diff().fillna(0.0)
    norm_cols = [c for c in sim_df.columns if c.endswith("_NormClose")]
    leg_b_col = norm_cols[-1] if norm_cols else "SpreadINR"

    denom = sim_df[leg_b_col].replace(0, np.nan)
    sim_df["GrossDailyReturn"] = (
        sim_df["StrategyPosition"].shift(1).fillna(0) * (sim_df["DailySpreadChange"] / denom)
    ).fillna(0.0)

    # 3. Friction deductions on position changes
    pos_change = sim_df["StrategyPosition"].diff().abs().fillna(0)
    friction_frac = friction_bps / 10000.0
    sim_df["FrictionCost"] = pos_change * friction_frac
    sim_df["NetDailyReturn"] = sim_df["GrossDailyReturn"] - sim_df["FrictionCost"]

    # 4. Cumulative equity curve and drawdowns
    sim_df["CumulativeReturn"] = (1.0 + sim_df["NetDailyReturn"]).cumprod() - 1.0
    sim_df["CumulativeReturnPct"] = sim_df["CumulativeReturn"] * 100.0

    running_max = (1.0 + sim_df["CumulativeReturn"]).cummax()
    sim_df["DrawdownPct"] = ((1.0 + sim_df["CumulativeReturn"]) / running_max - 1.0) * 100.0

    # Trade statistics
    trade_starts = (sim_df["StrategyPosition"] != 0) & (sim_df["StrategyPosition"].shift(1) == 0)
    total_trades = int(trade_starts.sum())

    active_days = sim_df[sim_df["StrategyPosition"] != 0]
    winning_days = int((active_days["NetDailyReturn"] > 0).sum())
    win_rate = (winning_days / len(active_days) * 100.0) if len(active_days) > 0 else 0.0

    cum_ret = float(sim_df["CumulativeReturnPct"].iloc[-1])
    max_dd = float(sim_df["DrawdownPct"].min())
    spread_vol = float(sim_df["SpreadINR"].std())

    daily_mean = sim_df["NetDailyReturn"].mean()
    daily_std = sim_df["NetDailyReturn"].std()
    annualized_sharpe = (
        float((daily_mean / daily_std * np.sqrt(252))) if daily_std > 1e-8 else 0.0
    )

    total_friction = float(sim_df["FrictionCost"].sum() * 100.0)

    result = BacktestResult(
        total_days=len(sim_df),
        total_trades=total_trades,
        winning_trades=winning_days,
        win_rate_pct=round(win_rate, 1),
        cumulative_return_pct=round(cum_ret, 2),
        max_drawdown_pct=round(max_dd, 2),
        spread_volatility_inr=round(spread_vol, 2),
        annualized_sharpe=round(annualized_sharpe, 2),
        friction_cost_pct=round(total_friction, 3),
        disclaimer="Research evaluation only. Assumes zero bid-ask impact, perfect liquidity, and constant margins. Past spread behavior is not predictive of future convergence.",
    )

    return sim_df, result

