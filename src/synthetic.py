"""Isolated synthetic data generator for GoldParity UI testing and demonstration.

IMPORTANT: All datasets produced by this module are explicitly marked with
DataSource='SYNTHETIC_DEMO' and must NEVER be mixed with real exchange observations.
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.contract_specs import GLOBAL_REGISTRY, ContractRegistry, normalize_price


def generate_synthetic_bhavcopy(
    trade_date: Optional[datetime.date] = None,
    num_days: int = 1,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic MCX gold futures data strictly for UI demonstration.

    Args:
        trade_date: Reference end trade date (default: 2024-10-15)
        num_days: Number of historical days to generate (1 for single snapshot, >1 for series)
        random_seed: Deterministic seed for reproducible testing

    Returns:
        DataFrame with canonical columns + DataSource='SYNTHETIC_DEMO' flag.
    """
    rng = np.random.default_rng(random_seed)
    end_date = trade_date or datetime.date(2024, 10, 15)

    # Generate business dates
    date_list: List[datetime.date] = []
    curr = end_date
    while len(date_list) < num_days:
        if curr.weekday() < 5:  # Monday to Friday
            date_list.append(curr)
        curr -= datetime.timedelta(days=1)
    date_list = sorted(date_list)

    # Contract definitions for the synthetic dataset
    # (Symbol, Expiry Month Offset from base, Base Quote in local basis)
    # Reference gold benchmark: ₹72,000 / 10g of 995 purity (~₹7,200/g)
    # Pure 999 gold: ~₹7,228.9 / g
    contract_templates = [
        # GOLDM: quoted per 10g (995 purity)
        {"symbol": "GOLDM", "expiries": [datetime.date(2024, 11, 5), datetime.date(2024, 12, 5), datetime.date(2025, 2, 5)], "base_quote": 72150.0, "vol_range": (8000, 15000), "oi_range": (12000, 18000)},
        # GOLDTEN: quoted per 10g (999 purity)
        {"symbol": "GOLDTEN", "expiries": [datetime.date(2024, 11, 5), datetime.date(2024, 12, 5)], "base_quote": 72480.0, "vol_range": (1500, 4000), "oi_range": (3000, 6000)},
        # GOLDGUINEA: quoted per 8g (999 purity) -> 7,248 * 8 = 57,984
        {"symbol": "GOLDGUINEA", "expiries": [datetime.date(2024, 10, 31), datetime.date(2024, 11, 29), datetime.date(2024, 12, 31)], "base_quote": 58050.0, "vol_range": (2500, 6000), "oi_range": (4000, 8000)},
        # GOLDPETAL: quoted per 1g (999 purity) -> ~7,260
        {"symbol": "GOLDPETAL", "expiries": [datetime.date(2024, 10, 31), datetime.date(2024, 11, 29), datetime.date(2024, 12, 31)], "base_quote": 7265.0, "vol_range": (10000, 25000), "oi_range": (15000, 30000)},
        # GOLD: Big Gold 1kg, quoted per 10g (995 purity)
        {"symbol": "GOLD", "expiries": [datetime.date(2024, 12, 5), datetime.date(2025, 2, 5)], "base_quote": 72100.0, "vol_range": (5000, 10000), "oi_range": (10000, 15000)},
    ]

    rows = []
    # Drift factors for time-series if num_days > 1
    daily_price_walk = 0.0

    for dt in date_list:
        daily_price_walk += rng.normal(15.0, 120.0)  # Gentle random walk in gold price

        for tmpl in contract_templates:
            sym = tmpl["symbol"]
            for exp_dt in tmpl["expiries"]:
                if exp_dt <= dt:
                    continue  # Contract already expired on this date

                days_to_exp = (exp_dt - dt).days
                # Realistic contango carry of ~6% annual interest
                contango_adj = tmpl["base_quote"] * (0.06 * days_to_exp / 365.0)

                # Small basis noise between mini / guinea / petal
                noise = rng.normal(0, tmpl["base_quote"] * 0.001)

                close_price = round(tmpl["base_quote"] + daily_price_walk * (tmpl["base_quote"] / 72000.0) + contango_adj + noise, 2)
                intraday_range = tmpl["base_quote"] * rng.uniform(0.004, 0.012)

                high_price = round(close_price + rng.uniform(0.2, 0.7) * intraday_range, 2)
                low_price = round(close_price - rng.uniform(0.2, 0.7) * intraday_range, 2)
                open_price = round(rng.uniform(low_price, high_price), 2)

                # Ensure strict envelope
                high_price = max(high_price, open_price, close_price)
                low_price = min(low_price, open_price, close_price)

                vol = int(rng.integers(tmpl["vol_range"][0], tmpl["vol_range"][1]))
                oi = int(rng.integers(tmpl["oi_range"][0], tmpl["oi_range"][1]))

                rows.append(
                    {
                        "Symbol": sym,
                        "Date": dt,
                        "ExpiryDate": exp_dt,
                        "Open": open_price,
                        "High": high_price,
                        "Low": low_price,
                        "Close": close_price,
                        "Volume": vol,
                        "OpenInterest": oi,
                        "DataSource": "SYNTHETIC_DEMO",
                    }
                )

    return pd.DataFrame(rows)
