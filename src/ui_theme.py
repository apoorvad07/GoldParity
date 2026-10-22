"""GoldParity UI Theme & Design System.

Provides:
- Institutional color palette definitions
- Global CSS design system with Google Fonts, glassmorphism, and atmospheric gradients
- Base64 SVG and image asset loaders with safe fallbacks
- Reusable UI component builders for hero, feature cards, and coverage strips
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import List, Optional, Tuple


# -----------------------------------------------------------------------------
# Color Palette Constants
# -----------------------------------------------------------------------------
COLOR_BG_DARK = "#080B10"          # Base canvas
COLOR_SIDEBAR_DARK = "#0B1017"     # Sidebar navigation
COLOR_PANEL_DARK = "#111821"       # Elevated glassmorphic cards
COLOR_GOLD_PRIMARY = "#D8A84E"     # Bullion gold
COLOR_GOLD_CHAMPAGNE = "#F4D18A"   # Highlights & gradients
COLOR_GOLD_DEEP = "#A3751E"        # Shadow / border gold
COLOR_TEXT_PRIMARY = "#F5F5F2"     # Off-white crisp readability
COLOR_TEXT_SECONDARY = "#A8B0BA"   # Slate metallic secondary
COLOR_BORDER_GOLD = "rgba(216, 168, 78, 0.16)"
COLOR_BORDER_CHARCOAL = "rgba(255, 255, 255, 0.07)"


# -----------------------------------------------------------------------------
# Asset Loaders
# -----------------------------------------------------------------------------
def load_asset_base64(path_str: str, mime_type: Optional[str] = None) -> str:
    """Read a local asset file and return a base64 Data URI string.
    
    Returns an empty string if the file is missing, allowing graceful CSS fallback.
    """
    path = Path(path_str)
    if not path.exists():
        return ""

    if mime_type is None:
        ext = path.suffix.lower()
        if ext == ".svg":
            mime_type = "image/svg+xml"
        elif ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        else:
            mime_type = "application/octet-stream"

    with open(path, "rb") as f:
        b64_content = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64_content}"


# Cached preloads
LOGO_B64 = load_asset_base64("assets/goldparity_logo.svg")
MARK_B64 = load_asset_base64("assets/goldparity_mark.svg")
FAVICON_B64 = load_asset_base64("assets/goldparity_favicon.png") or load_asset_base64("assets/goldparity_favicon.svg")
HERO_IMG_B64 = load_asset_base64("assets/gold_vault_hero.jpg")
TEXTURE_IMG_B64 = load_asset_base64("assets/gold_texture_macro.jpg")


# -----------------------------------------------------------------------------
# Global Theme CSS
# -----------------------------------------------------------------------------
def get_global_css() -> str:
    """Generate the unified CSS stylesheet for GoldParity."""
    hero_bg_rule = (
        f"background-image: linear-gradient(180deg, rgba(8, 11, 16, 0.65) 0%, rgba(8, 11, 16, 0.94) 100%), url('{HERO_IMG_B64}');"
        if HERO_IMG_B64
        else "background: linear-gradient(135deg, #111821 0%, #080B10 100%);"
    )

    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* Global Foundation & Ambient Lighting */
    html, body, [class*="css"], .stApp {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: {COLOR_BG_DARK} !important;
        background-image: 
            radial-gradient(circle at 14% 12%, rgba(216, 168, 78, 0.07) 0%, transparent 40%),
            radial-gradient(circle at 86% 18%, rgba(17, 24, 33, 0.40) 0%, transparent 45%),
            radial-gradient(circle at 50% 65%, rgba(216, 168, 78, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 80% 92%, rgba(216, 168, 78, 0.05) 0%, transparent 40%) !important;
        background-attachment: fixed !important;
        color: {COLOR_TEXT_PRIMARY};
    }}

    /* Typography Hierarchy */
    .brand-display, .hero-headline, .section-heading, .landing-title {{
        font-family: 'Cinzel', Georgia, serif !important;
        letter-spacing: 0.02em;
    }}

    .gold-gradient-text {{
        background: linear-gradient(135deg, {COLOR_GOLD_CHAMPAGNE} 0%, {COLOR_GOLD_PRIMARY} 50%, {COLOR_GOLD_DEEP} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
    }}

    /* Tabular Numerals for Financial Accuracy */
    .tabular-nums, div[data-testid="stMetricValue"], td, th, .mono-num {{
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums;
        font-feature-settings: "tnum" 1, "cv05" 1;
    }}

    /* Container Bounds */
    .block-container {{
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1440px !important;
    }}

    /* Sidebar Architecture */
    section[data-testid="stSidebar"] {{
        background-color: {COLOR_SIDEBAR_DARK} !important;
        border-right: 1px solid rgba(216, 168, 78, 0.14) !important;
    }}

    .sidebar-logo-container {{
        padding: 0.75rem 0 0.5rem 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .sidebar-logo-img {{
        max-width: 220px;
        height: auto;
    }}

    /* Complete Elimination of Question-Mark Tooltip Icons */
    div[data-testid="stTooltipIcon"],
    button[data-testid="stBaseButton-headerNoPadding"],
    .stTooltipIcon {{
        display: none !important;
    }}

    /* Navigation Radio Elements */
    div[data-testid="stRadio"] > label {{
        display: none !important;
    }}
    div[data-testid="stRadio"] > div {{
        gap: 0.35rem;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"] {{
        background-color: transparent;
        padding: 0.5rem 0.85rem;
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
        border: 1px solid transparent;
        color: {COLOR_TEXT_SECONDARY} !important;
        font-weight: 500;
        font-size: 0.88rem;
        display: flex;
        align-items: center;
    }}
    /* Hide default radio circle so initial badge becomes the primary visual anchor */
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{
        display: none !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
        background-color: rgba(17, 24, 33, 0.7);
        color: {COLOR_TEXT_PRIMARY} !important;
        border-color: rgba(216, 168, 78, 0.25);
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] {{
        background: linear-gradient(90deg, rgba(216, 168, 78, 0.18) 0%, rgba(17, 24, 33, 0.85) 100%);
        border: 1px solid rgba(216, 168, 78, 0.45);
        color: {COLOR_TEXT_PRIMARY} !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }}

    /* Hero Section (Cinematic Vault Atmosphere) */
    .landing-hero {{
        border-radius: 16px;
        position: relative;
        overflow: hidden;
        margin-bottom: 2rem;
        border: 1px solid rgba(216, 168, 78, 0.24);
        box-shadow: 0 16px 48px -8px rgba(0, 0, 0, 0.75), 0 0 32px rgba(216, 168, 78, 0.08);
        padding: 3.5rem 3.5rem 3rem 3.5rem;
        {hero_bg_rule}
        background-size: cover;
        background-position: center;
    }}

    .landing-eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: rgba(216, 168, 78, 0.12);
        border: 1px solid rgba(216, 168, 78, 0.35);
        border-radius: 20px;
        padding: 0.3rem 0.85rem;
        color: {COLOR_GOLD_CHAMPAGNE};
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 1.25rem;
    }}

    .landing-headline {{
        font-family: 'Cinzel', serif !important;
        font-size: 2.85rem;
        font-weight: 800;
        line-height: 1.15;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 1.15rem;
        max-width: 820px;
        letter-spacing: -0.01em;
    }}

    .landing-subtext {{
        font-size: 1.05rem;
        color: {COLOR_TEXT_SECONDARY};
        line-height: 1.65;
        max-width: 680px;
        margin-bottom: 2rem;
        font-weight: 400;
    }}

    /* Elevated Glassmorphism Panel */
    .card-panel {{
        background: {COLOR_PANEL_DARK};
        backdrop-filter: blur(16px);
        border: 1px solid {COLOR_BORDER_GOLD};
        border-radius: 12px;
        padding: 1.35rem 1.65rem;
        margin-bottom: 1.35rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45);
    }}
    .panel-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.95rem;
    }}
    .panel-title {{
        font-size: 1.02rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        letter-spacing: -0.01em;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    .panel-subtitle {{
        font-size: 0.82rem;
        color: {COLOR_TEXT_SECONDARY};
    }}

    /* 4-Feature Interactive Cards Grid */
    .feature-card {{
        background: rgba(17, 24, 33, 0.85);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(216, 168, 78, 0.18);
        border-radius: 12px;
        padding: 1.65rem 1.45rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.25s ease-in-out;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        position: relative;
        overflow: hidden;
    }}
    .feature-card:hover {{
        border-color: rgba(216, 168, 78, 0.45);
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.55), 0 0 20px rgba(216, 168, 78, 0.12);
    }}
    .feature-card-icon {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 42px;
        height: 42px;
        border-radius: 8px;
        background: rgba(216, 168, 78, 0.08);
        border: 1px solid rgba(216, 168, 78, 0.2);
        margin-bottom: 1.15rem;
        transition: all 0.2s ease-in-out;
    }}
    .feature-card:hover .feature-card-icon {{
        background: rgba(216, 168, 78, 0.16);
        border-color: rgba(216, 168, 78, 0.45);
    }}
    .feature-card-title {{
        font-family: 'Cinzel', serif !important;
        font-size: 1.12rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 0.55rem;
        letter-spacing: 0.01em;
    }}
    .feature-card-desc {{
        font-size: 0.86rem;
        color: {COLOR_TEXT_SECONDARY};
        line-height: 1.55;
        margin-bottom: 1.25rem;
        flex-grow: 1;
    }}

    /* Bottom Information Strip */
    .bottom-info-strip {{
        background: rgba(11, 16, 23, 0.92);
        border: 1px solid rgba(216, 168, 78, 0.24);
        border-radius: 12px;
        padding: 1.35rem 1.85rem;
        margin-top: 2rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}

    /* Consistent Metallic Gold Initial Badges across Sidebar & Navigation */
    div[data-testid="stRadio"] label[data-baseweb="radio"] code,
    .gold-initial-badge {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 22px !important;
        height: 22px !important;
        min-width: 22px !important;
        border-radius: 5px !important;
        background: #0B1017 !important;
        border: 1px solid rgba(216, 168, 78, 0.45) !important;
        color: {COLOR_GOLD_PRIMARY} !important;
        -webkit-text-fill-color: {COLOR_GOLD_PRIMARY} !important;
        font-family: 'Cinzel', serif !important;
        font-size: 0.74rem !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        text-align: center !important;
        vertical-align: middle !important;
        margin-right: 8px !important;
        margin-left: 0 !important;
        padding: 0 !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4), inset 0 0 4px rgba(216, 168, 78, 0.08) !important;
        user-select: none !important;
        flex-shrink: 0 !important;
    }}

    /* Ensure initial remains strictly metallic gold in active, hover, and focus states */
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover code,
    div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] code,
    div[data-testid="stRadio"] label[data-baseweb="radio"]:focus code,
    div[data-testid="stRadio"] label[data-baseweb="radio"]:active code {{
        color: {COLOR_GOLD_PRIMARY} !important;
        -webkit-text-fill-color: {COLOR_GOLD_PRIMARY} !important;
        background: #0B1017 !important;
        border-color: rgba(216, 168, 78, 0.85) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5), 0 0 8px rgba(216, 168, 78, 0.25) !important;
    }}

    .gold-initial-badge-lg {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        min-width: 44px;
        border-radius: 8px;
        background: linear-gradient(135deg, rgba(17, 24, 33, 0.98) 0%, rgba(11, 16, 23, 0.95) 100%);
        border: 1px solid rgba(216, 168, 78, 0.45);
        color: {COLOR_GOLD_CHAMPAGNE};
        font-family: 'Cinzel', serif;
        font-size: 1.35rem;
        font-weight: 800;
        line-height: 1;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5), 0 0 16px rgba(216, 168, 78, 0.12);
        transition: all 0.25s ease-in-out;
    }}
    .feature-card:hover .gold-initial-badge-lg {{
        border-color: rgba(216, 168, 78, 0.85);
        color: #FFFFFF;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6), 0 0 20px rgba(216, 168, 78, 0.25);
        transform: scale(1.05);
    }}

    .sidebar-meta-header {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.72rem;
        font-weight: 700;
        color: #A0ABBA;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }}

    .hallmark-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(216, 168, 78, 0.08);
        border: 1px solid rgba(216, 168, 78, 0.28);
        border-radius: 6px;
        padding: 0.2rem 0.55rem;
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
        color: {COLOR_GOLD_CHAMPAGNE};
        font-weight: 600;
    }}

    /* Status Badges & Subtle Indicators */
    .status-dot {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }}
    .status-dot-live {{
        background-color: #34D399;
        box-shadow: 0 0 6px rgba(52, 211, 153, 0.6);
    }}
    .status-dot-demo {{
        background-color: {COLOR_GOLD_CHAMPAGNE};
        box-shadow: 0 0 6px rgba(244, 209, 138, 0.6);
    }}
    .status-dot-idle {{
        background-color: {COLOR_TEXT_SECONDARY};
    }}

    .badge-live {{
        background: rgba(52, 211, 153, 0.1);
        color: #34D399;
        border: 1px solid rgba(52, 211, 153, 0.3);
        padding: 0.2rem 0.65rem;
        border-radius: 16px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }}
    .badge-demo {{
        background: rgba(216, 168, 78, 0.1);
        color: {COLOR_GOLD_CHAMPAGNE};
        border: 1px solid rgba(216, 168, 78, 0.3);
        padding: 0.2rem 0.65rem;
        border-radius: 16px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }}
    .badge-idle {{
        background: rgba(168, 176, 186, 0.08);
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid rgba(168, 176, 186, 0.2);
        padding: 0.2rem 0.65rem;
        border-radius: 16px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }}

    /* Primary Gold Action Buttons */
    div.stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLOR_GOLD_CHAMPAGNE} 0%, {COLOR_GOLD_PRIMARY} 50%, {COLOR_GOLD_DEEP} 100%) !important;
        color: #080B10 !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 0.65rem 1.65rem !important;
        border-radius: 8px !important;
        letter-spacing: 0.04em !important;
        box-shadow: 0 4px 18px rgba(216, 168, 78, 0.35) !important;
        transition: all 0.2s ease-in-out !important;
    }}
    div.stButton > button[kind="primary"]:hover {{
        box-shadow: 0 6px 24px rgba(216, 168, 78, 0.55) !important;
        transform: translateY(-1px) !important;
    }}
    div.stButton > button[kind="secondary"] {{
        background: rgba(17, 24, 33, 0.85) !important;
        border: 1px solid rgba(216, 168, 78, 0.32) !important;
        color: {COLOR_TEXT_PRIMARY} !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
    }}
    div.stButton > button[kind="secondary"]:hover {{
        border-color: {COLOR_GOLD_PRIMARY} !important;
        color: {COLOR_GOLD_CHAMPAGNE} !important;
        background: rgba(17, 24, 33, 1.0) !important;
    }}

    /* Streamlit Table Styling */
    div[data-testid="stDataFrame"] {{
        background: rgba(17, 24, 33, 0.85);
        border-radius: 10px;
        border: 1px solid rgba(168, 176, 186, 0.15);
        overflow: hidden;
    }}

    /* Section Banners for Subpages */
    .section-banner {{
        background: linear-gradient(135deg, rgba(17, 24, 33, 0.95) 0%, rgba(8, 11, 16, 0.95) 100%);
        border: 1px solid rgba(216, 168, 78, 0.22);
        border-radius: 12px;
        padding: 1.5rem 1.85rem;
        margin-bottom: 1.65rem;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }}
    .section-banner-title {{
        font-family: 'Cinzel', serif !important;
        font-size: 1.55rem;
        font-weight: 800;
        color: {COLOR_TEXT_PRIMARY};
        letter-spacing: 0.01em;
        margin-bottom: 0.35rem;
    }}
    .section-banner-subtitle {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 0.88rem;
    }}

    /* Overview Hero Container */
    .hero-container {{
        background: {COLOR_PANEL_DARK};
        border: 1px solid rgba(216, 168, 78, 0.22);
        border-radius: 12px;
        padding: 1.85rem 2.2rem;
        margin-bottom: 1.65rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }}
    .hero-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(216, 168, 78, 0.12);
        border: 1px solid rgba(216, 168, 78, 0.35);
        border-radius: 20px;
        padding: 0.25rem 0.75rem;
        color: {COLOR_GOLD_CHAMPAGNE};
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 0.85rem;
    }}
    .hero-headline {{
        font-family: 'Cinzel', serif !important;
        font-size: 1.95rem;
        font-weight: 800;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 0.65rem;
        letter-spacing: -0.01em;
    }}
    .gold-text {{
        color: {COLOR_GOLD_PRIMARY};
    }}
    .hero-desc {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 0.92rem;
        line-height: 1.6;
        margin-bottom: 1.35rem;
        max-width: 900px;
    }}
    .hero-status-strip {{
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(216, 168, 78, 0.15);
    }}
    .hero-stat-item {{
        font-size: 0.82rem;
        color: {COLOR_TEXT_SECONDARY};
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }}
    .hero-stat-item strong {{
        color: {COLOR_TEXT_PRIMARY};
    }}

    /* Demo Mode Watermark Banner */
    .demo-banner {{
        background: rgba(17, 24, 33, 0.85);
        border: 1px solid rgba(216, 168, 78, 0.28);
        border-left: 3px solid {COLOR_GOLD_PRIMARY};
        color: {COLOR_TEXT_PRIMARY};
        padding: 0.85rem 1.25rem;
        border-radius: 6px;
        font-size: 0.84rem;
        margin-bottom: 1.35rem;
        display: flex;
        align-items: center;
        gap: 0.95rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }}
    .demo-banner-tag {{
        background: rgba(216, 168, 78, 0.14);
        border: 1px solid rgba(216, 168, 78, 0.35);
        color: {COLOR_GOLD_CHAMPAGNE};
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        flex-shrink: 0;
    }}

    /* Empty States */
    .empty-state {{
        background: rgba(17, 24, 33, 0.7);
        backdrop-filter: blur(14px);
        border: 1px dashed rgba(216, 168, 78, 0.28);
        border-radius: 12px;
        padding: 3.5rem 2.5rem;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }}
    .empty-state-icon {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 52px;
        height: 52px;
        border-radius: 10px;
        background: rgba(216, 168, 78, 0.08);
        border: 1px solid rgba(216, 168, 78, 0.22);
        margin: 0 auto 1.15rem auto;
    }}
    .empty-state-title {{
        font-family: 'Cinzel', serif !important;
        font-size: 1.35rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 0.45rem;
    }}
    .empty-state-desc {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 0.92rem;
        max-width: 540px;
        margin: 0 auto 1.35rem auto;
        line-height: 1.6;
    }}

    /* Methodology Callout */
    .methodology-callout {{
        background: rgba(11, 16, 23, 0.92);
        border: 1px solid rgba(216, 168, 78, 0.28);
        border-left: 4px solid {COLOR_GOLD_PRIMARY};
        border-radius: 8px;
        padding: 1.35rem 1.65rem;
        margin-top: 1.65rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }}
    .methodology-title {{
        color: {COLOR_GOLD_PRIMARY};
        font-size: 0.88rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.55rem;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }}
    .methodology-text {{
        color: #CBD5E1;
        font-size: 0.85rem;
        line-height: 1.65;
    }}
</style>
"""
