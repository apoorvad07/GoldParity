"""GoldParity — Institutional Commodity Derivatives Intelligence Platform.

A high-performance financial intelligence application for analyzing and comparing
MCX Gold futures contracts (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL, GOLD).

Built with institutional dark-navy & bullion-gold styling, strict data validation,
version-sensitive contract specifications, and analytical honesty.
"""

from __future__ import annotations

import base64
import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    calculate_relative_value_matrix,
    compute_multi_day_spread_series,
    enrich_with_specifications,
    simulate_spread_mean_reversion,
)
from src.contract_specs import GLOBAL_REGISTRY, ContractRegistry
from src.loader import (
    IngestionReport,
    LocalRepoReport,
    load_local_raw_repository,
    read_market_data,
)
from src.synthetic import generate_synthetic_bhavcopy
from src.ui_theme import (
    COLOR_BG_DARK,
    COLOR_GOLD_CHAMPAGNE,
    COLOR_GOLD_PRIMARY,
    COLOR_PANEL_DARK,
    COLOR_SIDEBAR_DARK,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FAVICON_B64,
    HERO_IMG_B64,
    LOGO_B64,
    MARK_B64,
    TEXTURE_IMG_B64,
    get_global_css,
)
from src.validator import DataQualityReport, validate_market_data


