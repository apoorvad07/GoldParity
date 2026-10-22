"""Tests for GoldParity UI Theme, SVG vector assets, and styling helpers."""

from pathlib import Path
import pytest
from xml.etree import ElementTree as ET

from src.ui_theme import (
    COLOR_BG_DARK,
    COLOR_GOLD_PRIMARY,
    COLOR_PANEL_DARK,
    COLOR_SIDEBAR_DARK,
    get_global_css,
    load_asset_base64,
)


def test_svg_assets_exist_and_are_valid():
    """Verify that all required SVG brand assets exist and parse as valid XML/SVG."""
    assets_dir = Path("assets")
    assert assets_dir.exists()

    required_svgs = [
        "goldparity_mark.svg",
        "goldparity_logo.svg",
        "goldparity_favicon.svg",
    ]

    for filename in required_svgs:
        file_path = assets_dir / filename
        assert file_path.exists(), f"Missing required asset: {filename}"
        assert file_path.stat().st_size > 100, f"Asset is unexpectedly small: {filename}"

        # Parse SVG to verify well-formed XML
        tree = ET.parse(file_path)
        root = tree.getroot()
        assert "svg" in root.tag.lower()

    # Favicon PNG for Streamlit page_icon support
    png_favicon = assets_dir / "goldparity_favicon.png"
    assert png_favicon.exists(), "Missing goldparity_favicon.png asset"
    assert png_favicon.stat().st_size > 100, "goldparity_favicon.png is unexpectedly small"


def test_ui_theme_constants():
    """Verify core palette definitions."""
    assert COLOR_BG_DARK == "#080B10"
    assert COLOR_SIDEBAR_DARK == "#0B1017"
    assert COLOR_PANEL_DARK == "#111821"
    assert COLOR_GOLD_PRIMARY == "#D8A84E"


def test_load_asset_base64():
    """Verify asset base64 loader returns non-empty data URI for existing files and empty string for non-existent files."""
    valid_uri = load_asset_base64("assets/goldparity_mark.svg")
    assert valid_uri.startswith("data:image/svg+xml;base64,")

    missing_uri = load_asset_base64("assets/non_existent_file.png")
    assert missing_uri == ""


def test_get_global_css():
    """Verify CSS generator returns non-empty stylesheet containing required institutional rules."""
    css = get_global_css()
    assert "<style>" in css
    assert "#080B10" in css
    assert "#D8A84E" in css
    assert "Plus Jakarta Sans" in css
    assert "Cinzel" in css
    assert ".gold-initial-badge" in css
    assert ".gold-initial-badge-lg" in css
    assert "stTooltipIcon" in css
    assert "code" in css
