"""Configurable and version-sensitive contract specifications for MCX Gold futures.

Supports:
- GOLDM: Gold Mini (100g trading unit, quote per 10g, 995 fineness)
- GOLDTEN: Gold 10g (10g trading unit, quote per 10g, 999 fineness)
- GOLDGUINEA: Gold Guinea (8g trading unit, quote per 8g, 999 fineness)
- GOLDPETAL: Gold Petal (1g trading unit, quote per 1g, 999 fineness)
- GOLD: Big Gold benchmark (1000g trading unit, quote per 10g, 995 fineness)

Provides methods for purity adjustments, quotation basis conversions,
and version-sensitive configuration retrieval.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ContractSpec:
    """Specification for an MCX commodity futures contract."""

    symbol: str
    display_name: str
    trading_unit_grams: float  # Physical delivery/lot weight in grams
    quotation_basis_grams: float  # Grams corresponding to quoted price
    purity_fineness: float  # Purity in parts per 1000 (e.g. 995.0 or 999.0)
    tick_size: float  # Minimum price tick in INR
    lot_size: int  # Standard trading lot multiplier
    version: str  # Specification version string
    effective_from: datetime.date  # Start date of specification validity
    effective_to: Optional[datetime.date] = None  # None = currently active
    specification_source: str = "MCX Contract Specification Circular"
    notes: str = ""

    def is_active_on(self, query_date: datetime.date) -> bool:
        """Check if this specification version was in effect on the given date."""
        if query_date < self.effective_from:
            return False
        if self.effective_to is not None and query_date > self.effective_to:
            return False
        return True

    def calculate_contract_value(self, price: float) -> float:
        """Calculate total notional contract value in INR from the quoted price.

        Formula: (Quoted Price / Quotation Basis in Grams) * Trading Unit in Grams
        """
        if self.quotation_basis_grams <= 0:
            raise ValueError(f"Invalid quotation basis: {self.quotation_basis_grams}")
        return (price / self.quotation_basis_grams) * self.trading_unit_grams

    def to_dict(self) -> dict:
        """Export specification parameters as a readable dictionary."""
        return {
            "Symbol": self.symbol,
            "Name": self.display_name,
            "Trading Unit (g)": self.trading_unit_grams,
            "Quotation Basis (g)": self.quotation_basis_grams,
            "Purity (Fineness)": self.purity_fineness,
            "Tick Size (₹)": self.tick_size,
            "Lot Size": self.lot_size,
            "Version": self.version,
            "Effective From": self.effective_from.isoformat(),
            "Effective To": self.effective_to.isoformat() if self.effective_to else "Current",
            "Source": self.specification_source,
            "Notes": self.notes,
        }


# Default historical specifications registry
DEFAULT_SPECS: List[ContractSpec] = [
    # GOLDM (Gold Mini): 100g contract, quoted per 10g, 995 fineness
    ContractSpec(
        symbol="GOLDM",
        display_name="Gold Mini",
        trading_unit_grams=100.0,
        quotation_basis_grams=10.0,
        purity_fineness=995.0,
        tick_size=1.0,
        lot_size=1,
        version="v1.0-standard",
        effective_from=datetime.date(2010, 1, 1),
        effective_to=None,
        specification_source="MCX Circular MCX/TRD/2020/GOLDM",
        notes="Delivery unit 100g bar. Quote in Rs per 10g. Purity 995.",
    ),
    # GOLDTEN: Gold 10g, quoted per 10g, 999 fineness
    ContractSpec(
        symbol="GOLDTEN",
        display_name="Gold 10 Grams",
        trading_unit_grams=10.0,
        quotation_basis_grams=10.0,
        purity_fineness=999.0,
        tick_size=1.0,
        lot_size=1,
        version="v1.0-standard",
        effective_from=datetime.date(2019, 1, 1),
        effective_to=None,
        specification_source="MCX Circular MCX/TRD/2019/GOLDTEN",
        notes="Trading unit 10g. Quoted in Rs per 10g. High-purity 999.",
    ),
    # GOLDGUINEA: Gold Guinea (8g), quoted per 8g, 999 fineness
    ContractSpec(
        symbol="GOLDGUINEA",
        display_name="Gold Guinea",
        trading_unit_grams=8.0,
        quotation_basis_grams=8.0,
        purity_fineness=999.0,
        tick_size=1.0,
        lot_size=1,
        version="v1.0-standard",
        effective_from=datetime.date(2010, 1, 1),
        effective_to=None,
        specification_source="MCX Circular MCX/TRD/2012/GOLDGUINEA",
        notes="Trading unit 1 Guinea (8g). Quoted per 1 Guinea (8g). Purity 999.",
    ),
    # GOLDPETAL: Gold Petal (1g), quoted per 1g, 999 fineness
    ContractSpec(
        symbol="GOLDPETAL",
        display_name="Gold Petal",
        trading_unit_grams=1.0,
        quotation_basis_grams=1.0,
        purity_fineness=999.0,
        tick_size=1.0,
        lot_size=1,
        version="v1.0-standard",
        effective_from=datetime.date(2011, 1, 1),
        effective_to=None,
        specification_source="MCX Circular MCX/TRD/2011/GOLDPETAL",
        notes="Trading unit 1g coin/ingot. Quoted per 1g. Purity 999.",
    ),
    # GOLD (Standard Big Gold Benchmark): 1kg, quoted per 10g, 995 fineness
    ContractSpec(
        symbol="GOLD",
        display_name="Gold 1kg",
        trading_unit_grams=1000.0,
        quotation_basis_grams=10.0,
        purity_fineness=995.0,
        tick_size=1.0,
        lot_size=1,
        version="v1.0-standard",
        effective_from=datetime.date(2003, 1, 1),
        effective_to=None,
        specification_source="MCX Circular MCX/TRD/2003/GOLD",
        notes="Benchmark 1kg gold futures. Quoted in Rs per 10g. Purity 995.",
    ),
]


class ContractRegistry:
    """Version-sensitive registry for commodity contract specifications."""

    def __init__(self, specs: Optional[List[ContractSpec]] = None) -> None:
        self._specs_by_symbol: Dict[str, List[ContractSpec]] = {}
        specs_to_load = specs if specs is not None else DEFAULT_SPECS
        for s in specs_to_load:
            self.register(s)

    def register(self, spec: ContractSpec) -> None:
        """Register a new or updated contract specification version."""
        sym = spec.symbol.upper().strip()
        if sym not in self._specs_by_symbol:
            self._specs_by_symbol[sym] = []
        self._specs_by_symbol[sym].append(spec)

    def get_spec(self, symbol: str, as_of_date: Optional[datetime.date] = None) -> ContractSpec:
        """Retrieve the valid specification for a symbol as of a specific date.

        If as_of_date is None, returns the latest active specification.
        Raises KeyError if symbol is not found, or ValueError if no valid version on date.
        """
        sym = symbol.upper().strip()
        if sym not in self._specs_by_symbol:
            raise KeyError(
                f"Unsupported contract symbol: '{symbol}'. "
                f"Supported symbols: {self.list_supported_symbols()}"
            )

        candidates = self._specs_by_symbol[sym]
        if as_of_date is None:
            # Prefer active spec (effective_to is None) or latest effective_from
            active = [c for c in candidates if c.effective_to is None]
            if active:
                return active[-1]
            return max(candidates, key=lambda c: c.effective_from)

        valid = [c for c in candidates if c.is_active_on(as_of_date)]
        if not valid:
            raise ValueError(
                f"No specification for {sym} found active on date {as_of_date}."
            )
        return valid[-1]

    def list_supported_symbols(self) -> List[str]:
        """List all registered contract symbols."""
        return sorted(list(self._specs_by_symbol.keys()))

    def get_all_active_specs(self, as_of_date: Optional[datetime.date] = None) -> Dict[str, ContractSpec]:
        """Get the active spec for each supported symbol."""
        result = {}
        for sym in self.list_supported_symbols():
            try:
                result[sym] = self.get_spec(sym, as_of_date=as_of_date)
            except ValueError:
                pass
        return result


# Global default registry instance
GLOBAL_REGISTRY = ContractRegistry()


def normalize_price(
    raw_price: float,
    spec: ContractSpec,
    target_quote_grams: float = 10.0,
    target_purity: float = 999.0,
) -> float:
    """Normalize a raw contract quote to a standard reference basis.

    Standard benchmark default: INR per 10 grams of 999 purity.

    Formula:
    1. Raw Price per Gram = raw_price / spec.quotation_basis_grams
    2. Pure Gold Price per Gram (100% fine) = Raw Price per Gram * (1000.0 / spec.purity_fineness)
    3. Target Purity Price per Gram = Pure Gold Price per Gram * (target_purity / 1000.0)
       => Equivalently: Raw Price per Gram * (target_purity / spec.purity_fineness)
    4. Target Basis Price = Target Purity Price per Gram * target_quote_grams

    Combined:
        Normalized = (raw_price / spec.quotation_basis_grams)
                   * (target_purity / spec.purity_fineness)
                   * target_quote_grams
    """
    if raw_price <= 0:
        raise ValueError(f"Price must be strictly positive, got {raw_price}")
    if spec.quotation_basis_grams <= 0 or spec.purity_fineness <= 0:
        raise ValueError("Specification must have positive quotation basis and purity")

    price_per_gram = raw_price / spec.quotation_basis_grams
    purity_adjusted_per_gram = price_per_gram * (target_purity / spec.purity_fineness)
    return purity_adjusted_per_gram * target_quote_grams


def denormalize_price(
    normalized_price: float,
    spec: ContractSpec,
    target_quote_grams: float = 10.0,
    target_purity: float = 999.0,
) -> float:
    """Reverse normalize: convert standard reference basis price back to raw quoted price."""
    if normalized_price <= 0:
        raise ValueError(f"Normalized price must be positive, got {normalized_price}")
    price_per_gram = normalized_price / target_quote_grams
    contract_purity_per_gram = price_per_gram * (spec.purity_fineness / target_purity)
    return contract_purity_per_gram * spec.quotation_basis_grams
