"""Tests for contract specifications, registry, and parity normalization."""

import datetime
import pytest

from src.contract_specs import (
    ContractRegistry,
    ContractSpec,
    GLOBAL_REGISTRY,
    normalize_price,
    denormalize_price,
)


def test_supported_contract_symbols():
    """Verify all core required contracts are present in registry."""
    symbols = GLOBAL_REGISTRY.list_supported_symbols()
    for required in ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]:
        assert required in symbols


def test_contract_spec_attributes():
    """Verify specification parameters for GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL."""
    spec_mini = GLOBAL_REGISTRY.get_spec("GOLDM")
    assert spec_mini.trading_unit_grams == 100.0
    assert spec_mini.quotation_basis_grams == 10.0
    assert spec_mini.purity_fineness == 995.0

    spec_ten = GLOBAL_REGISTRY.get_spec("GOLDTEN")
    assert spec_ten.trading_unit_grams == 10.0
    assert spec_ten.quotation_basis_grams == 10.0
    assert spec_ten.purity_fineness == 999.0

    spec_guinea = GLOBAL_REGISTRY.get_spec("GOLDGUINEA")
    assert spec_guinea.trading_unit_grams == 8.0
    assert spec_guinea.quotation_basis_grams == 8.0
    assert spec_guinea.purity_fineness == 999.0

    spec_petal = GLOBAL_REGISTRY.get_spec("GOLDPETAL")
    assert spec_petal.trading_unit_grams == 1.0
    assert spec_petal.quotation_basis_grams == 1.0
    assert spec_petal.purity_fineness == 999.0


def test_unknown_contract_symbol():
    """Verify KeyError is raised when querying an unsupported contract."""
    with pytest.raises(KeyError):
        GLOBAL_REGISTRY.get_spec("SILVERM")


def test_purity_and_unit_normalization():
    """Verify normalization to 10g of 999 purity basis."""
    spec_mini = GLOBAL_REGISTRY.get_spec("GOLDM")
    spec_guinea = GLOBAL_REGISTRY.get_spec("GOLDGUINEA")
    spec_petal = GLOBAL_REGISTRY.get_spec("GOLDPETAL")
    spec_ten = GLOBAL_REGISTRY.get_spec("GOLDTEN")

    # GOLDM: 72,000 for 10g of 995 purity
    norm_mini = normalize_price(72000.0, spec_mini, target_quote_grams=10.0, target_purity=999.0)
    expected_mini = (72000.0 / 10.0) * (999.0 / 995.0) * 10.0
    assert pytest.approx(norm_mini, rel=1e-5) == expected_mini

    # GOLDGUINEA: 58,000 for 8g of 999 purity
    norm_guinea = normalize_price(58000.0, spec_guinea, target_quote_grams=10.0, target_purity=999.0)
    expected_guinea = (58000.0 / 8.0) * (999.0 / 999.0) * 10.0  # 72,500
    assert pytest.approx(norm_guinea, rel=1e-5) == 72500.0

    # GOLDPETAL: 7,250 for 1g of 999 purity
    norm_petal = normalize_price(7250.0, spec_petal, target_quote_grams=10.0, target_purity=999.0)
    assert pytest.approx(norm_petal, rel=1e-5) == 72500.0

    # GOLDTEN: 72,500 for 10g of 999 purity
    norm_ten = normalize_price(72500.0, spec_ten, target_quote_grams=10.0, target_purity=999.0)
    assert pytest.approx(norm_ten, rel=1e-5) == 72500.0


def test_denormalization_roundtrip():
    """Verify that denormalizing a normalized price recovers the original quote."""
    spec_mini = GLOBAL_REGISTRY.get_spec("GOLDM")
    raw_quote = 72345.0
    norm = normalize_price(raw_quote, spec_mini)
    recovered = denormalize_price(norm, spec_mini)
    assert pytest.approx(recovered, rel=1e-5) == raw_quote


def test_contract_notional_value():
    """Verify total rupee notional value of 1 contract lot."""
    spec_mini = GLOBAL_REGISTRY.get_spec("GOLDM")
    # 72,000 per 10g * 100g = 720,000
    assert spec_mini.calculate_contract_value(72000.0) == 720000.0

    spec_guinea = GLOBAL_REGISTRY.get_spec("GOLDGUINEA")
    # 58,000 per 8g * 8g = 58,000
    assert spec_guinea.calculate_contract_value(58000.0) == 58000.0

    spec_petal = GLOBAL_REGISTRY.get_spec("GOLDPETAL")
    # 7,250 per 1g * 1g = 7,250
    assert spec_petal.calculate_contract_value(7250.0) == 7250.0


def test_version_sensitive_registry():
    """Verify registry supports version-sensitive contracts across dates."""
    custom_reg = ContractRegistry([])
    # Old spec: 2015-2020
    spec_old = ContractSpec(
        symbol="TESTGOLD",
        display_name="Test Gold Old",
        trading_unit_grams=10.0,
        quotation_basis_grams=10.0,
        purity_fineness=995.0,
        tick_size=1.0,
        lot_size=1,
        version="v1.0",
        effective_from=datetime.date(2015, 1, 1),
        effective_to=datetime.date(2020, 12, 31),
    )
    # New spec: 2021 onwards
    spec_new = ContractSpec(
        symbol="TESTGOLD",
        display_name="Test Gold New",
        trading_unit_grams=10.0,
        quotation_basis_grams=10.0,
        purity_fineness=999.0,
        tick_size=0.5,
        lot_size=1,
        version="v2.0",
        effective_from=datetime.date(2021, 1, 1),
        effective_to=None,
    )
    custom_reg.register(spec_old)
    custom_reg.register(spec_new)

    # Historical query in 2018 should return old spec
    res_2018 = custom_reg.get_spec("TESTGOLD", as_of_date=datetime.date(2018, 6, 1))
    assert res_2018.version == "v1.0"
    assert res_2018.purity_fineness == 995.0

    # Modern query in 2024 should return new spec
    res_2024 = custom_reg.get_spec("TESTGOLD", as_of_date=datetime.date(2024, 6, 1))
    assert res_2024.version == "v2.0"
    assert res_2024.purity_fineness == 999.0
