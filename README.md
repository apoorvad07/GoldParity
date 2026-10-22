# GoldParity — MCX Gold Derivatives Intelligence Platform

GoldParity is an institutional-grade quantitative data-product for comparing and evaluating relative value across Multi Commodity Exchange of India (MCX) Gold Futures contracts:
- **GOLDM** (Gold Mini)
- **GOLDTEN** (Gold 10 Grams)
- **GOLDGUINEA** (Gold Guinea)
- **GOLDPETAL** (Gold Petal)
- **GOLD** (Big Gold 1kg Benchmark)

Built with analytical honesty, strict data validation, version-sensitive contract specifications, and a dark navy / restrained gold user experience.

---

## Architecture & Features

```
GoldParity/
├── .streamlit/
│   └── config.toml             # Institutional dark navy & gold theme settings
├── data/
│   ├── sample_mcx_bhavcopy.csv # Realistic MCX Bhavcopy snapshot (15-Oct-2024)
│   └── README.md               # Schema notes & alias mapping documentation
├── src/
│   ├── contract_specs.py       # Version-sensitive contract specs & normalization math
│   ├── loader.py               # Flexible CSV/Excel ingestion & column alias resolution
│   ├── validator.py            # Strict validation layer, explicit date parser, data auditor
│   ├── analytics.py            # Relative value matrix, basis spreads, term structure
│   └── synthetic.py            # Isolated synthetic data generator for demonstration mode
├── tests/
│   ├── test_contract_specs.py  # Tests for contract specifications and normalization math
│   ├── test_loader.py          # Tests for file loading and column mapping
│   ├── test_validator.py       # Tests for date parsing, envelope checks, deduplication
│   └── test_analytics.py       # Tests for parity matrix, spreads, and multi-day series
├── app.py                      # Interactive Streamlit application
├── requirements.txt            # Pinned dependencies
└── README.md                   # Setup, usage, methodology, and limitations
```

---

## Mathematical Methodology & Parity Normalization

Because MCX contracts trade with different trading units, quotation bases, and physical purities, raw market quotes cannot be directly compared.

### Contract Specifications Summary
| Contract | Trading Unit | Quotation Basis | Purity (Fineness) | Tick Size |
| :--- | :--- | :--- | :--- | :--- |
| **GOLDM** | 100 grams | ₹ per 10 grams | **995** / 1000 | ₹1.00 |
| **GOLDTEN** | 10 grams | ₹ per 10 grams | **999** / 1000 | ₹1.00 |
| **GOLDGUINEA** | 8 grams | ₹ per 8 grams | **999** / 1000 | ₹1.00 |
| **GOLDPETAL** | 1 gram | ₹ per 1 gram | **999** / 1000 | ₹1.00 |
| **GOLD** | 1,000 grams | ₹ per 10 grams | **995** / 1000 | ₹1.00 |

### Parity Normalization Formula
GoldParity normalizes all quotes into a common benchmark basis: **₹ per 10 grams of 999 fineness (pure gold equivalent)** (customizable to 995 fineness):

$$\text{Price per Gram} = \frac{\text{Quoted Price}}{\text{Quotation Basis in Grams}}$$

$$\text{Purity Adjustment Factor} = \frac{\text{Target Purity Fineness}}{\text{Contract Purity Fineness}}$$

$$\text{Normalized Price} = \text{Price per Gram} \times \text{Purity Adjustment Factor} \times 10.0$$

*Example*: If `GOLDM` (995 fineness) closes at ₹72,220 for 10g, its 999-fineness 10g equivalent is:
$$\text{Normalized Price} = \frac{72220}{10} \times \frac{999}{995} \times 10 = ₹72,510.37$$

### Relative Value Spreads
Given a benchmark contract (e.g., nearest `GOLDM`):
$$\text{Spread (₹/10g)} = \text{Normalized Close}_{\text{contract}} - \text{Normalized Close}_{\text{benchmark}}$$
$$\text{Basis Spread (\%)} = \frac{\text{Spread}}{\text{Normalized Close}_{\text{benchmark}}} \times 100\%$$

---

## Setup & Local Execution (Windows Friendly)

### 1. Prerequisites
- Python 3.10 to 3.13 installed.

### 2. Create and Activate Virtual Environment
```powershell
# In PowerShell or Command Prompt within the GoldParity folder:
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the Automated Test Suite
```powershell
python -m pytest tests/ -v
```

### 5. Launch the Streamlit Application
```powershell
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## Operating Modes

### 1. File Upload Mode (Real Observations)
- Upload standard MCX Bhavcopy files (`.csv`, `.xlsx`, `.xls`).
- The validator automatically detects headers (e.g. `EXPIRY_DT`, `NO_OF_CONTRACTS`, `CLOSE_PRICE`), strips whitespace, validates dates strictly, and renders parity metrics.
- Try uploading the bundled sample dataset: `data/sample_mcx_bhavcopy.csv`.

### 2. Demonstration Mode (Synthetic Testing)
- Toggle **Demo Mode (Synthetic Data)** in the sidebar.
- Clearly watermarked with an alert banner; synthetic records are isolated and never conflated with real market data.
- Provides a 30-day time series in the Backtesting tab for UI validation.

---

## Analytical Integrity & Limitations

1. **Analytical Honesty**: GoldParity does not fabricate historical price points, trading signals, or backtest Sharpe ratios.
2. **Execution Costs**: Real MCX trading involves Exchange Turnover Charges, GST (18%), CTT (Commodity Transaction Tax: 0.01% on sell side), SEBI regulatory fees, and stamp duty. These frictions should be factored in before attempting physical delivery or cash arbitrage.
3. **Multi-Day Series Requirement**: Chronological backtesting requires historical multi-day Bhavcopies. Single-day snapshot uploads report cross-sectional parity rather than longitudinal performance.