# -----------------------------------------------------------------------------
# Streamlit Page Setup & Institutional Theme
# -----------------------------------------------------------------------------
fav_icon_png = Path("assets/goldparity_favicon.png")
st.set_page_config(
    page_title="GoldParity — MCX Derivatives Intelligence",
    page_icon=str(fav_icon_png) if fav_icon_png.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# Inject unified institutional dark stylesheet
st.markdown(get_global_css(), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Chart Layout Helper (Prevents Duplicate Kwarg Errors)
# -----------------------------------------------------------------------------
def update_chart_theme(
    fig: go.Figure,
    height: int = 360,
    yaxis_title: Optional[str] = None,
    xaxis_title: Optional[str] = None,
    yaxis_range: Optional[List[float]] = None,
    barmode: Optional[str] = None,
    show_coloraxis_scale: bool = True,
    title: Optional[str] = None,
) -> go.Figure:
    """Safely apply the institutional dark theme to Plotly figures without duplicate kwargs."""
    layout = dict(
        paper_bgcolor="rgba(19, 29, 44, 0.0)",  # Transparent to inherit glass panel
        plot_bgcolor="#0A101C",
        font=dict(color="#A0ABBA", family="'Plus Jakarta Sans', sans-serif", size=11),
        margin=dict(l=45, r=30, t=40, b=40),
        height=height,
        xaxis=dict(
            gridcolor="rgba(160, 171, 186, 0.08)",
            zerolinecolor="rgba(160, 171, 186, 0.2)",
            tickfont=dict(color="#A0ABBA", family="'JetBrains Mono', monospace", size=10),
            title=dict(text=xaxis_title, font=dict(color="#A0ABBA", size=11)) if xaxis_title else None,
        ),
        yaxis=dict(
            gridcolor="rgba(160, 171, 186, 0.08)",
            zerolinecolor="rgba(160, 171, 186, 0.2)",
            tickfont=dict(color="#A0ABBA", family="'JetBrains Mono', monospace", size=10),
            title=dict(text=yaxis_title, font=dict(color="#A0ABBA", size=11)) if yaxis_title else None,
            range=yaxis_range,
        ),
        hoverlabel=dict(
            bgcolor="#0E172A",
            font_color="#F4F2EC",
            font_size=11,
            font_family="'Plus Jakarta Sans', sans-serif",
            bordercolor="#D6AE52",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#CBD5E1", size=10, family="'Plus Jakarta Sans', sans-serif"),
        ),
    )
    if title:
        layout["title"] = dict(text=title, font=dict(color="#F4F2EC", size=12))
    if barmode:
        layout["barmode"] = barmode
    if not show_coloraxis_scale:
        layout["coloraxis_showscale"] = False

    fig.update_layout(**layout)
    return fig


# -----------------------------------------------------------------------------
# Navigation Router State
# -----------------------------------------------------------------------------
NAV_PAGES = ["Home", "Overview", "Relative Value", "Backtesting", "Data Quality"]

if "nav_choice" not in st.session_state:
    st.session_state["nav_choice"] = "Home"


def navigate_to(page: str) -> None:
    """Callback to switch active application page from buttons and links."""
    st.session_state["nav_choice"] = page


# -----------------------------------------------------------------------------
# Sidebar Navigation & Ingestion Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    if LOGO_B64:
        st.markdown(
            f"""
            <div class="sidebar-logo-container">
                <img src="{LOGO_B64}" class="sidebar-logo-img" alt="GoldParity — Real Data. True Value." />
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-title">GOLDPARITY</div>
                <div class="sidebar-subtitle">Real Data. True Value.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='border-color: rgba(214, 174, 82, 0.15); margin: 0.5rem 0 1rem 0;' />", unsafe_allow_html=True)

    nav_labels = {
        "Home": "`H`  Home",
        "Overview": "`O`  Overview",
        "Relative Value": "`R`  Relative Value",
        "Backtesting": "`B`  Backtesting",
        "Data Quality": "`D`  Data Quality",
    }
    nav_choice = st.radio(
        "Navigation",
        options=NAV_PAGES,
        key="nav_choice",
        format_func=lambda x: nav_labels.get(x, x),
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color: rgba(214, 174, 82, 0.15); margin: 1.2rem 0 0.8rem 0;' />", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="sidebar-meta-header">
            <span class="gold-initial-badge">M</span>
            <span>Market Data Ingestion</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    has_local_raw = Path("data/raw").exists() and any(Path("data/raw").glob("*.csv"))
    source_options = []
    if has_local_raw:
        source_options.append("Local MCX Repository (data/raw/)")
    source_options.extend(["Upload MCX Bhavcopy (CSV/Excel)", "Demo Mode (Synthetic Data)"])

    source_labels = {
        "Local MCX Repository (data/raw/)": "`L`  Local MCX Repository",
        "Upload MCX Bhavcopy (CSV/Excel)": "`U`  Upload MCX Bhavcopy",
        "Demo Mode (Synthetic Data)": "`D`  Demo Mode",
    }

    data_source_mode = st.radio(
        "Ingestion Source Mode",
        options=source_options,
        index=0 if has_local_raw else 1,
        format_func=lambda s: source_labels.get(s, s),
    )

    include_gold_benchmark = False
    uploaded_file = None
    demo_mode = False

    if data_source_mode == "Local MCX Repository (data/raw/)":
        include_gold_benchmark = st.checkbox(
            "Include 1kg GOLD Benchmark",
            value=False,
        )
    elif data_source_mode == "Upload MCX Bhavcopy (CSV/Excel)":
        uploaded_file = st.file_uploader(
            "Upload MCX Bhavcopy (CSV, XLSX)",
            type=["csv", "xlsx", "xls"],
        )
    elif data_source_mode == "Demo Mode (Synthetic Data)":
        demo_mode = True

    st.markdown("<hr style='border-color: rgba(214, 174, 82, 0.15); margin: 1.2rem 0 0.8rem 0;' />", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="sidebar-meta-header">
            <span class="gold-initial-badge">B</span>
            <span>Benchmark & Parity Basis</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    benchmark_options = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
    if include_gold_benchmark or data_source_mode == "Demo Mode (Synthetic Data)":
        benchmark_options.append("GOLD")

    benchmark_sym = st.selectbox(
        "Benchmark Contract",
        options=benchmark_options,
        index=0,
    )

    purity_basis = st.selectbox(
        "Target Parity Fineness",
        options=[999.0, 995.0],
        index=0,
        format_func=lambda x: f"{int(x)} Fineness ({'Pure' if x == 999.0 else 'Standard'})",
    )

    target_quote_grams = 10.0


# -----------------------------------------------------------------------------
# Data Ingestion & State Resolution
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_synthetic_dataset(num_days: int = 1) -> pd.DataFrame:
    """Generate deterministic synthetic market data for UI demonstration."""
    return generate_synthetic_bhavcopy(
        trade_date=datetime.date(2024, 10, 15),
        num_days=num_days,
        random_seed=42,
    )


raw_df: Optional[pd.DataFrame] = None
ingestion_rep: Optional[IngestionReport] = None
local_repo_rep: Optional[LocalRepoReport] = None
is_synthetic = False
data_source_label = "Awaiting Dataset Ingestion"

if data_source_mode == "Local MCX Repository (data/raw/)":
    try:
        raw_df, local_repo_rep = load_local_raw_repository(
            raw_dir="data/raw",
            include_gold_benchmark=include_gold_benchmark,
        )
        data_source_label = f"Local MCX Historical ({local_repo_rep.files_loaded} files, {local_repo_rep.total_rows} records)"
        is_synthetic = False
    except Exception as exc:
        st.error(f"Error loading local MCX repository: {exc}")
elif uploaded_file is not None:
    try:
        raw_df, ingestion_rep = read_market_data(uploaded_file, filename=uploaded_file.name)
        data_source_label = f"Uploaded Bhavcopy: {uploaded_file.name} (Historical)"
        is_synthetic = False
    except Exception as exc:
        st.error(f"Error reading uploaded file: {exc}")
elif demo_mode:
    raw_df = load_synthetic_dataset(num_days=30 if nav_choice == "Backtesting" else 1)
    data_source_label = "Synthetic Demonstration Dataset (Sample Observations)"
    is_synthetic = True


# Validate and enrich
clean_df = pd.DataFrame()
quality_rep = DataQualityReport()
enriched_df = pd.DataFrame()

if raw_df is not None and not raw_df.empty:
    clean_df, quality_rep = validate_market_data(raw_df)
    if not clean_df.empty:
        enriched_df = enrich_with_specifications(
            clean_df,
            target_quote_grams=target_quote_grams,
            target_purity=purity_basis,
        )

# Date filter resolution
available_dates = sorted(enriched_df["Date"].unique().tolist()) if not enriched_df.empty else []
selected_date = available_dates[-1] if available_dates else datetime.date(2024, 10, 15)

with st.sidebar:
    if local_repo_rep and local_repo_rep.files_loaded > 0:
        st.markdown(
            f"""
            <div style="background: rgba(19, 29, 44, 0.7); border: 1px solid rgba(214, 174, 82, 0.25); border-radius: 8px; padding: 0.65rem 0.85rem; margin-top: 0.8rem; font-size: 0.76rem;">
                <div style="color: #D6AE52; font-weight: 700; margin-bottom: 0.35rem; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; display: flex; align-items: center; gap: 0.45rem;">
                    <span class="gold-initial-badge">L</span>
                    <span>Active Local Repository</span>
                </div>
                <div style="color: #CBD5E1; margin-bottom: 0.15rem;">Loaded: <strong>{local_repo_rep.files_loaded} files</strong> ({local_repo_rep.total_rows} rows)</div>
                <div style="color: #A0ABBA; font-size: 0.72rem;">Contracts: <code>{', '.join(local_repo_rep.contracts_found)}</code></div>
                <div style="color: #A0ABBA; font-size: 0.72rem;">Date Span: <code>{local_repo_rep.date_range[0]} to {local_repo_rep.date_range[1]}</code></div>
                {"<div style='color: #F2D58A; font-size: 0.7rem; margin-top: 0.2rem;'>Status: 1kg GOLD Benchmark Isolated</div>" if local_repo_rep.files_excluded > 0 else "<div style='color: #34D399; font-size: 0.7rem; margin-top: 0.2rem;'>Status: 1kg GOLD Benchmark Included</div>"}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if len(available_dates) > 1:
        st.markdown("<hr style='border-color: rgba(214, 174, 82, 0.15); margin: 0.8rem 0 0.5rem 0;' />", unsafe_allow_html=True)
        selected_date = st.selectbox(
            "Select Trade Date",
            options=available_dates,
            index=len(available_dates) - 1,
            format_func=lambda d: d.strftime("%d-%b-%Y"),
        )


# Status badge rendering helper with subtle gold initial badge
if not is_synthetic and not enriched_df.empty:
    if local_repo_rep:
        badge_html = f'<span class="badge-live"><span class="gold-initial-badge">L</span> Local Historical ({len(local_repo_rep.contracts_found)} Contracts)</span>'
    else:
        badge_html = '<span class="badge-live"><span class="gold-initial-badge">U</span> Uploaded Historical</span>'
elif is_synthetic:
    badge_html = '<span class="badge-demo"><span class="gold-initial-badge">D</span> Synthetic Demo</span>'
else:
    badge_html = '<span class="badge-idle"><span class="status-dot status-dot-idle"></span>Awaiting Ingestion</span>' 

selected_date_str = selected_date.strftime("%d-%b-%Y") if available_dates else "None Selected"


# Demo mode alert banner
if is_synthetic:
    st.markdown(
        """
        <div class="demo-banner">
            <span class="gold-initial-badge">D</span>
            <div class="demo-banner-tag">SIMULATION</div>
            <div>
                <strong>Demonstration Mode Active</strong> — Displaying generated synthetic observations solely for interface
                and pipeline validation. Real market observations and trading signals are never fabricated.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# VIEW 0: HOME LANDING PAGE
# -----------------------------------------------------------------------------
if nav_choice == "Home":
    # Cinematic Vault Hero Banner
    st.markdown(
        """
        <div class="landing-hero">
            <div class="landing-eyebrow">
                MCX Gold Futures Analytics
            </div>
            <div class="landing-headline">
                Compare. Analyze.<br />
                <span class="gold-gradient-text">Find the Real Value.</span>
            </div>
            <div class="landing-subtext">
                GoldParity is an institutional commodity derivatives intelligence platform engineered for quantitative traders, bullion hedgers, and arbitrageurs. It unifies disparate Multi Commodity Exchange of India (MCX) gold futures contracts — standardizing lot sizes, physical delivery mechanisms, and fineness variations into pure, actionable ₹/10g parity basis.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Hero Action Buttons
    cta_col1, cta_col2, _ = st.columns([1.5, 1.8, 3.7])
    with cta_col1:
        st.button(
            "Launch Terminal",
            key="btn_hero_overview",
            on_click=navigate_to,
            args=("Overview",),
            type="primary",
            use_container_width=True,
        )
    with cta_col2:
        st.button(
            "Explore Relative Value",
            key="btn_hero_rv",
            on_click=navigate_to,
            args=("Relative Value",),
            type="secondary",
            use_container_width=True,
        )

    # Core Capabilities Header
    st.markdown(
        """
        <div style="margin: 2.2rem 0 1.1rem 0;">
            <div class="landing-eyebrow" style="margin-bottom: 0.45rem;">Core Platform Capabilities</div>
            <h3 class="brand-display" style="font-size: 1.45rem; color: #F5F5F2; margin-top: 0; margin-bottom: 0.25rem;">
                Institutional Parity & Analytical Infrastructure
            </h3>
            <div style="color: #A8B0BA; font-size: 0.88rem;">
                Dedicated analytics modules designed for cross-contract valuation, spread arbitrage, and data verification.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Interactive Feature Cards Grid with Initial Badges
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div style="margin-bottom: 1.15rem;">
                        <span class="gold-initial-badge-lg">O</span>
                    </div>
                    <div class="feature-card-title">Parity Normalization</div>
                    <div style="font-size: 0.72rem; color: #D8A84E; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem;">True ₹/10g Equivalence</div>
                    <div class="feature-card-desc">
                        Standardizes contract lot sizes (1kg, 100g, 10g, 8g, 1g) and purity specifications (995 standard vs 999 fine) to an institutional ₹/10g benchmark quote.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Open Overview",
            key="btn_card_ov",
            on_click=navigate_to,
            args=("Overview",),
            use_container_width=True,
        )

    with c2:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div style="margin-bottom: 1.15rem;">
                        <span class="gold-initial-badge-lg">R</span>
                    </div>
                    <div class="feature-card-title">Relative Value Matrix</div>
                    <div style="font-size: 0.72rem; color: #D8A84E; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem;">Cross-Contract Basis</div>
                    <div class="feature-card-desc">
                        Dynamic cross-contract spread matrix, synthetic calendar curves, basis divergence in bps, and statistical anomaly detection relative to benchmark.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "View Spreads",
            key="btn_card_rv",
            on_click=navigate_to,
            args=("Relative Value",),
            use_container_width=True,
        )

    with c3:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div style="margin-bottom: 1.15rem;">
                        <span class="gold-initial-badge-lg">B</span>
                    </div>
                    <div class="feature-card-title">Spread Backtesting</div>
                    <div style="font-size: 0.72rem; color: #D8A84E; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem;">Statistical Arbitrage</div>
                    <div class="feature-card-desc">
                        Simulates quantitative mean-reversion pairs strategies with strictly lagged signals (zero look-ahead bias), transaction friction deductions, and drawdown metrics.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Run Backtest",
            key="btn_card_bt",
            on_click=navigate_to,
            args=("Backtesting",),
            use_container_width=True,
        )

    with c4:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div style="margin-bottom: 1.15rem;">
                        <span class="gold-initial-badge-lg">D</span>
                    </div>
                    <div class="feature-card-title">Data Quality Audit</div>
                    <div style="font-size: 0.72rem; color: #D8A84E; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem;">Exchange Integrity</div>
                    <div class="feature-card-desc">
                        Strict multi-file bhavcopy parser, canonical schema normalization, timestamp continuity checks, duplicate prevention, and zero fabricated data guarantee.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Inspect Quality",
            key="btn_card_dq",
            on_click=navigate_to,
            args=("Data Quality",),
            use_container_width=True,
        )

    # Dynamic Bottom Information Strip
    if local_repo_rep and local_repo_rep.files_loaded > 0:
        coverage_title = f"Local MCX Historical Repository ({local_repo_rep.files_loaded} Files Ingested)"
        coverage_sub = f"Loaded {local_repo_rep.total_rows} historical observations spanning {local_repo_rep.date_range[0]} to {local_repo_rep.date_range[1]} across {len(local_repo_rep.contracts_found)} active contract series (offline local CSV bhavcopies)."
        detected_contracts = local_repo_rep.contracts_found
    elif uploaded_file is not None:
        coverage_title = f"Bhavcopy File Ingested: {uploaded_file.name}"
        coverage_sub = f"Normalized {len(clean_df)} historical records across {len(clean_df['Symbol'].unique()) if not clean_df.empty else 0} contracts from user-provided file."
        detected_contracts = sorted(clean_df["Symbol"].unique().tolist()) if not clean_df.empty else []
    elif is_synthetic:
        coverage_title = "Synthetic Demonstration Dataset Active (Sample Observations)"
        coverage_sub = "Deterministic multi-day synthetic observations for interface and pipeline demonstration. Real market observations are never fabricated."
        detected_contracts = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
    else:
        coverage_title = "Market Data Repository Awaiting Ingestion"
        coverage_sub = "No market data loaded yet. Select Local Repository, upload MCX Bhavcopy, or activate Demo Mode in sidebar."
        detected_contracts = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]

    badges_html = " ".join([f'<span class="hallmark-badge">{sym}</span>' for sym in detected_contracts])

    with st.container():
        st.markdown(
            f"""<div class="bottom-info-strip">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1.25rem;">
                    <div>
                        <div style="font-size: 0.7rem; font-weight: 700; color: #D8A84E; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.35rem;">
                            Market Repository Coverage & Metrics
                        </div>
                        <div style="font-family: 'Cinzel', serif; font-size: 1.22rem; font-weight: 700; color: #F5F5F2;">
                            {coverage_title}
                        </div>
                        <div style="color: #A8B0BA; font-size: 0.85rem; margin-top: 0.25rem;">
                            {coverage_sub}
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.45rem; flex-wrap: wrap; align-items: center;">
                        {badges_html}
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # 4 Responsive Cards using Streamlit native columns
        cov_col1, cov_col2, cov_col3, cov_col4 = st.columns(4)
        with cov_col1:
            st.markdown(
                """<div class="coverage-metric-card">
                    <div class="coverage-metric-tag" style="color: #34D399;">ANALYTICAL INTEGRITY</div>
                    <div class="coverage-metric-title">Analytical Honesty</div>
                    <div class="coverage-metric-desc">Missing or unavailable values are disclosed, not fabricated.</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with cov_col2:
            st.markdown(
                """<div class="coverage-metric-card">
                    <div class="coverage-metric-tag" style="color: #D8A84E;">STANDARDIZED BASIS</div>
                    <div class="coverage-metric-title">Purity Normalization</div>
                    <div class="coverage-metric-desc">999 and 995 fineness conversion basis.</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with cov_col3:
            st.markdown(
                """<div class="coverage-metric-card">
                    <div class="coverage-metric-tag" style="color: #D8A84E;">EXCHANGE SPECIFICATIONS</div>
                    <div class="coverage-metric-title">Contract Awareness</div>
                    <div class="coverage-metric-desc">Uses applicable MCX contract specifications.</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with cov_col4:
            st.markdown(
                """<div class="coverage-metric-card">
                    <div class="coverage-metric-tag" style="color: #34D399;">SIMULATION FIDELITY</div>
                    <div class="coverage-metric-title">Zero Look-Ahead</div>
                    <div class="coverage-metric-desc">Backtests use only information available at each point in time.</div>
                </div>""",
                unsafe_allow_html=True,
            )


# -----------------------------------------------------------------------------
# VIEW 1: OVERVIEW
# -----------------------------------------------------------------------------
elif nav_choice == "Overview":
    # Cinematic Hero Section
    st.markdown(
        f"""
        <div class="hero-container">
            <div class="hero-pill"><span class="gold-initial-badge">O</span> Institutional Parity Engine</div>
            <div class="hero-headline">
                Precision in <span class="gold-text">Gold Market</span> Intelligence
            </div>
            <div class="hero-desc">
                Institutional parity analytics, purity-normalized relative value spreads, and term-structure
                dynamics across Multi Commodity Exchange of India (MCX) Gold futures contracts.
            </div>
            <div class="hero-status-strip">
                <div class="hero-stat-item">
                    <span>Source:</span> {badge_html}
                </div>
                <div class="hero-stat-item">
                    <span>Trade Date:</span> <strong>{selected_date_str}</strong>
                </div>
                <div class="hero-stat-item">
                    <span>Benchmark:</span> <strong>{benchmark_sym}</strong>
                </div>
                <div class="hero-stat-item">
                    <span>Parity Target:</span> <strong>₹ / 10g ({int(purity_basis)} Fineness)</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if local_repo_rep and local_repo_rep.files_loaded > 0:
        st.markdown(
            f"""
            <div style="background: rgba(13, 20, 36, 0.85); border: 1px solid rgba(214, 174, 82, 0.28); border-radius: 8px; padding: 0.75rem 1.25rem; margin-bottom: 1.25rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <div>
                    <span style="color: #D6AE52; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase;">MCX Historical Repository:</span>
                    <span style="color: #CBD5E1; font-size: 0.82rem; margin-left: 0.5rem;">{local_repo_rep.total_rows} observations across <strong>{', '.join(local_repo_rep.contracts_found)}</strong> ({local_repo_rep.date_range[0]} to {local_repo_rep.date_range[1]})</span>
                </div>
                <div>
                    {"<span class='hallmark-badge' style='color:#F2D58A;'>1kg GOLD Benchmark Isolated</span>" if not include_gold_benchmark else "<span class='hallmark-badge' style='color:#34D399;'>1kg GOLD Benchmark Included</span>"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if enriched_df.empty:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon"><span class="gold-initial-badge-lg">O</span></div>
                <div class="empty-state-title">Awaiting Market Data</div>
                <div class="empty-state-desc">
                    Upload an official MCX Bhavcopy (CSV or Excel) in the sidebar to inspect live contract parity,
                    or activate <strong>Demo Mode</strong> to explore the analytical dashboard.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("MCX Gold Contract Specification Architecture", expanded=True):
            specs_data = [s.to_dict() for s in GLOBAL_REGISTRY.get_all_active_specs().values()]
            st.dataframe(pd.DataFrame(specs_data), use_container_width=True, hide_index=True)

    else:
        # Relative value matrix calculation for selected trade date
        matrix_df, summary = calculate_relative_value_matrix(
            enriched_df,
            benchmark_symbol=benchmark_sym,
            trade_date=selected_date,
        )

        # Responsive Key Metric Cards
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1:
            st.metric(
                label=f"{benchmark_sym} Norm. Close",
                value=f"₹{summary.benchmark_normalized_price:,.2f}" if summary else "—",
            )
        with m_col2:
            st.metric(
                label="Active Contracts",
                value=f"{summary.total_contracts}" if summary else "0",
            )
        with m_col3:
            st.metric(
                label="Traded Volume",
                value=f"{summary.total_volume_lots:,} Lots" if summary else "—",
            )
        with m_col4:
            st.metric(
                label="Estimated Turnover",
                value=f"₹{summary.total_turnover_inr / 1e7:,.2f} Cr" if summary else "—",
            )
        with m_col5:
            max_prem_txt = f"+{summary.max_premium_pct:.2f}%" if summary and summary.max_premium_pct is not None else "0.0%"
            st.metric(
                label=f"Max Premium ({summary.max_premium_contract or ''})",
                value=max_prem_txt,
            )

        st.markdown("<br/>", unsafe_allow_html=True)

        # Main Analytical Visualization: Multi-Contract Price Comparison
        st.markdown(
            """
            <div class="card-panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">Cross-Contract Price Structure</div>
                        <div class="panel-subtitle">Multi-contract comparison across expiries with normalization controls</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        viz_mode = st.radio(
            "Visualization Metric",
            options=["Normalized Parity Price (₹/10g 999 Basis)", "Raw Quoted Price (₹)"],
            horizontal=True,
            label_visibility="collapsed",
        )

        y_field = "NormalizedClose" if "Normalized" in viz_mode else "Close"
        y_title = f"Normalized Price (₹/10g, {int(purity_basis)} Fineness)" if "Normalized" in viz_mode else "Raw Quoted Price (₹)"

        chart_df = matrix_df.sort_values(by="DaysToExpiry").copy()
        chart_df["ContractLabel"] = chart_df["Symbol"] + " (" + chart_df["ExpiryDate"].astype(str) + ")"

        fig_main = px.bar(
            chart_df,
            x="ContractLabel",
            y=y_field,
            color="Symbol",
            color_discrete_map={
                "GOLDM": "#D6AE52",
                "GOLDTEN": "#F2D58A",
                "GOLDGUINEA": "#60A5FA",
                "GOLDPETAL": "#34D399",
                "GOLD": "#CBD5E1",
            },
            hover_data=["Close", "NormalizedClose", "QuotationBasisGrams", "PurityFineness", "Volume", "OpenInterest"],
            labels={y_field: y_title, "ContractLabel": "Contract Series"},
        )
        update_chart_theme(
            fig_main,
            height=390,
            yaxis_title=y_title,
            xaxis_title="Contract Series & Expiry",
            yaxis_range=[chart_df[y_field].min() * 0.96, chart_df[y_field].max() * 1.02],
        )
        st.plotly_chart(fig_main, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Supporting Panels: Market Snapshot & Liquidity Distribution
        left_col, right_col = st.columns([1.35, 1.0])

        with left_col:
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Market Observations & Parity Snapshot</div>
                            <div class="panel-subtitle">Actual observed exchange settlement values and converted unit equivalents</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            display_cols = [
                "Symbol",
                "ExpiryDate",
                "Close",
                "QuotationBasisGrams",
                "PurityFineness",
                "NormalizedClose",
                "ContractValueINR",
                "Volume",
                "OpenInterest",
            ]
            snapshot_view = matrix_df[display_cols].copy()
            snapshot_view.columns = [
                "Symbol",
                "Expiry",
                "Raw Quote (₹)",
                "Quote Basis",
                "Purity",
                f"Norm. Close ({int(purity_basis)}/10g)",
                "Lot Value (₹)",
                "Volume (Lots)",
                "OI",
            ]
            st.dataframe(
                snapshot_view.style.format(
                    {
                        "Raw Quote (₹)": "₹{:,.2f}",
                        "Quote Basis": "{:.0f}g",
                        "Purity": "{:.0f}",
                        f"Norm. Close ({int(purity_basis)}/10g)": "₹{:,.2f}",
                        "Lot Value (₹)": "₹{:,.0f}",
                        "Volume (Lots)": "{:,}",
                        "OI": "{:,}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with right_col:
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Liquidity & Open Interest Share</div>
                            <div class="panel-subtitle">Contract market participation and active open interest</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            agg_liq = matrix_df.groupby("Symbol")[["Volume", "OpenInterest"]].sum().reset_index()
            fig_liq = go.Figure()
            fig_liq.add_trace(
                go.Bar(
                    name="Volume (Lots)",
                    x=agg_liq["Symbol"],
                    y=agg_liq["Volume"],
                    marker_color="#D6AE52",
                )
            )
            fig_liq.add_trace(
                go.Bar(
                    name="Open Interest",
                    x=agg_liq["Symbol"],
                    y=agg_liq["OpenInterest"],
                    marker_color="#60A5FA",
                )
            )
            update_chart_theme(
                fig_liq,
                height=340,
                barmode="group",
            )
            st.plotly_chart(fig_liq, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Contract Specifications Drawer
        with st.expander("Configured MCX Contract Specifications & Version Registry"):
            specs_df = pd.DataFrame([s.to_dict() for s in GLOBAL_REGISTRY.get_all_active_specs().values()])
            st.dataframe(specs_df, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# VIEW 2: RELATIVE VALUE
# -----------------------------------------------------------------------------
elif nav_choice == "Relative Value":
    st.markdown(
        """
        <div class="section-banner">
            <div class="section-banner-title"><span class="gold-initial-badge" style="width: 26px; height: 26px; font-size: 0.88rem; margin-right: 0.5rem;">R</span> Relative Value & Parity Analysis</div>
            <div class="section-banner-subtitle">Purity-adjusted cross-contract spreads and forward term-structure evaluation.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if enriched_df.empty:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon"><span class="gold-initial-badge-lg">R</span></div>
                <div class="empty-state-title">No Data for Relative Value Analysis</div>
                <div class="empty-state-desc">
                    Relative value matrices, purity basis adjustments, and term structure curves require
                    either an uploaded MCX Bhavcopy or Demo Mode.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        matrix_df, summary = calculate_relative_value_matrix(
            enriched_df,
            benchmark_symbol=benchmark_sym,
            trade_date=selected_date,
        )

        st.markdown(
            f"""
            <div class="card-panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">Cross-Contract Parity Matrix (Benchmark: {benchmark_sym})</div>
                        <div class="panel-subtitle">All prices normalized to ₹ per {int(target_quote_grams)}g of {int(purity_basis)} fineness pure gold equivalent</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        matrix_cols = [
            "Symbol",
            "ExpiryDate",
            "DaysToExpiry",
            "Close",
            "NormalizedClose",
            "SpreadINR",
            "SpreadPct",
            "Volume",
            "OpenInterest",
        ]
        display_m = matrix_df[matrix_cols].copy()
        display_m.columns = [
            "Symbol",
            "Expiry",
            "Days to Exp",
            "Raw Quoted (₹)",
            "Normalized Close (₹/10g)",
            f"Spread vs {benchmark_sym} (₹/10g)",
            "Basis Spread (%)",
            "Volume",
            "OI",
        ]

        def highlight_spread(val):
            if pd.isna(val):
                return ""
            if val > 0.05:
                return "color: #34D399; font-weight: 700;"  # Premium
            elif val < -0.05:
                return "color: #F87171; font-weight: 700;"  # Discount
            return "color: #A0ABBA;"

        st.dataframe(
            display_m.style.format(
                {
                    "Raw Quoted (₹)": "₹{:,.2f}",
                    "Normalized Close (₹/10g)": "₹{:,.2f}",
                    f"Spread vs {benchmark_sym} (₹/10g)": "{:+,.2f}",
                    "Basis Spread (%)": "{:+.3f}%",
                    "Volume": "{:,}",
                    "OI": "{:,}",
                }
            ).map(highlight_spread, subset=["Basis Spread (%)", f"Spread vs {benchmark_sym} (₹/10g)"]),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Basis Spread (%) Distribution</div>
                            <div class="panel-subtitle">Premium (+) or Discount (-) relative to benchmark nearest contract</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            fig_spread = px.bar(
                matrix_df.sort_values(by="DaysToExpiry"),
                x="Symbol",
                y="SpreadPct",
                color="SpreadPct",
                color_continuous_scale=["#EF4444", "#1E293B", "#10B981"],
                text="SpreadPct",
                labels={"SpreadPct": "Basis Spread (%)", "Symbol": "Contract"},
                hover_data=["ExpiryDate", "SpreadINR", "NormalizedClose"],
            )
            fig_spread.update_traces(texttemplate="%{text:+.2f}%", textposition="outside")
            update_chart_theme(
                fig_spread,
                height=360,
                show_coloraxis_scale=False,
                yaxis_title="Basis Spread (%)",
            )
            st.plotly_chart(fig_spread, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with chart_col2:
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Normalized Forward Term Structure</div>
                            <div class="panel-subtitle">Contract parity curves across delivery expiries (contango vs backwardation)</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            fig_curve = px.line(
                matrix_df.sort_values(by="DaysToExpiry"),
                x="DaysToExpiry",
                y="NormalizedClose",
                color="Symbol",
                markers=True,
                color_discrete_map={
                    "GOLDM": "#D6AE52",
                    "GOLDTEN": "#F2D58A",
                    "GOLDGUINEA": "#60A5FA",
                    "GOLDPETAL": "#34D399",
                    "GOLD": "#CBD5E1",
                },
                hover_data=["ExpiryDate", "Close", "PurityFineness"],
                labels={
                    "DaysToExpiry": "Days to Expiry",
                    "NormalizedClose": f"Normalized Price (₹/10g, {int(purity_basis)})",
                },
            )
            update_chart_theme(
                fig_curve,
                height=360,
                yaxis_title=f"Normalized (₹/10g, {int(purity_basis)})",
            )
            st.plotly_chart(fig_curve, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Methodology & Analytical Rigor Callout
        st.markdown(
            f"""
            <div class="methodology-callout">
                <div class="methodology-title">Parity Normalization Methodology & Assumptions</div>
                <div class="methodology-text">
                    <strong>1. Unit Quotation Conversion:</strong> Quotes are first adjusted to a price per gram using configured contract specs (e.g., GOLDM = 10g quote, GOLDGUINEA = 8g quote, GOLDPETAL = 1g quote).<br/>
                    <strong>2. Purity Normalization:</strong> Raw prices are scaled to the benchmark purity fineness ({int(purity_basis)}/1000):
                    <br/>
                    <code style="color: #D6AE52; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">Normalized Price = (Raw Quote / Quote Grams) * (Target Purity / Contract Purity) * 10.0</code>
                    <br/>
                    <strong>3. Limitations & Execution Friction:</strong> Quoted basis spreads do not guarantee riskless arbitrage. Exploiting parity spreads in live markets requires factoring in MCX exchange fees, Commodity Transaction Tax (CTT: 0.01% on sell side), GST (18%), delivery tender margin escalation, and bid-ask spread slippage.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# VIEW 3: BACKTESTING
# -----------------------------------------------------------------------------
elif nav_choice == "Backtesting":
    st.markdown(
        """
        <div class="section-banner">
            <div class="section-banner-title"><span class="gold-initial-badge" style="width: 26px; height: 26px; font-size: 0.88rem; margin-right: 0.5rem;">B</span> Historical Strategy Evaluation & Backtesting</div>
            <div class="section-banner-subtitle">Research-grade evaluation of parity spread mean-reversion without look-ahead bias or fabricated returns.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    unique_dates_count = len(enriched_df["Date"].unique()) if not enriched_df.empty else 0

    if enriched_df.empty or unique_dates_count < 2:
        st.markdown(
            f"""
            <div class="empty-state">
                <div class="empty-state-icon"><span class="gold-initial-badge-lg">B</span></div>
                <div class="empty-state-title">Chronological Time-Series Required</div>
                <div class="empty-state-desc">
                    The currently loaded dataset contains <strong>{unique_dates_count}</strong> trade date(s).
                    Evaluating historical spread stationarity, roll carry, and mean-reversion dynamics
                    requires a multi-day series of MCX Bhavcopies.
                </div>
                <div style="color: #F4D18A; font-size: 0.82rem; background: rgba(216, 168, 78, 0.1); border: 1px solid rgba(216, 168, 78, 0.3); display: inline-block; padding: 6px 16px; border-radius: 4px;">
                    Note: Activate <strong>Demo Mode</strong> in the sidebar to simulate a 30-day chronological series.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Strategy Architecture & Analytical Integrity Protocol", expanded=True):
            st.markdown(
                """
                ### Relative Value Pairs Strategy Architecture
                1. **Pair Formulation**: Compare contract pair (e.g. `GOLDGUINEA` vs `GOLDM`, or `GOLDTEN` vs `GOLDM`).
                2. **Normalized Parity Spread**:
                   $$\\text{Spread}_t = \\text{NormClose}_A(t) - \\text{NormClose}_B(t)$$
                3. **Lagged Signal Formulation (Zero Look-Ahead Bias)**:
                   Signals are strictly derived from lagged statistics $Z_{t-1} = \\frac{\\text{Spread}_{t-1} - \\mu_{20}(t-1)}{\\sigma_{20}(t-1)}$ so execution occurs on observed prices without future contamination.
                4. **Friction Deductions**:
                   Every simulated turnover transition accounts for realistic execution friction (brokerage, exchange fees, CTT, and bid-ask slippage).
                """
            )

    else:
        # Multi-day dataset is active: Render strategy controls and evaluation
        available_legs = sorted(enriched_df["Symbol"].unique().tolist())
        idx_a = available_legs.index("GOLDGUINEA") if "GOLDGUINEA" in available_legs else 0
        idx_b = available_legs.index("GOLDM") if "GOLDM" in available_legs else (1 if len(available_legs) > 1 else 0)

        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns(4)
        with ctrl_col1:
            sym_a = st.selectbox("Contract Leg A", options=available_legs, index=idx_a)
        with ctrl_col2:
            sym_b = st.selectbox("Contract Leg B (Reference)", options=available_legs, index=idx_b)
        with ctrl_col3:
            z_thresh = st.slider("Z-Score Entry Threshold (σ)", min_value=0.5, max_value=2.5, value=1.0, step=0.1)
        with ctrl_col4:
            friction_bps = st.number_input("Execution Friction (bps per leg)", min_value=0.0, max_value=25.0, value=3.0, step=0.5)

        spread_df = compute_multi_day_spread_series(enriched_df, symbol_a=sym_a, symbol_b=sym_b)
        sim_df, bt_result = simulate_spread_mean_reversion(spread_df, z_entry_threshold=z_thresh, friction_bps=friction_bps)

        if bt_result is None:
            st.warning("Insufficient overlapping chronological records to calculate statistical spread parameters.")
        else:
            # Performance Metric Cards
            b1, b2, b3, b4, b5 = st.columns(5)
            with b1:
                st.metric("Evaluated Days", f"{bt_result.total_days} Obs")
            with b2:
                st.metric("Total Signals", f"{bt_result.total_trades} Trades")
            with b3:
                ret_color = "#34D399" if bt_result.cumulative_return_pct >= 0 else "#F87171"
                st.metric("Cumulative Return", f"{bt_result.cumulative_return_pct:+.2f}%")
            with b4:
                st.metric("Max Drawdown", f"{bt_result.max_drawdown_pct:.2f}%")
            with b5:
                st.metric("Spread Volatility (1σ)", f"₹{bt_result.spread_volatility_inr:,.2f}")

            st.markdown("<br/>", unsafe_allow_html=True)

            # Chart 1: Spread Series & Moving Average Bands
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Parity Spread Dynamics & Rolling Bands</div>
                            <div class="panel-subtitle">Normalized spread (₹/10g) with 20-day rolling mean and mean-reversion bounds</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            fig_spread_ts = go.Figure()
            fig_spread_ts.add_trace(
                go.Scatter(
                    x=sim_df["Date"],
                    y=sim_df["SpreadINR"],
                    mode="lines+markers",
                    name=f"Spread ({sym_a} - {sym_b})",
                    line=dict(color="#D6AE52", width=2),
                )
            )
            if "Spread_Mean_20d" in sim_df.columns:
                fig_spread_ts.add_trace(
                    go.Scatter(
                        x=sim_df["Date"],
                        y=sim_df["Spread_Mean_20d"],
                        mode="lines",
                        name="20d Mean",
                        line=dict(color="#A0ABBA", dash="dash"),
                    )
                )
                upper_band = sim_df["Spread_Mean_20d"] + z_thresh * sim_df["Spread_Std_20d"]
                lower_band = sim_df["Spread_Mean_20d"] - z_thresh * sim_df["Spread_Std_20d"]
                fig_spread_ts.add_trace(
                    go.Scatter(
                        x=sim_df["Date"],
                        y=upper_band,
                        mode="lines",
                        name=f"+{z_thresh}σ Band",
                        line=dict(color="rgba(248, 113, 113, 0.45)", dash="dot"),
                    )
                )
                fig_spread_ts.add_trace(
                    go.Scatter(
                        x=sim_df["Date"],
                        y=lower_band,
                        mode="lines",
                        name=f"-{z_thresh}σ Band",
                        line=dict(color="rgba(52, 211, 153, 0.45)", dash="dot"),
                    )
                )

            update_chart_theme(
                fig_spread_ts,
                height=360,
                yaxis_title="Spread (₹/10g)",
            )
            st.plotly_chart(fig_spread_ts, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Chart 2: Cumulative Return & Drawdown Panels
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.markdown(
                    """
                    <div class="card-panel">
                        <div class="panel-header">
                            <div>
                                <div class="panel-title">Cumulative Strategy Equity Curve (%)</div>
                                <div class="panel-subtitle">Net cumulative return with lagged signal execution and friction deductions</div>
                            </div>
                        </div>
                    """,
                    unsafe_allow_html=True,
                )
                fig_ret = go.Figure()
                fig_ret.add_trace(
                    go.Scatter(
                        x=sim_df["Date"],
                        y=sim_df["CumulativeReturnPct"],
                        mode="lines",
                        name="Cumulative Return %",
                        line=dict(color="#34D399" if bt_result.cumulative_return_pct >= 0 else "#F87171", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(52, 211, 153, 0.08)" if bt_result.cumulative_return_pct >= 0 else "rgba(248, 113, 113, 0.08)",
                    )
                )
                update_chart_theme(
                    fig_ret,
                    height=280,
                    yaxis_title="Return (%)",
                )
                st.plotly_chart(fig_ret, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c_col2:
                st.markdown(
                    """
                    <div class="card-panel">
                        <div class="panel-header">
                            <div>
                                <div class="panel-title">Historical Drawdown Profile (%)</div>
                                <div class="panel-subtitle">Underwater curve visualizing peak-to-trough equity retracements</div>
                            </div>
                        </div>
                    """,
                    unsafe_allow_html=True,
                )
                fig_dd = go.Figure()
                fig_dd.add_trace(
                    go.Scatter(
                        x=sim_df["Date"],
                        y=sim_df["DrawdownPct"],
                        mode="lines",
                        name="Drawdown %",
                        line=dict(color="#F87171", width=1.5),
                        fill="tozeroy",
                        fillcolor="rgba(248, 113, 113, 0.15)",
                    )
                )
                update_chart_theme(
                    fig_dd,
                    height=280,
                    yaxis_title="Drawdown (%)",
                )
                st.plotly_chart(fig_dd, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Analytical Honesty Disclaimer
            st.markdown(
                f"""
                <div class="methodology-callout">
                    <div class="methodology-title">Research-Grade Evaluation Disclosures</div>
                    <div class="methodology-text">
                        <strong>Analytical Integrity:</strong> {bt_result.disclaimer}<br/>
                        <strong>Total Friction Cost Deducted:</strong> {bt_result.friction_cost_pct:.3f}% (reflecting {friction_bps:.1f} bps per leg on {bt_result.total_trades} executed transitions).<br/>
                        Past performance of cross-contract spreads does not guarantee future cointegration or mean-reversion. Thin retail contracts (e.g. GOLDPETAL) may experience liquidity gaps during high market volatility.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# -----------------------------------------------------------------------------
# VIEW 4: DATA QUALITY
# -----------------------------------------------------------------------------
elif nav_choice == "Data Quality":
    st.markdown(
        """
        <div class="section-banner">
            <div class="section-banner-title"><span class="gold-initial-badge" style="width: 26px; height: 26px; font-size: 0.88rem; margin-right: 0.5rem;">D</span> Data Quality & Ingestion Audit</div>
            <div class="section-banner-subtitle">Complete audit of ingested Bhavcopy files, canonical column mappings, date validations, and error logs.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if raw_df is None or raw_df.empty:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon"><span class="gold-initial-badge-lg">D</span></div>
                <div class="empty-state-title">No Dataset Ingested</div>
                <div class="empty-state-desc">
                    Upload an MCX Bhavcopy file in the sidebar to review column mapping diagnostics,
                    date format parsing, and data validation logs.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Audit Summary Metrics
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            st.metric("Total Rows Ingested", f"{quality_rep.total_rows_ingested:,}")
        with q2:
            st.metric("Valid Rows Retained", f"{quality_rep.valid_rows_retained:,}")
        with q3:
            st.metric("Dropped Rows", f"{quality_rep.dropped_rows_count:,}")
        with q4:
            st.metric("Deduplicated Rows", f"{quality_rep.duplicate_rows_count:,}")

        st.markdown("<br/>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["Column Mapping Diagnostics", "Validation Issues Log", "Data Inspector"])

        with tab1:
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Exchange Column Schema Resolution</div>
                            <div class="panel-subtitle">Transparent mapping between exchange Bhavcopy headers and GoldParity canonical schema</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            if local_repo_rep:
                st.markdown(
                    f"**Repository Directory**: `data/raw/` &nbsp;|&nbsp; **Files Ingested**: `{local_repo_rep.files_loaded} / {local_repo_rep.files_scanned}` &nbsp;|&nbsp; **Benchmark Isolated**: `{'Yes (1kg GOLD Excluded)' if local_repo_rep.files_excluded > 0 else 'No (1kg GOLD Included)'}`"
                )
                file_rows = []
                for fs in local_repo_rep.file_summaries:
                    status_badge = "Loaded" if fs.status == "Loaded" else ("Excluded (Benchmark)" if "Excluded" in fs.status else fs.status)
                    file_rows.append(
                        {
                            "File Name": fs.filename,
                            "Contract": fs.symbol,
                            "Obs (Rows)": fs.row_count,
                            "Date Span": f"{fs.date_min} to {fs.date_max}" if fs.date_min else "—",
                            "Delivery Expiries": ", ".join(fs.expiry_dates[:3]) + ("..." if len(fs.expiry_dates) > 3 else ""),
                            "Ingestion Status": status_badge,
                        }
                    )
                st.dataframe(pd.DataFrame(file_rows), use_container_width=True, hide_index=True)

                if local_repo_rep.errors:
                    for err in local_repo_rep.errors:
                        st.warning(f"Repository Warning: {err}")
            elif ingestion_rep:
                st.markdown(f"**Ingested File**: `{ingestion_rep.filename}` ({ingestion_rep.file_type})")
                map_data = []
                for canon in ["Symbol", "Date", "ExpiryDate", "Open", "High", "Low", "Close", "Volume", "OpenInterest"]:
                    src_col = ingestion_rep.mapped_columns.get(canon, "—")
                    status = "Mapped" if src_col != "—" else "Missing"
                    map_data.append({"Canonical Field": canon, "Source File Column": src_col, "Status": status})

                st.dataframe(pd.DataFrame(map_data), use_container_width=True, hide_index=True)

                if ingestion_rep.unmapped_columns:
                    st.info(f"Unmapped source columns preserved: `{', '.join(ingestion_rep.unmapped_columns)}`")
            else:
                st.markdown("Synthetic data generated with canonical schema directly.")

            st.markdown("#### Supported Commodity Symbols Discovered")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.write("**Supported Gold Contracts Found:**")
                st.write(quality_rep.supported_symbols_found or "None")
            with col_s2:
                st.write("**Other / Unsupported Symbols Filtered:**")
                st.write(quality_rep.unsupported_symbols_found or "None")

            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown(
                """
                <div class="card-panel">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">Audit Issues & Integrity Log</div>
                            <div class="panel-subtitle">Line-level diagnostic logs distinguishing warnings from dropped records</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            if not quality_rep.issues:
                st.success("Clean dataset: 0 validation errors or warnings detected.")
            else:
                issues_data = [
                    {
                        "Severity": i.level,
                        "Category": i.category,
                        "Row Index": i.row_index if i.row_index is not None else "—",
                        "Contract": i.contract or "—",
                        "Diagnostic Message": i.message,
                    }
                    for i in quality_rep.issues
                ]
                st.dataframe(pd.DataFrame(issues_data), use_container_width=True, hide_index=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("#### Cleaned & Enriched Dataset")
            st.dataframe(enriched_df, use_container_width=True, hide_index=True)

            st.markdown("#### Raw Ingested Snapshot")
            st.dataframe(raw_df.head(25), use_container_width=True, hide_index=True)
